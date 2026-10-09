#!/usr/bin/env zsh

if [[ -n "${HERDR_PLUGIN_ROOT:-}" ]]; then
  __herdr_layouts_plugin_root=${HERDR_PLUGIN_ROOT:A}
else
  __herdr_layouts_plugin_root=${0:A:h:h}
fi

source "$__herdr_layouts_plugin_root/libexec/layouts.zsh" || exit $?
herdr-layout-list
