# Source this file from zsh to load this plugin's commands.
__herdr_layouts_ready() {
  command -v herdr >/dev/null 2>&1 || { echo "herdr: not installed" >&2; return 1; }
  command -v jq >/dev/null 2>&1 || { echo "herdr: jq not found" >&2; return 1; }
  [ "$(herdr status server 2>/dev/null | awk '/^status:/{print $2}')" = running ] || {
    echo "herdr: server not running" >&2; return 1
  }
}

__herdr_layout_dir() { print -r -- "${XDG_CONFIG_HOME:-$HOME/.config}/herdr/layouts"; }

# Keep every layout operation inside the layout directory, including symlinks.
__herdr_layout_name() {
  local name=$1 dir="$(__herdr_layout_dir)" file
  [[ -n "$name" && "$name" != [-.]* && -z "${name//[a-zA-Z0-9_-]/}" ]] || {
    echo 'herdr: layout names must start with a letter, digit, or underscore and contain only letters, digits, underscores, or hyphens' >&2
    return 2
  }
  for file in "$dir/$name.json" "$dir/$name.agents.json"; do
    [[ ! -L "$file" ]] || { echo "herdr: refusing symlink $file" >&2; return 2; }
  done
}

# One request, one response. The daemon speaks JSON lines over its unix socket,
# so nc is a complete client here — no token and no websocket, unlike Xirp.
__herdr_rpc() {
  local sock="${XDG_CONFIG_HOME:-$HOME/.config}/herdr/herdr.sock"
  [ -S "$sock" ] || { echo "herdr: no socket at $sock (is the server running?)" >&2; return 1; }
  command -v nc >/dev/null 2>&1 || { echo "herdr: nc not found" >&2; return 1; }
  printf '%s\n' "$1" | nc -U "$sock"
}

# usage: herdr-layout-save <name> [tab-id]
#   Defaults to the active tab. Overwrites an existing name without asking —
#   these are cheap to recreate and a prompt during a save is worse than a lost one.
herdr-layout-save() {
  __herdr_layouts_ready || return 1
  local name=$1 tab=$2 params='{}' out dir
  [ -n "$name" ] || { echo "usage: herdr-layout-save <name> [tab-id]" >&2; return 2; }
  __herdr_layout_name "$name" || return $?
  [ -n "$tab" ] && params=$(jq -nc --arg tab "$tab" '{tab_id:$tab}')

  out=$(__herdr_rpc "{\"id\":\"save\",\"method\":\"layout.export\",\"params\":$params}") || return 1
  print -r -- "$out" | jq -e '.result.layout' >/dev/null 2>&1 || {
    echo "herdr: export failed: $(print -r -- "$out" | jq -r '.error.code // .' 2>/dev/null)" >&2
    return 1
  }

  dir=$(__herdr_layout_dir); mkdir -p "$dir"
  print -r -- "$out" | jq '.result.layout' > "$dir/$name.json" || return 1
  echo "saved $name ($(print -r -- "$out" | jq '[.result.layout.root|..|objects|select(.type=="pane")]|length') panes) -> $dir/$name.json"
  __herdr_layout_snap_agents "$name" "$(print -r -- "$out" | jq -r '.result.layout.tab_id')"
}

# Save only session IDs reported for the pane. Never infer a conversation from
# its working directory or opening prompt: multiple agents can share both.
__herdr_layout_snap_agents() {
  local name=$1 tab=$2 pane label kind sid
  local sidecar="$(__herdr_layout_dir)/$name.agents.json" entries='{}'

  while IFS=$'\t' read -r pane label kind; do
    sid=$(herdr pane get "$pane" | jq -r --arg k "$kind" \
      '.result.pane | select(.agent == $k) | .agent_session.value // empty')
    if [[ -z "$sid" || -n "${sid//[a-zA-Z0-9_-]/}" || "$sid" == -* ]]; then
      echo "$pane: no verified session; will start fresh" >&2
      continue
    fi
    entries=$(print -r -- "$entries" | jq --arg l "$label" --arg s "$sid" \
      --arg k "$kind" '.[$l] = {kind: $k, session: $s, verified: true}')
  done < <(herdr pane list | jq -r --arg tab "$tab" \
    '.result.panes[] | select(.tab_id == $tab and (.label // "") != "" and (.agent // "") != "")
     | [.pane_id, .label, .agent] | @tsv')

  # Exclude every duplicate, rather than arbitrarily assigning it to one pane.
  entries=$(print -r -- "$entries" | jq 'to_entries | group_by(.value.kind, .value.session)
    | map(select(length == 1) | .[0]) | from_entries') || return 1
  # Always replace the sidecar so an empty snapshot cannot retain old sessions.
  print -r -- "$entries" | jq . > "$sidecar" || return 1
  echo "  agents: $(print -r -- "$entries" | jq -r 'keys | join(", ")') -> ${sidecar:t}"
}

# usage: herdr-layout-load <name> [workspace-id]
#   Always creates a new tab. Passing the saved tab_id back would make herdr
#   replace that tab, and a load is not worth destroying live panes over.
herdr-layout-load() {
  __herdr_layouts_ready || return 1
  local name=$1 ws=$2 file root params out
  [ -n "$name" ] || { echo "usage: herdr-layout-load <name> [workspace-id]" >&2; return 2; }
  __herdr_layout_name "$name" || return $?
  file="$(__herdr_layout_dir)/$name.json"
  [ -r "$file" ] || { echo "herdr: no saved layout $name" >&2; return 1; }

  [ -n "$ws" ] || ws=$(jq -r '.workspace_id // empty' "$file")
  root=$(jq -c '.root' "$file") || return 1
  params=$(jq -nc --arg ws "$ws" --arg label "$name" --argjson root "$root" \
    '{workspace_id:$ws, tab_label:$label, focus:true, root:$root}')

  out=$(__herdr_rpc "{\"id\":\"load\",\"method\":\"layout.apply\",\"params\":$params}") || return 1
  print -r -- "$out" | jq -e '.result' >/dev/null 2>&1 || {
    echo "herdr: apply failed: $(print -r -- "$out" | jq -r '.error.code // .' 2>/dev/null)" >&2
    return 1
  }
  echo "loaded $name -> $(print -r -- "$out" | jq -r '.result.tab.tab_id // "new tab"')"
  echo "note: shells only — use herdr-layout-up to resume saved agents" >&2
}

# usage: herdr-layout-list
herdr-layout-list() {
  local dir; dir=$(__herdr_layout_dir)
  [ -d "$dir" ] || { echo "no saved layouts"; return 0; }
  # Listed with find rather than a glob qualifier: (N) depends on shell options
  # this file cannot assume, and an unmatched bare glob is a hard error.
  local f found=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    found=1
    printf "%-22s %s panes\n" "${${f:t}:r}" "$(jq '[.root|..|objects|select(.type=="pane")]|length' "$f" 2>/dev/null)"
  done < <(find "$dir" -maxdepth 1 -type f -name '*.json' ! -name '*.agents.json' 2>/dev/null | sort)
  (( found )) || echo "no saved layouts"
}

# usage: herdr-layout-up <name> [kind]
#   Workspace, layout and agents in one line: find a workspace labelled <name> or
#   create one, load the layout into it, then start an agent in every pane under
#   the pane's own label.
#
#   Resolution is by label because a saved layout carries the workspace id it was
#   exported from, and those do not survive a server restart — a bare
#   herdr-layout-load of a layout saved weeks ago dies on workspace_not_found.
#
#   `workspace create` always brings an empty tab of its own and layout.apply
#   cannot fill an existing one without replacing it, so the layout arrives as a
#   second tab and the placeholder is closed afterwards.
#
#   The sidecar `<name>.agents.json` that herdr-layout-save writes alongside the
#   layout carries verified session IDs by pane label. Panes without one start
#   fresh. A failed resume is reported rather than replaced with a guessed session.
herdr-layout-up() {
  __herdr_layouts_ready || return 1
  local name=$1 kind="${2:-claude}" ws='' placeholder='' created tab pane label cwd
  local sidecar sid pane_kind failures=0
  [ -n "$name" ] || { echo "usage: herdr-layout-up <name> [kind]" >&2; return 2; }
  __herdr_layout_name "$name" || return $?
  [ -r "$(__herdr_layout_dir)/$name.json" ] || { echo "herdr: no saved layout $name" >&2; return 1; }
  sidecar="$(__herdr_layout_dir)/$name.agents.json"

  # An agent name is unique among live agents, so a second run would half-fail
  # anyway — but it would still leave a stray tab, and any pane that did start
  # would open a second view of a conversation already running elsewhere.
  local live
  live=$(herdr agent list | jq -r '.result.agents[].name // empty' \
    | grep -Fx -f <(jq -r '[.root|..|objects|select(.type=="pane")|.label//empty][]' \
        "$(__herdr_layout_dir)/$name.json") 2>/dev/null | head -3)
  [ -n "$live" ] && {
    echo "herdr: $name is already up (${${(f)live}:0:3}) — close it first" >&2; return 1
  }

  ws=$(herdr workspace list | jq -r --arg l "$name" \
    'first(.result.workspaces[] | select(.label == $l) | .workspace_id) // empty') || return 1
  if [ -z "$ws" ]; then
    created=$(herdr workspace create --label "$name" --no-focus) || return 1
    ws=$(print -r -- "$created" | jq -r '.result.workspace.workspace_id')
    placeholder=$(print -r -- "$created" | jq -r '.result.tab.tab_id')
  fi

  herdr-layout-load "$name" "$ws" || return 1
  [ -n "$placeholder" ] && herdr tab close "$placeholder" >/dev/null 2>&1

  tab=$(herdr workspace get "$ws" | jq -r '.result.workspace.active_tab_id')
  local -a args
  while IFS=$'\t' read -r pane label cwd; do
    [ -n "$pane" ] || continue
    args=()
    sid=''
    pane_kind=$kind
    if [ -r "$sidecar" ]; then
      # A saved fleet can be mixed — the kind travels per pane, the argument is
      # only the default for panes the sidecar says nothing about.
      pane_kind=$(jq -r --arg l "$label" --arg k "$kind" '.[$l].kind // $k' "$sidecar")
      sid=$(jq -r --arg l "$label" '.[$l] | select(.verified == true) | .session // empty' "$sidecar")
      if [[ -n "$sid" ]]; then
        if [[ -n "${sid//[a-zA-Z0-9_-]/}" || "$sid" == -* ]]; then
          echo "$pane: invalid saved session" >&2; (( failures++ )); continue
        fi
        case "$pane_kind" in
          claude) args+=(--resume "$sid") ;;
          codex) args+=(resume "$sid") ;;
          *) echo "$pane: cannot resume $pane_kind" >&2; (( failures++ )); continue ;;
        esac
      fi
    fi
    [ -n "$HERDR_AGENT_ARGS" ] && args+=(${=HERDR_AGENT_ARGS})

    if herdr agent start "$label" --kind "$pane_kind" --pane "$pane" \
         ${args:+--} "${args[@]}" >/dev/null 2>&1; then
      # Hand the id to herdr as well, or the pane comes back a dead shell after a
      # server restart. herdr only captures a resume id from argv in one exact
      # shape and misses ours, and it takes a reported one only under its own
      # source string — `herdr:<kind>`, which is what herdr-link sends.
      [ -n "$sid" ] && herdr pane report-agent-session "$pane" --source "herdr:$pane_kind" --agent "$pane_kind" --agent-session-id "$sid" >/dev/null 2>&1
      echo "$pane  $label  $pane_kind${sid:+  resumed ${sid[1,8]}}"
    else
      echo "$pane  $label  $pane_kind  FAILED (pane left at its prompt)" >&2
      (( failures++ ))
    fi
    sid=''
  done < <(herdr pane list | jq -r --arg tab "$tab" \
    '.result.panes[] | select(.tab_id == $tab)
     | [.pane_id, (.label // (.pane_id | sub("^.*:"; ""))), .cwd] | @tsv')
  echo "workspace $ws, tab $tab: $failures failed launches" >&2
  (( failures == 0 ))
}

# usage: herdr-grid-agents [count] [kind] [label]
#   The herdr answer to kitty-grid-claude-danger. kitty's version opens a tab of
#   N windows each running `zsh -lic claude-danger`; that cannot work here,
#   because `kitty @` does not see panes herdr owns.
#
#   Splitting and starting are separate in herdr on purpose: `agent start`
#   requires a pane already at its prompt and never creates layout. So build the
#   tab first, then start an agent in each pane, naming them <label>-1..N so
#   `herdr agent prompt <name>` works immediately and the session refs that
#   survive a restart have somewhere to attach.
#
#   Splits alternate right/down rather than repeating one direction, which
#   otherwise leaves unusably narrow columns past about four panes.
#
#   DANGER: each pane is an unsupervised agent. Flags come from
#   HERDR_AGENT_ARGS, empty by default — the caller decides whether to bypass
#   permission checks, not this helper.
herdr-grid-agents() {
  __herdr_layouts_ready || return 1
  local want="${1:-9}" kind="${2:-claude}" label="${3:-}"
  [[ "$want" == <-> ]] && (( want > 0 )) \
    || { echo "herdr-grid-agents: count must be a positive number, got: ${1:-}" >&2; return 2; }

  if [ -z "$label" ]; then
    [ "$PWD" = "$HOME" ] && label=home || label="${PWD:t}"
  fi
  # herdr names are [a-z][a-z0-9_-]{0,31} and must be unique among live agents.
  label=$(print -r -- "${label:l}" | tr -c 'a-z0-9_-' '-' | sed 's/^[^a-z]*//; s/-*$//')
  [ -n "$label" ] || { echo "herdr-grid-agents: could not derive a usable label; pass one" >&2; return 1; }

  local created tab root pane prev dir i name failures=0
  created=$(herdr tab create --label "$label" --cwd "$PWD") || return 1
  tab=$(print -r -- "$created" | jq -r '.result.tab.tab_id')
  root=$(print -r -- "$created" | jq -r '.result.root_pane.pane_id')
  local -a panes=("$root")

  prev=$root
  for (( i = 2; i <= want; i++ )); do
    (( i % 2 == 0 )) && dir=right || dir=down
    pane=$(herdr pane split "$prev" --direction "$dir" --no-focus --cwd "$PWD" \
      | jq -r '.result.pane.pane_id') || return 1
    [ -n "$pane" ] && [ "$pane" != null ] || { (( failures++ )); break; }
    panes+=("$pane")
    prev=$pane
  done

  i=1
  for pane in $panes; do
    name="$label-$i"
    # Named before start so a failed launch still leaves an addressable pane.
    herdr pane rename "$pane" "$name" >/dev/null 2>&1
    if herdr agent start "$name" --kind "$kind" --pane "$pane" \
         ${HERDR_AGENT_ARGS:+-- ${=HERDR_AGENT_ARGS}} >/dev/null 2>&1; then
      echo "$pane  $name  $kind"
    else
      echo "$pane  $name  $kind  FAILED (pane left at its prompt)" >&2
      (( failures++ ))
    fi
    (( i++ ))
  done
  echo "tab $tab: ${#panes} panes in $PWD, $failures failures" >&2
  (( failures == 0 ))
}
