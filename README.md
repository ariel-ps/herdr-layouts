# Herdr Layouts

Save pane layouts, restore them, and create grids of coding agents.

Commands: `herdr-layout-save`, `herdr-layout-load`, `herdr-layout-up`, `herdr-layout-list`, and `herdr-grid-agents`. Layout load creates shells; layout up also resumes saved agents.

## Install

[Herdr Setup](https://github.com/ariel-ps/herdr-setup) installs prerequisites and lets you select this plugin in `dependencies.json`.

For standalone installation, you need Herdr 0.9.3+, Rust 1.89+ with Cargo (for installation), zsh, jq, and Unix-socket-capable netcat (`nc`):

```sh
herdr plugin install ariel-ps/herdr-layouts --ref main --yes
```

Use a commit or release tag instead of `main` to pin a version. Supports macOS, Ubuntu/Debian, and Fedora.

Herdr Setup loads the enabled plugin's helpers in bash or zsh. For a manual installation, source the installed plugin's `shell.bash` in `.bashrc` or `shell.zsh` in `.zshrc`. These root files are stable public loaders for the private `libexec/layouts.zsh` implementation. Bash helpers call that same zsh implementation, so zsh must also be installed; you keep bash as your shell.

## Code and Board tabs

Every new workspace keeps its default first tab (typically labelled `1`) and adds two more tabs labelled `code` and `board` without stealing focus. The same hooks then open Neovim and Herdr Board when each named tab's shell is idle.

You can still create or rename any other idle, single-pane tab to `code` or `board` (case-insensitive) to trigger the same launchers manually.

Neovim must be installed and available on PATH for `code` tabs. The `herdr-board` plugin must be installed and enabled for `board` tabs; the hook finds its executable automatically.

Each app starts at most once per pane. It leaves other tab names, tabs with multiple panes, and panes already running an agent or another program alone. The launcher is a compiled Rust binary; Python is not needed at runtime. No Herdr restart is needed after enabling the plugin.

Run `herdr plugin action invoke dev.ariel.herdr-layouts.control-panel` to browse setup tools and help through **Herdr Plus**. Herdr Setup also binds **prefix+Down** to this panel. Herdr 0.9.3 does not display plugin actions in its sidebar or right-click menus.

## Saving and restoring

```sh
herdr-layout-save work
herdr-layout-list
herdr-layout-up work
```

Names accept letters, digits, underscores, and hyphens, and cannot start with a hyphen. `herdr-layout-up` resumes Claude and Codex sessions only when Herdr reported a unique session ID when saving. Unidentified panes start fresh; launch failures return a nonzero exit status. Pane labels must be unique when saving or resuming; ambiguous layouts are rejected before any agents start.

Re-save layouts created by older versions to capture verified sessions. Older conversation snapshots are no longer trusted because they could associate multiple panes with the same conversation. Layout geometry still loads normally.

## Development

Run the contract and runtime tests with `python3 tests/test_plugin.py`. Check shell syntax with `zsh -n shell.zsh && zsh -n libexec/layouts.zsh && zsh -n actions/list-layouts.zsh && bash -n shell.bash`.

Build the tab launcher with `sh scripts/build/install.sh` and check it with `python3 tests/test_named_tabs.py`.

## License

Original project code is licensed under the [MIT License](LICENSE). Third-party code and media retain their own terms; this license does not grant rights to game assets, downloaded themes, or other third-party content.
