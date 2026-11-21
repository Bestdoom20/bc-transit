# Install Worldwide Transit (instructions for an AI agent)

What this is: a travel planner skill for anywhere in the world: live flight prices and the cheapest days to fly,
trains, coaches, ferries, city transit with live delays, and driving time and fuel cost. Free, no API key, no setup,
standard-library Python.

The user handed you this repository and said something like "install this". Install it, ask them one question, check it
works, and tell them what to ask. They should not have to type a command.

## Steps (with a shell)

1. **Install.** Run the installer. It needs `git` and Python 3.9+, puts the skill in `~/.claude/skills` (Claude Code)
   and/or `~/.agents/skills` (Codex, Gemini CLI and others), and runs both selftests. Success ends with `INSTALL OK`.
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Bestdoom20/worldwide-transit/main/install.sh | sh
   ```
   Windows PowerShell: `irm https://raw.githubusercontent.com/Bestdoom20/worldwide-transit/main/install.ps1 | iex`.
   If your harness reads skills from another folder, pass it: `sh install.sh /path/to/skills`.
   If Python is missing or older than 3.9, install it with the system package manager if you are allowed, else ask.

2. **Home region.** If you already know where the user lives (memory, profile, this conversation), use that. Otherwise
   ask ONE short question: "What city or region are you usually in?" Then save it with its IANA time zone and the
   local currency:
   ```bash
   python3 ~/.claude/skills/worldwide-transit/transit.py home "Kelowna, BC" --tz America/Vancouver --currency CAD
   ```
   (Use the folder the installer printed.)

3. **Check it live.** Plan one short trip near their home, for example between their city centre and its main station
   or university, and show them the answer:
   ```bash
   python3 <skill folder>/transit.py plan "<a place in their city>" "<another place in their city>" -n 1
   python3 <skill folder>/flights.py selftest && python3 <skill folder>/drive.py selftest
   ```
   If it prints "No public transport route found in Transitous", run the `gtfs.py feeds` command it prints. If that
   lists their local operator, `gtfs.py next <id> "<stop>"` gives exact times. Tell the user which one covers them.

4. **Hand over.** Tell them it is ready and give two or three questions they can ask you, for example "when is the next
   bus home?", "cheapest week in January to fly to Tokyo for 30 days?", "is it cheaper to drive to Vancouver and fly
   from there?". From now on follow
   [SKILL.md](SKILL.md) whenever they ask about transit.

## If you have no shell (a chat-only assistant)

You cannot install it. Tell the user to either hand this repository link to an agent that has a shell (Claude Code,
Codex, Gemini CLI or similar), or paste this into a terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/Bestdoom20/worldwide-transit/main/install.sh | sh
```
