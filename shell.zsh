# Source this public loader from zsh to load the plugin's commands.
if [[ -n "${HERDR_PLUGIN_ROOT:-}" ]]; then
  __herdr_layouts_plugin_root=${HERDR_PLUGIN_ROOT:A}
else
  __herdr_layouts_plugin_root=${${(%):-%x}:A:h}
fi

source "$__herdr_layouts_plugin_root/libexec/layouts.zsh" || return $?
unset __herdr_layouts_plugin_root
