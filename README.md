# Colon-3 Bot

A Discord bot that lets you designate a channel where every message must be
some form of `:3`. Anything else gets deleted and the author is notified.

## Setup

1. Create a bot application at https://discord.com/developers/applications
   - Under **Bot**, enable the **Message Content Intent** and the
     **Server Members Intent** (both are required for this bot to work).
   - Copy the bot token.
2. Invite the bot to your server using the OAuth2 URL generator, with scopes
   `bot` and `applications.commands`, and permissions: `Read Messages/View
   Channels`, `Send Messages`, `Manage Messages`, `Read Message History`.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your token:
   ```bash
   cp .env.example .env
   ```
   ```env
   DISCORD_BOT_TOKEN=your-token-here
   ```
5. Run the bot:
   ```bash
   python bot.py
   ```

`.env` and `config.json` are listed in `.gitignore` so your token and
server settings don't end up committed if you put this in a repo.

Settings are stored in `config.json` next to `bot.py`, and persist across
restarts.

## Commands

- `/set-colon3-tag role:<@role>` — Set which role is allowed to manage
  colon-3 settings (in addition to Administrators). Only Administrators can
  run this until a tag role has been set.
- `/set-colon3 channel:<#channel>` — Mark a channel as the `:3`-only
  channel for this server.
- `/unset-colon3` — Remove the restriction.
- `/set-colon3-log channel:<#channel>` — Send a log embed to this channel
  every time a message is deleted (who, which channel, the content, and any
  attachment names).
- `/unset-colon3-log` — Turn deletion logging off.

## What counts as valid ":3"

After trimming only leading/trailing whitespace (no whitespace allowed in
the middle), the message must match one of:

- `:3`, `:33`, `:333`, ... 
- `=3`, `=33`, `=333`, ...
- `:>3`, `:>33`, `:>333`, ...
- `;3`, `;33`, `;333`, ...

Attachments/images are allowed *alongside* valid `:3` text, but a message
with only an attachment and no valid text is still deleted.

## A note on the "ephemeral" warning

True ephemeral messages (visible only to the sender) are a feature of slash
command interactions — they don't exist for ordinary messages a user types
in a channel. Since the offending message here isn't a slash command, the
bot can't reply to it ephemerally. Instead, it DMs the user privately, which
is the closest equivalent. If the user has DMs disabled, it falls back to a
message in the channel that mentions them and auto-deletes after 5 seconds.