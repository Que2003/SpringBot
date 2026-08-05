# SpringBot Realtime

SpringBot is a Discord community assistant with AI chat, moderation, support tickets, reminders, study tools, music, server utilities, and a lightweight health service for Railway.

## Current runtime

Production starts with:

```bash
python springbot_runtime.py
```

The runtime loads the existing `bot_v2.py` commands and adds reliability monitoring plus newer community features.

## New in SpringBot 2.1

- `!ping`, `!status`, or `!health` — show Discord connection, latency, uptime, database status, and AI status
- `!diagnose` — admin-only configuration checks
- `!poll Question | Option 1 | Option 2` — reaction polls with up to 10 options
- `!setwelcome [#channel]` and `!welcomeoff` — automatic welcome messages
- `!close` — close a SpringBot support ticket
- `!feedback <message>` — save feature requests and feedback
- `/health` — Railway health endpoint that reports whether Discord and the database are ready
- Automatic reconnect logging and deployment health checks

## Existing features

- AI chat, memory, brainstorming, channel summaries, and project planning
- Moderation scans, incident history, scam detection, and server health recommendations
- Support tickets and reminders
- Knowledge-base and study commands
- Voice playback through radio and direct-stream commands
- Live RSS news, web summaries, and information commands

## Required environment variables

- `DISCORD_TOKEN` — required
- `OPENAI_API_KEY` — optional; enables AI features
- `OPENAI_MODEL` — optional
- `SPRINGBOT_PREFIX` — optional, defaults to `!`
- `SPRINGBOT_DB` — optional SQLite path; use a Railway Volume for persistent data
- `PORT` — supplied by Railway

The Discord Developer Portal must have **Message Content Intent** enabled. **Server Members Intent** is also required for automatic welcome messages.

## Useful commands

```text
!v2help
!ping
!diagnose
!ticket I need help
!close
!poll Best study time? | Morning | Evening
!setwelcome #welcome
!remind 30m check the server
!springai Explain DNS simply
```

## Railway deployment

The repository uses its root `Dockerfile`, starts `springbot_runtime.py`, exposes `/health`, installs FFmpeg for voice features, and restarts failed processes according to `railway.json`.
