#!/bin/sh
# Worldwide Transit installer: puts the skill where agent harnesses look for it, then runs the selftests. Safe to run again.
#   curl -fsSL https://raw.githubusercontent.com/Bestdoom20/worldwide-transit/main/install.sh | sh
#   sh install.sh /path/to/skills      install into one folder of your choice instead
set -eu
REPO=https://github.com/Bestdoom20/worldwide-transit.git
die() { echo "ERROR: $*" >&2; exit 1; }
command -v git >/dev/null || die "git not found: install git first"
command -v python3 >/dev/null || die "python3 not found: install Python 3.9 or newer first"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' || die "Python 3.9+ needed, found $(python3 --version)"

if [ $# -gt 0 ]; then
  targets=$1
else
  # Claude Code reads ~/.claude/skills; Codex, Gemini CLI and most other harnesses read ~/.agents/skills
  targets=""
  [ -d "$HOME/.claude" ] && targets="$HOME/.claude/skills"
  { [ -d "$HOME/.agents" ] || [ -d "$HOME/.codex" ] || [ -d "$HOME/.gemini" ] || [ -z "$targets" ]; } && targets="$targets $HOME/.agents/skills"
fi

for dir in $targets; do
  dest="$dir/worldwide-transit"
  if [ -d "$dest/.git" ]; then
    echo "== updating $dest"
    git -C "$dest" pull -q --ff-only
  else
    echo "== installing into $dest"
    mkdir -p "$dir"
    git clone -q --depth 1 "$REPO" "$dest"
  fi
  python3 "$dest/transit.py" selftest
  python3 "$dest/gtfs.py" selftest
done
echo "INSTALL OK. Ask your agent: \"when is the next bus home?\" It will ask for your city once, then answer."
