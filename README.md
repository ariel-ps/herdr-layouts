# Herdr Layouts

Save pane layouts, restore them, and create grids of coding agents.

Commands: `herdr-layout-save`, `herdr-layout-load`, `herdr-layout-up`, `herdr-layout-list`, and `herdr-grid-agents`. Layout load creates shells; layout up also resumes saved agents.

## Install

[Herdr Setup](https://github.com/ariel-ps/herdr-setup) installs prerequisites and lets you select this plugin in `dependencies.json`.

With Herdr 0.9.3+ already installed:

```sh
herdr plugin install ariel-ps/herdr-layouts --ref main --yes
```

Use a commit or release tag instead of `main` to pin a version. Supports macOS, Ubuntu/Debian, and Fedora.

Herdr Setup loads the enabled plugin's helpers in bash or zsh. For a manual installation, source the installed plugin's `shell.bash` in `.bashrc` or `shell.zsh` in `.zshrc`. Bash helpers call the same zsh implementation, so zsh must also be installed; you keep bash as your shell.
