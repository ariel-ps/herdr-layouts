# Bash entry points reuse the plugin's zsh implementation.
if [[ -n "${HERDR_PLUGIN_ROOT:-}" ]]; then
  __herdr_layouts_plugin_root=$(CDPATH='' cd -- "$HERDR_PLUGIN_ROOT" && pwd -P)
else
  __herdr_layouts_plugin_root=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
fi

herdr-layout-save() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/libexec/layouts.zsh"; shift; herdr-layout-save "$@"' herdr-layout-save "$__herdr_layouts_plugin_root" "$@"
}

herdr-layout-load() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/libexec/layouts.zsh"; shift; herdr-layout-load "$@"' herdr-layout-load "$__herdr_layouts_plugin_root" "$@"
}

herdr-layout-up() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/libexec/layouts.zsh"; shift; herdr-layout-up "$@"' herdr-layout-up "$__herdr_layouts_plugin_root" "$@"
}

herdr-layout-list() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/libexec/layouts.zsh"; shift; herdr-layout-list "$@"' herdr-layout-list "$__herdr_layouts_plugin_root" "$@"
}

herdr-grid-agents() {
  HERDR_AGENT_ARGS="${HERDR_AGENT_ARGS:-}" zsh -fc 'source "$1/libexec/layouts.zsh"; shift; herdr-grid-agents "$@"' herdr-grid-agents "$__herdr_layouts_plugin_root" "$@"
}
