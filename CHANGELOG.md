# Changelog

All notable changes to Herdr Layouts are documented in this file.

## Unreleased

### Added

- Auto-launch `lazygit` in a tab labelled `lazygit`, alongside the existing `code` and `board` tabs. New workspaces now get all three tabs by default.

### Changed

- Adopt the canonical Herdr plugin repository structure without changing the public shell commands.
- Keep the root shell files as public loaders and move the zsh implementation to `libexec/layouts.zsh`.
- Run the manifest action through its dedicated adapter in `actions/`.
