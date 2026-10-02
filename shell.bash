# Bash entry points reuse the plugin's zsh implementation.
_HERDR_LAYOUTS_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export PATH="$_HERDR_LAYOUTS_ROOT/bin:$PATH"

herdr-layout-save() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/shell.zsh"; shift; herdr-layout-save "$@"' herdr-layout-save "$_HERDR_LAYOUTS_ROOT" "$@"
}

herdr-layout-load() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/shell.zsh"; shift; herdr-layout-load "$@"' herdr-layout-load "$_HERDR_LAYOUTS_ROOT" "$@"
}

herdr-layout-up() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/shell.zsh"; shift; herdr-layout-up "$@"' herdr-layout-up "$_HERDR_LAYOUTS_ROOT" "$@"
}

herdr-layout-list() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/shell.zsh"; shift; herdr-layout-list "$@"' herdr-layout-list "$_HERDR_LAYOUTS_ROOT" "$@"
}

herdr-grid-agents() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/shell.zsh"; shift; herdr-grid-agents "$@"' herdr-grid-agents "$_HERDR_LAYOUTS_ROOT" "$@"
}
