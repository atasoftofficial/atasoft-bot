"""
utils/embeds.py
----------------
Tüm cog'ların kullandığı ortak embed stili.
Common embed styling used across all cogs.
"""

import discord
from datetime import datetime, timezone

BRAND_NAME = "AtasoftBot"
BRAND_COLOR = discord.Color.blurple()


def make_embed(
    title: str | None = None,
    description: str | None = None,
    color: discord.Color | None = None,
    footer: str | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or BRAND_COLOR,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=footer or BRAND_NAME)
    return embed
