#!/usr/bin/env bash
# The Municipal Oracle: harmless bureaucracy for uncertain computers.

set -u

if [[ -t 1 && -z ${NO_COLOR:-} ]]; then
  DIM=$'\e[2m'; BOLD=$'\e[1m'; CYAN=$'\e[36m'; YELLOW=$'\e[33m'; RESET=$'\e[0m'
else
  DIM=''; BOLD=''; CYAN=''; YELLOW=''; RESET=''
fi

pause() {
  [[ -t 1 && -z ${ORACLE_IMPATIENT:-} ]] && sleep "${1:-0.25}"
}

typewriter() {
  local text=$1 i
  if [[ -t 1 && -z ${ORACLE_IMPATIENT:-} ]]; then
    for ((i=0; i<${#text}; i++)); do
      printf '%s' "${text:i:1}"
      sleep 0.012
    done
    printf '\n'
  else
    printf '%s\n' "$text"
  fi
}

pick() {
  local n=$1; shift
  printf '%s' "${@:1+n%$#:1}"
}

place=${PWD##*/}
[[ -n $place ]] || place='/ (an unnecessarily important directory)'
shell_name=${SHELL##*/}
[[ -n $shell_name ]] || shell_name='an unidentified shell'
minute=$(date +%M 2>/dev/null || printf '00')
minute=$((10#$minute))
jobs=$(jobs -p 2>/dev/null | wc -l | tr -d ' ')
seed_text="$place|$shell_name|$minute|$jobs|${USER:-mysterious resident}"

if command -v cksum >/dev/null 2>&1; then
  seed=$(printf '%s' "$seed_text" | cksum | awk '{print $1}')
else
  seed=${#seed_text}
fi

departments=(
  'Department of Almosts'
  'Office of Reversible Omens'
  'Bureau of Unclaimed Tuesdays'
  'Ministry of Indoor Weather'
  'Commission on Suspiciously Specific Feelings'
  'Subcommittee for Things Found Under Desks'
)
objects=(
  'a blue cup' 'the third drawer' 'an obsolete cable'
  'a sentence you nearly deleted' 'one left shoe' 'a patient onion'
)
verbs=(
  'will forgive' 'has been quietly supervising' 'intends to outlive'
  'is impersonating' 'will file an appeal against' 'remembers'
)
consequences=(
  'Do not optimize this.'
  'The appropriate response is an unnecessarily good sandwich.'
  'Proceed, but leave one useful mistake intact.'
  'A door will become a hallway if given sufficient paperwork.'
  'This is neither good nor bad, but it is wearing a small hat.'
  'Your next idea has already arrived and is pretending to be clutter.'
)

department=$(pick "$seed" "${departments[@]}")
object=$(pick "$((seed / 7))" "${objects[@]}")
verb=$(pick "$((seed / 13))" "${verbs[@]}")
consequence=$(pick "$((seed / 17))" "${consequences[@]}")
case_number=$(printf '%04d-%02d' "$((seed % 10000))" "$((minute + jobs + 1))")

printf '\n%s╭────────────────────────────────────────────╮%s\n' "$CYAN" "$RESET"
printf '%s│%s  %sTHE MUNICIPAL ORACLE%s                    %s│%s\n' "$CYAN" "$RESET" "$BOLD" "$RESET" "$CYAN" "$RESET"
printf '%s│%s  Permit for One (1) Improbable Future   %s│%s\n' "$CYAN" "$RESET" "$CYAN" "$RESET"
printf '%s╰────────────────────────────────────────────╯%s\n\n' "$CYAN" "$RESET"

typewriter "Now convening: $department."
pause .35
printf '%sEvidence entered into the record:%s\n' "$DIM" "$RESET"
printf '  present location ........ %s\n' "$place"
printf '  presiding shell ......... %s\n' "$shell_name"
printf '  background conspirators . %s\n' "$jobs"
printf '  case number ............. %s\n\n' "$case_number"
pause .35

printf '%s' "$YELLOW"
typewriter "FINDING: $object $verb the present arrangement."
typewriter "RULING:  $consequence"
printf '%s\n' "$RESET"
pause .3

printf '%sSigned electronically by:%s\n' "$DIM" "$RESET"
printf '      _\n'
printf '   __/o\\__    %s\n' "$department"
printf '  /_______/    %s\n' "$DIM(acting through a very small pigeon)$RESET"
printf '\n%sThis ruling expires the moment it becomes convenient.%s\n\n' "$DIM" "$RESET"

