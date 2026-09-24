"""
Colon-3 Bot
-----------
A Discord bot that lets you designate a channel where every message must be
some form of ":3" (or a recognized variant). Anything else gets deleted and
the author gets a DM explaining why.

Setup commands (slash commands):
    /set-colon3-tag role:<@role>     - Set which role is allowed to manage
                                        colon-3 settings. Only usable by an
                                        Administrator, or by someone who
                                        already holds the current tag role.
    /set-colon3 channel:<#channel>   - Mark a channel as the colon-3-only
                                        channel for this server.
    /unset-colon3                    - Remove the colon-3 restriction for
                                        this server.

Permission model:
    - Each guild can have one "tag" role stored in config.json.
    - If a tag role IS set, only members with that role (or Administrators)
      can run /set-colon3 and /set-colon3-tag.
    - If NO tag role is set yet, only server Administrators can run those
      commands (this is the bootstrap fallback).

Message validation:
    A message in the colon-3 channel is allowed if, after stripping ONLY
    leading/trailing whitespace (no whitespace allowed in the middle), its
    text content matches one of:
        :3   :33   :333  ...   (":" followed by one or more "3"s)
        =3   =33   =333  ...   ("=" followed by one or more "3"s)
        :>3  :>33  :>333 ...   (":>" followed by one or more "3"s)
        ;3   ;33   ;333  ...   (";" followed by one or more "3"s)
    Attachments/images are allowed ALONGSIDE valid text, but a message with
    an attachment and NO text (or invalid text) is still deleted -- the
    ":3" text is always required.

Important note on "ephemeral" warnings:
    True ephemeral messages ("only the sender sees this") are a feature of
    Discord's slash-command *interactions* -- they don't exist for normal
    messages sent by a regular user in a channel. Since the message being
    moderated here is an ordinary user message (not a slash command), the
    bot can't reply to it ephemerally. The closest equivalent -- and what
    this bot does -- is to DM the user privately. If the user has DMs
    disabled, the bot falls back to a channel message that auto-deletes
    after a few seconds, so at least something is visible.
"""

import json
import os
import re
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()  # Loads variables from a .env file in the working directory

CONFIG_PATH = Path(__file__).parent / "config.json"

# Patterns for valid ":3" content. Each is anchored to match the WHOLE
# trimmed string (no partial matches, no internal whitespace allowed since
# whitespace isn't part of any of these character classes).
VALID_PATTERNS = [
    re.compile(r"^:3+$"),
    re.compile(r"^=3+$"),
    re.compile(r"^:>3+$"),
    re.compile(r"^;3+$"),
]


def is_valid_colon3(content: str) -> bool:
    """Return True if the message content (after trimming only leading/
    trailing whitespace) matches one of the allowed :3 variants."""
    stripped = content.strip()
    if not stripped:
        return False
    return any(pattern.match(stripped) for pattern in VALID_PATTERNS)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_guild_config(config: dict, guild_id: int) -> dict:
    guild_conf = config.setdefault(
        str(guild_id), {"channel_id": None, "tag_role_id": None, "log_channel_id": None}
    )
    # Backfill the key for configs saved before logging existed.
    guild_conf.setdefault("log_channel_id", None)
    return guild_conf


intents = discord.Intents.default()
intents.message_content = True  # Required to read message text
intents.members = True  # Required to reliably resolve roles/DM users

bot = commands.Bot(command_prefix="!unused-", intents=intents)
# We only use slash commands; the prefix above is arbitrary and unused.


def can_manage_colon3(member: discord.Member, guild_conf: dict) -> bool:
    """Permission check shared by all setup commands."""
    if member.guild_permissions.administrator:
        return True
    tag_role_id = guild_conf.get("tag_role_id")
    if tag_role_id is not None:
        return any(role.id == tag_role_id for role in member.roles)
    # No tag role configured yet -> only admins (already checked above).
    return False


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Logged in as {bot.user}. Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.tree.command(name="set-colon3-tag", description="Set the role allowed to manage colon-3 settings.")
@app_commands.describe(role="The role that should be allowed to configure the colon-3 channel.")
async def set_colon3_tag(interaction: discord.Interaction, role: discord.Role):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    config = load_config()
    guild_conf = get_guild_config(config, interaction.guild.id)

    member = interaction.user
    if not isinstance(member, discord.Member):
        member = interaction.guild.get_member(interaction.user.id)

    if not can_manage_colon3(member, guild_conf):
        await interaction.response.send_message(
            "You don't have permission to do that. You need to be an Administrator, "
            "or hold the currently configured tag role.",
            ephemeral=True,
        )
        return

    guild_conf["tag_role_id"] = role.id
    save_config(config)

    await interaction.response.send_message(
        f"Done. Members with {role.mention} (or Administrators) can now manage colon-3 settings.",
        ephemeral=True,
    )


@bot.tree.command(name="set-colon3", description="Mark a channel as the :3-only channel.")
@app_commands.describe(channel="The text channel where only :3 will be allowed.")
async def set_colon3(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    config = load_config()
    guild_conf = get_guild_config(config, interaction.guild.id)

    member = interaction.user
    if not isinstance(member, discord.Member):
        member = interaction.guild.get_member(interaction.user.id)

    if not can_manage_colon3(member, guild_conf):
        await interaction.response.send_message(
            "You don't have permission to do that. You need to be an Administrator, "
            "or hold the currently configured tag role.",
            ephemeral=True,
        )
        return

    guild_conf["channel_id"] = channel.id
    save_config(config)

    await interaction.response.send_message(
        f"{channel.mention} is now a :3-only channel. Any message there that isn't "
        f"a valid :3 (or variant like =3, :33, :>3, ;3...) will be deleted.",
        ephemeral=True,
    )


@bot.tree.command(name="set-colon3-log", description="Set a channel where deleted-message logs are sent.")
@app_commands.describe(channel="The text channel where deletion logs should be posted.")
async def set_colon3_log(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    config = load_config()
    guild_conf = get_guild_config(config, interaction.guild.id)

    member = interaction.user
    if not isinstance(member, discord.Member):
        member = interaction.guild.get_member(interaction.user.id)

    if not can_manage_colon3(member, guild_conf):
        await interaction.response.send_message(
            "You don't have permission to do that. You need to be an Administrator, "
            "or hold the currently configured tag role.",
            ephemeral=True,
        )
        return

    guild_conf["log_channel_id"] = channel.id
    save_config(config)

    await interaction.response.send_message(
        f"Deletion logs will now be posted in {channel.mention}.",
        ephemeral=True,
    )


@bot.tree.command(name="unset-colon3-log", description="Stop logging deleted colon-3 messages.")
async def unset_colon3_log(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    config = load_config()
    guild_conf = get_guild_config(config, interaction.guild.id)

    member = interaction.user
    if not isinstance(member, discord.Member):
        member = interaction.guild.get_member(interaction.user.id)

    if not can_manage_colon3(member, guild_conf):
        await interaction.response.send_message(
            "You don't have permission to do that. You need to be an Administrator, "
            "or hold the currently configured tag role.",
            ephemeral=True,
        )
        return

    guild_conf["log_channel_id"] = None
    save_config(config)

    await interaction.response.send_message("Deletion logging has been turned off.", ephemeral=True)


@bot.tree.command(name="unset-colon3", description="Remove the :3-only restriction for this server.")
async def unset_colon3(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    config = load_config()
    guild_conf = get_guild_config(config, interaction.guild.id)

    member = interaction.user
    if not isinstance(member, discord.Member):
        member = interaction.guild.get_member(interaction.user.id)

    if not can_manage_colon3(member, guild_conf):
        await interaction.response.send_message(
            "You don't have permission to do that. You need to be an Administrator, "
            "or hold the currently configured tag role.",
            ephemeral=True,
        )
        return

    guild_conf["channel_id"] = None
    save_config(config)

    await interaction.response.send_message("The :3-only restriction has been removed.", ephemeral=True)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    config = load_config()
    guild_conf = config.get(str(message.guild.id))
    if not guild_conf or guild_conf.get("channel_id") != message.channel.id:
        return

    if is_valid_colon3(message.content):
        return

    # Invalid message in the colon-3 channel: delete it and notify the user.
    try:
        await message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass

    warning = (
        f"Your message in **#{message.channel.name}** (in **{message.guild.name}**) was removed. "
        "You can only post \":3\" (or a variant like =3, :33, :>3, ;3...) in that channel."
    )

    try:
        await message.author.send(warning)
    except discord.Forbidden:
        # DMs closed -- fall back to a self-deleting channel message.
        try:
            notice = await message.channel.send(f"{message.author.mention} {warning}")
            await notice.delete(delay=5)
        except discord.Forbidden:
            pass

    log_channel_id = guild_conf.get("log_channel_id")
    if log_channel_id:
        log_channel = message.guild.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(
                title="Colon-3 message deleted",
                color=discord.Color.red(),
                timestamp=message.created_at,
            )
            embed.add_field(name="User", value=f"{message.author.mention} ({message.author})", inline=False)
            embed.add_field(name="Channel", value=message.channel.mention, inline=False)
            content_preview = message.content if message.content else "*(no text content)*"
            if len(content_preview) > 1000:
                content_preview = content_preview[:1000] + "…"
            embed.add_field(name="Content", value=content_preview, inline=False)
            if message.attachments:
                embed.add_field(
                    name="Attachments",
                    value=", ".join(a.filename for a in message.attachments),
                    inline=False,
                )
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

    await bot.process_commands(message)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Set the DISCORD_BOT_TOKEN environment variable to your bot's token before running."
        )
    bot.run(token)