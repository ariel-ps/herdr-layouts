# Herdr Layouts

Save pane layouts, restore them, and create grids of coding agents.

Commands: `herdr-layout-save`, `herdr-layout-load`, `herdr-layout-up`, `herdr-layout-list`, and `herdr-grid-agents`. Layout load creates shells; layout up also resumes saved agents.

## Install

[Herdr Setup](https://github.com/ariel-ps/herdr-setup) installs prerequisites and lets you select this plugin in `dependencies.json`.

For standalone installation, you need Herdr 0.9.3+, zsh, jq, and Unix-socket-capable netcat (`nc`):

```sh
herdr plugin install ariel-ps/herdr-layouts --ref main --yes
```

Use a commit or release tag instead of `main` to pin a version. Supports macOS, Ubuntu/Debian, and Fedora.

Herdr Setup loads the enabled plugin's helpers in bash or zsh. For a manual installation, source the installed plugin's `shell.bash` in `.bashrc` or `shell.zsh` in `.zshrc`. Bash helpers call the same zsh implementation, so zsh must also be installed; you keep bash as your shell.

## Saving and restoring

```sh
herdr-layout-save work
herdr-layout-list
herdr-layout-up work
```

Names accept letters, digits, underscores, and hyphens, and cannot start with a hyphen. `herdr-layout-up` resumes Claude and Codex sessions only when Herdr reported a unique session ID when saving. Unidentified panes start fresh; launch failures return a nonzero exit status.

Re-save layouts created by older versions to capture verified sessions. Older conversation snapshots are no longer trusted because they could associate multiple panes with the same conversation. Layout geometry still loads normally.

## License

Original project code is licensed under the [MIT License](LICENSE). Third-party code and media retain their own terms; this license does not grant rights to game assets, downloaded themes, or other third-party content.
