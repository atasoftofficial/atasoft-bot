"""
main.py
-------
AtasoftBot (açık kaynak / gösterim sürümü) — giriş noktası.
AtasoftBot (open-source / showcase edition) — entry point.

Token'ı asla kodun içine yazma; ortam değişkeni kullan.
Never hardcode your token; use an environment variable.

    export ATASOFTBOT_TOKEN="your-token-here"      # Linux / macOS
    setx ATASOFTBOT_TOKEN "your-token-here"         # Windows
"""

import asyncio
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from utils.storage import JsonStore

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
log = logging.getLogger("AtasoftBot")

TOKEN = os.getenv("ATASOFTBOT_TOKEN")
COMMAND_PREFIX = os.getenv("ATASOFTBOT_PREFIX", "!")

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True
INTENTS.voice_states = True

EXTENSIONS = [
    "cogs.onboarding",      # Kayıt sistemi + kurallar / Registration + rules
    "cogs.moderation",      # Ban / kick / mute / uyarı / rol / mesaj sil
    "cogs.leveling",        # Metin + ses XP, seviye rütbeleri
    "cogs.welcome",         # Giriş-çıkış, otorol, saatli selam, otomesaj
    "cogs.tickets",         # Destek talebi (ticket) sistemi
    "cogs.suggestions",     # Öneri, anket, self-rol menüsü
    "cogs.private_rooms",   # Katılınca oluşan özel ses odaları
    "cogs.invites",         # Davet takip sistemi
    "cogs.minecraft_status",  # Minecraft sunucu durum kanalı
]


class AtasoftBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=COMMAND_PREFIX, intents=INTENTS, help_command=None)
        self.store = JsonStore(os.getenv("ATASOFTBOT_DATA_PATH", "data/guilds.json"))

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
                log.info("Yüklendi / Loaded: %s", extension)
            except Exception:
                log.exception("Yüklenemedi / Failed to load: %s", extension)
        try:
            synced = await self.tree.sync()
            log.info("%d slash komut senkronize edildi / synced.", len(synced))
        except Exception:
            log.exception("Slash komutlar senkronize edilemedi / Slash command sync failed.")

    async def on_ready(self):
        log.info("Giriş yapıldı: %s (id: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="/yardim")
        )


async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ Bu komutu kullanmak için yeterli iznin yok. / You don't have permission to use this command."
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = f"⏳ Çok hızlısın, {error.retry_after:.0f} saniye bekle. / Slow down, try again in {error.retry_after:.0f}s."
    else:
        log.exception("Slash komut hatası / Slash command error", exc_info=error)
        message = "⚠️ Beklenmeyen bir hata oluştu. / An unexpected error occurred."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


async def main():
    if not TOKEN:
        raise RuntimeError(
            "ATASOFTBOT_TOKEN bulunamadı. .env dosyasına veya ortam değişkenine ekleyin.\n"
            "ATASOFTBOT_TOKEN not found. Add it to your .env file or environment variables."
        )
    bot = AtasoftBot()
    bot.tree.on_error = on_app_command_error
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
