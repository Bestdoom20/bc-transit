# Worldwide Transit installer for Windows: puts the skill where agent harnesses look for it, then runs the selftests.
#   irm https://raw.githubusercontent.com/Bestdoom20/worldwide-transit/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'
$repo = 'https://github.com/Bestdoom20/worldwide-transit.git'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git not found: install Git for Windows first' }
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }   # works in Windows PowerShell 5.1 too
if (-not $py) { throw 'Python not found: install Python 3.9 or newer from python.org first' }
& $py.Source -m pip install -q tzdata   # Windows has no system time zone database

# Claude Code reads ~/.claude/skills; Codex, Gemini CLI and most other harnesses read ~/.agents/skills
$targets = @()
if (Test-Path "$HOME/.claude") { $targets += "$HOME/.claude/skills" }
if ((Test-Path "$HOME/.agents") -or (Test-Path "$HOME/.codex") -or (Test-Path "$HOME/.gemini") -or -not $targets) { $targets += "$HOME/.agents/skills" }

foreach ($dir in $targets) {
  $dest = Join-Path $dir 'worldwide-transit'
  if (Test-Path "$dest/.git") { Write-Host "== updating $dest"; git -C $dest pull -q --ff-only }
  else { Write-Host "== installing into $dest"; New-Item -ItemType Directory -Force $dir | Out-Null; git clone -q --depth 1 $repo $dest }
  foreach ($s in 'transit', 'gtfs', 'flights', 'drive') {
    & $py.Source "$dest/$s.py" selftest; if ($LASTEXITCODE) { throw "$s.py selftest failed" }
  }
}
Write-Host 'INSTALL OK. Ask your agent: "plan me a trip". It will ask for your city once, then answer.'
