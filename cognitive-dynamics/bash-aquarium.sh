#!/usr/bin/env bash
# Turn shell history into a brief terminal aquarium. Nothing is executed.

set -u

frames=90
still=0
while (($#)); do
  case $1 in
    --still) still=1 ;;
    --frames) shift; frames=${1:-90} ;;
    -h|--help)
      printf '%s\n' 'usage: bash-aquarium.sh [--still] [--frames N]'
      printf '%s\n' 'Optional stdin format: EXIT_STATUS<TAB>COMMAND'
      exit 0 ;;
    *) printf 'unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

if ! [[ $frames =~ ^[0-9]+$ ]] || ((frames < 1)); then
  printf 'frames must be a positive integer\n' >&2
  exit 2
fi

declare -a commands=() statuses=() xs=() ys=() speeds=() glyphs=() colors=()

if [[ ! -t 0 ]]; then
  while IFS=$'\t' read -r status command; do
    [[ -n ${command:-} ]] || continue
    if [[ $status =~ ^[0-9]+$ ]]; then
      statuses+=("$status"); commands+=("$command")
    else
      statuses+=(0); commands+=("$status${command:+	$command}")
    fi
  done
else
  history_file=${HISTFILE:-$HOME/.bash_history}
  if [[ -r $history_file ]]; then
    while IFS= read -r command; do
      [[ $command =~ ^#[0-9]+$ ]] && continue
      commands+=("$command"); statuses+=(0)
    done < <(tail -n 24 "$history_file")
  fi
fi

if ((${#commands[@]} == 0)); then
  commands=('echo hello' 'printf "%s\n" plankton | sort' 'git status' 'make # failed')
  statuses=(0 0 0 1)
fi

# Keep the tank legible.
if ((${#commands[@]} > 12)); then
  commands=("${commands[@]: -12}")
  statuses=("${statuses[@]: -12}")
fi

cols=${COLUMNS:-$(tput cols 2>/dev/null || printf 80)}
lines=${LINES:-$(tput lines 2>/dev/null || printf 24)}
((cols < 44)) && cols=44
((lines < 14)) && lines=14
width=$((cols - 2))
height=$((lines - 5))

hash_command() {
  local value
  value=$(printf '%s' "$1" | cksum 2>/dev/null | awk '{print $1}')
  printf '%s' "${value:-${#1}}"
}

for i in "${!commands[@]}"; do
  command=${commands[i]}
  seed=$(hash_command "$command")
  xs[i]=$((seed % (width - 15) + 1))
  ys[i]=$((seed / 17 % (height - 3) + 1))
  speeds[i]=$((seed % 3 + 1))
  colors[i]=$((31 + seed % 6))
  if ((statuses[i] != 0)) || [[ $command == *'# failed'* ]]; then
    glyphs[i]='×_× ｡ﾟ'
  elif [[ $command == *'|'* ]]; then
    glyphs[i]='o==o==o>'
  elif ((${#command} > 55)); then
    glyphs[i]='<º))))><~~~~'
  elif [[ $command == git* ]]; then
    glyphs[i]='<git)))><'
  else
    word=${command%% *}; word=${word:0:5}
    glyphs[i]="<${word:-sh}><"
  fi
done

cleanup() {
  [[ -t 1 ]] && printf '\e[0m\e[?25h\n'
}
trap cleanup EXIT INT TERM

draw_frame() {
  local frame=$1 i x y floor label
  printf '\e[H'
  printf '\e[36m╭%*s╮\e[0m\n' "$width" '' | tr ' ' '─'
  for ((y=1; y<=height; y++)); do
    printf '\e[36m│\e[0m%*s\e[36m│\e[0m\n' "$width" ''
  done
  printf '\e[36m╰%*s╯\e[0m\n' "$width" '' | tr ' ' '─'
  printf '\e[2m shell history aquarium — pipes are worms; long commands are eels; failures sink \e[0m'

  for i in "${!commands[@]}"; do
    x=$(( (xs[i] + frame * speeds[i]) % (width - ${#glyphs[i]} - 1) + 1 ))
    if ((statuses[i] != 0)) || [[ ${commands[i]} == *'# failed'* ]]; then
      y=$((ys[i] + frame / 6))
      floor=$((height - 1))
      ((y > floor)) && y=$floor
    else
      y=${ys[i]}
    fi
    printf '\e[%d;%dH\e[%dm%s\e[0m' "$((y + 1))" "$((x + 1))" "${colors[i]}" "${glyphs[i]}"
  done
  label=${commands[frame % ${#commands[@]}]}
  label=${label//$'\n'/ }
  label=${label:0:$((width - 12))}
  printf '\e[%d;3H\e[2mobserved: %s\e[0m' "$((height + 3))" "$label"
}

if [[ ! -t 1 ]] || ((still)); then
  printf 'SHELL HISTORY AQUARIUM\n\n'
  for i in "${!commands[@]}"; do
    printf '%-13s %s\n' "${glyphs[i]}" "${commands[i]}"
  done
  exit 0
fi

printf '\e[2J\e[H\e[?25l'
for ((frame=0; frame<frames; frame++)); do
  draw_frame "$frame"
  sleep 0.08
done

