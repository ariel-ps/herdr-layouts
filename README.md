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

Herdr Setup loads the enabled plugin's helpers in bash or zsh. For a manual installation, source the installed plugin's `shell.bash` in `.bashrc` or `shell.zsh` in `.zshrc`. Bash helpers call the same zsh implementation, so zsh must also be installed; you keep bash as your shell.

## Code and Board tabs

Create a tab named `code` (case-insensitive), or rename a new shell tab to `Code`, to open `nvim .` in that tab's directory. Neovim must be installed and available on PATH; your existing Neovim configuration is used.

Create or rename an idle tab to `board` (case-insensitive) to open Herdr Board in that tab. The `herdr-board` plugin must be installed and enabled; the hook finds its executable automatically.

Each app starts at most once per pane. It leaves other tab names, tabs with multiple panes, and panes already running an agent or another program alone. The launcher is a compiled Rust binary; Python is not needed at runtime. No Herdr restart is needed after enabling the plugin.

Open **Control panel** from Herdr’s plugin actions menu or a pane, tab, or workspace context menu to browse setup tools and help. This delegates to the installed **Herdr Plus** plugin.

## Saving and restoring

```sh
herdr-layout-save work
herdr-layout-list
herdr-layout-up work
```

Names accept letters, digits, underscores, and hyphens, and cannot start with a hyphen. `herdr-layout-up` resumes Claude and Codex sessions only when Herdr reported a unique session ID when saving. Unidentified panes start fresh; launch failures return a nonzero exit status.

Re-save layouts created by older versions to capture verified sessions. Older conversation snapshots are no longer trusted because they could associate multiple panes with the same conversation. Layout geometry still loads normally.

## Development

Build the tab launcher with `sh scripts/build/install.sh` and check it with `python3 tests/test_named_tabs.py`.

## License

Original project code is licensed under the [MIT License](LICENSE). Third-party code and media retain their own terms; this license does not grant rights to game assets, downloaded themes, or other third-party content.
