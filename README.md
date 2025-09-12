# DarkNode Discord Bot

This bot manages tmate-based VPS sessions inside Docker.

## Features
- Deploy new VPS sessions with tmate SSH link
- Start, stop, restart, and regenerate SSH
- Restart the bot via command
- System info commands
- Admin-only commands

## Usage

1. Build image:

```bash
docker build -t darknode-bot .
```

2. Run with environment variables:

```bash
docker run -d --name darknode-bot \
  -e DISCORD_TOKEN=YOUR_BOT_TOKEN \
  -e ADMINS=123456789012345678,987654321098765432 \
  darknode-bot
```

Admins should be provided as comma-separated Discord user IDs.
