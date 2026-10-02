# Herdr Layouts

Save pane layouts, restore them, and create grids of coding agents.

Commands: `herdr-layout-save`, `herdr-layout-load`, `herdr-layout-up`, `herdr-layout-list`, and `herdr-grid-agents`. Layout load creates shells; layout up also resumes saved agents.

## Install

[Herdr Setup](https://github.com/ariel-ps/herdr-setup) installs prerequisites and lets you select this plugin in `dependencies.json`.

With Herdr 0.9.3+ already installed:

```sh
herdr plugin install ariel-ps/herdr-layouts --ref main --yes
```

Use a commit or release tag instead of `main` to pin a version. Supports macOS and Ubuntu/Debian Linux.

Herdr Setup loads `shell.zsh` for enabled plugins when a new zsh starts. For a manual installation, source the installed plugin’s `shell.zsh` in your `.zshrc`.
