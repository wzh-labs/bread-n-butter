# bread-n-butter

Personal Claude Code skills and shell aliases.

## Install

```sh
./install.sh
```

This will:

- Symlink each directory in [skills/](skills/) into `~/.claude/skills/`.
- Symlink [shell/aliases.sh](shell/aliases.sh) to `~/.bread-n-butter-aliases.sh` and add a `source` line to `~/.zshrc` (idempotent).
- Copy [iterm/com.googlecode.iterm2.plist](iterm/com.googlecode.iterm2.plist) to `~/Library/Preferences/com.googlecode.iterm2.plist` (overwrites existing).

After install, run `source ~/.zshrc` to pick up the aliases in your current shell.

## Export iTerm settings

To snapshot your current iTerm2 preferences back into this repo:

```sh
./export-iterm.sh
```

Restarts `cfprefsd` first so the on-disk plist reflects in-memory changes, then copies it into [iterm/](iterm/).

## Layout

- [skills/](skills/) — Claude Code skills, one per subdirectory.
- [shell/aliases.sh](shell/aliases.sh) — shell aliases.
- [iterm/](iterm/) — iTerm2 preferences plist.
- [install.sh](install.sh) — installer.
- [export-iterm.sh](export-iterm.sh) — snapshot live iTerm2 prefs back into the repo.
