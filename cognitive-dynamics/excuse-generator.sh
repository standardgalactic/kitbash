#!/usr/bin/env bash
# Produce an absurd but evidence-based explanation of a Git repository.

set -u

if ! command -v git >/dev/null 2>&1; then
  printf 'Excuse denied: Git itself has failed to attend the hearing.\n' >&2
  exit 1
fi

if ! root=$(git rev-parse --show-toplevel 2>/dev/null); then
  printf 'Work could not begin because this directory has not yet developed version control.\n'
  exit 1
fi

cd "$root" || exit 1
branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || printf 'detached consciousness')
porcelain=$(git status --porcelain=v1 2>/dev/null || true)
staged=$(printf '%s\n' "$porcelain" | awk 'substr($0,1,1) != " " && substr($0,1,1) != "?" {n++} END {print n+0}')
unstaged=$(printf '%s\n' "$porcelain" | awk 'substr($0,2,1) != " " && substr($0,1,2) != "??" {n++} END {print n+0}')
untracked=$(printf '%s\n' "$porcelain" | awk 'substr($0,1,2) == "??" {n++} END {print n+0}')
conflicts=$(printf '%s\n' "$porcelain" | awk 'substr($0,1,2) ~ /^(DD|AU|UD|UA|DU|AA|UU)$/ {n++} END {print n+0}')

upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)
ahead=0
behind=0
if [[ -n $upstream ]]; then
  counts=$(git rev-list --left-right --count "$upstream...HEAD" 2>/dev/null || printf '0 0')
  read -r behind ahead <<<"$counts"
fi

stash_count=$(git stash list 2>/dev/null | wc -l | tr -d ' ')
age='unknown'
if epoch=$(git log -1 --format=%ct 2>/dev/null); then
  now=$(date +%s)
  age=$(((now - epoch) / 86400))
fi

plural() {
  local n=$1 singular=$2 plural_form=${3:-${2}s}
  if ((n == 1)); then printf '%s %s' "$n" "$singular"; else printf '%s %s' "$n" "$plural_form"; fi
}

facts=()
((untracked > 0)) && facts+=("$(plural "$untracked" 'untracked file') awaiting citizenship")
((unstaged > 0)) && facts+=("$(plural "$unstaged" 'working-tree alteration') refusing formal recognition")
((staged > 0)) && facts+=("$(plural "$staged" 'staged change') dressed for an event that has not occurred")
((conflicts > 0)) && facts+=("$(plural "$conflicts" 'merge conflict') engaged in constitutional litigation")
((stash_count > 0)) && facts+=("$(plural "$stash_count" 'stash') held in an undisclosed location")
((ahead > 0)) && facts+=("the local branch being $(plural "$ahead" 'commit') ahead of public opinion")
((behind > 0)) && facts+=("the local branch being $(plural "$behind" 'commit') behind contemporary events")
[[ -z $upstream ]] && facts+=("the absence of any recognized upstream authority")
[[ $branch == 'detached consciousness' ]] && facts+=("HEAD undergoing a period of detached consciousness")
[[ $age != unknown && $age -gt 14 ]] && facts+=("the last commit having entered a ${age}-day contemplative retreat")

printf '\nOFFICIAL EXPLANATION OF DELAY\n'
printf 'Repository: %s\n' "${root##*/}"
printf 'Branch:     %s\n\n' "$branch"

if ((${#facts[@]} == 0)); then
  printf 'The repository is clean, synchronized, and administratively blameless.\n'
  printf 'Accordingly, the delay must be attributed to the dangerous proximity of completion.\n'
else
  printf 'Progress was delayed by '
  for i in "${!facts[@]}"; do
    if ((i > 0 && i == ${#facts[@]} - 1)); then
      printf ', and '
    elif ((i > 0)); then
      printf ', '
    fi
    printf '%s' "${facts[i]}"
  done
  printf '.\n'
fi

printf '\nThis explanation is technically accurate and emotionally inadmissible.\n\n'

