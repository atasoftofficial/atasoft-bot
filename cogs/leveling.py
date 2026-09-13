"""
cogs/leveling.py
-----------------
Metin mesajı + sesli sohbet süresine dayalı XP / seviye sistemi.
Message-based and voice-time-based XP / leveling system.

- Her mesaj için rastgele XP (spam'i önlemek için kısa cooldown ile).
  Random XP per message, with a short per-user cooldown to discourage spam.
- Sesli kanalda geçirilen her dakika için XP.
  XP for every minute spent in a voice channel.
- Seviye atlayınca duyuru + opsiyonel rol ödülü.
  Level-up announcement + optional role reward.
"""

import random
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.embeds import make_embed

XP_PER_MESSAGE = (15, 25)          # min-max XP per message
MESSAGE_COOLDOWN_SECONDS = 60
XP_PER_VOICE_MINUTE = 10


def xp_for_level(level: int) -> int:
    """Basit artan eğri: her seviye bir öncekinden biraz daha zor.
    Simple increasing curve: each level needs a bit more XP than the last."""
    return 5 * (level ** 2) + 50 * level + 100


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = bot.store  # type: ignore[attr-defined]
        self._last_message_at: dict[tuple[int, int], float] = {}
        self._voice_join_at: dict[tuple[int, int], float] = {}
        self.voice_xp_loop.start()

    def cog_unload(self):
        self.voice_xp_loop.cancel()

    # ---------- Depolama / Storage ----------

    def cfg(self, guild_id: int) -> dict:
        g = self.store.guild(guild_id)
        g.setdefault("leveling", {"users": {}, "announce_channel_id": None, "level_roles": {}})
        return g["leveling"]

    def user_data(self, guild_id: int, user_id: int) -> dict:
        cfg = self.cfg(guild_id)
        return cfg["users"].setdefault(str(user_id), {"xp": 0, "level": 0})

    # ---------- XP mantığı / XP logic ----------

    async def add_xp(self, member: discord.Member, amount: int):
        cfg = self.cfg(member.guild.id)
        data = self.user_data(member.guild.id, member.id)
        data["xp"] += amount

        needed = xp_for_level(data["level"])
        leveled_up = False
        while data["xp"] >= needed:
            data["xp"] -= needed
            data["level"] += 1
            leveled_up = True
            needed = xp_for_level(data["level"])

        await self.store.save()

        if leveled_up:
            await self._announce_level_up(member, data["level"])
            await self._apply_level_role(member, data["level"])

    async def _announce_level_up(self, member: discord.Member, level: int):
        cfg = self.cfg(member.guild.id)
        channel_id = cfg.get("announce_channel_id")
        channel = member.guild.get_channel(channel_id) if channel_id else None
        embed = make_embed(
            title="⬆️ Seviye Atladın! / Level Up!",
            description=f"{member.mention} artık **Seviye {level}**!",
        )
        if channel:
            await channel.send(embed=embed)

    async def _apply_level_role(self, member: discord.Member, level: int):
        cfg = self.cfg(member.guild.id)
        role_id = cfg.get("level_roles", {}).get(str(level))
        if not role_id:
            return
        role = member.guild.get_role(int(role_id))
        if role:
            try:
                await member.add_roles(role, reason=f"Seviye {level} ödülü / Level {level} reward")
            except discord.Forbidden:
                pass

    # ---------- Event listener'lar / Event listeners ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        key = (message.guild.id, message.author.id)
        now = time.time()
        if now - self._last_message_at.get(key, 0) < MESSAGE_COOLDOWN_SECONDS:
            return
        self._last_message_at[key] = now
        await self.add_xp(message.author, random.randint(*XP_PER_MESSAGE))

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        key = (member.guild.id, member.id)
        # Kanala katıldı / joined a channel
        if before.channel is None and after.channel is not None:
            self._voice_join_at[key] = time.time()
        # Kanaldan ayrıldı / left a channel
        elif before.channel is not None and after.channel is None:
            joined_at = self._voice_join_at.pop(key, None)
            if joined_at:
                minutes = int((time.time() - joined_at) // 60)
                if minutes > 0:
                    await self.add_xp(member, minutes * XP_PER_VOICE_MINUTE)

    @tasks.loop(minutes=5)
    async def voice_xp_loop(self):
        """Uzun süre sesli kalanlara periyodik XP verir (ayrılmayı beklemeden).
        Periodically grants XP to users who stay in voice a long time (without waiting for them to leave)."""
        now = time.time()
        for key, joined_at in list(self._voice_join_at.items()):
            guild_id, user_id = key
            minutes = int((now - joined_at) // 60)
            if minutes <= 0:
                continue
            guild = self.bot.get_guild(guild_id)
            member = guild.get_member(user_id) if guild else None
            if member:
                await self.add_xp(member, minutes * XP_PER_VOICE_MINUTE)
            self._voice_join_at[key] = now

    @voice_xp_loop.before_loop
    async def _before_voice_xp_loop(self):
        await self.bot.wait_until_ready()

    # ---------- Komutlar / Commands ----------

    @app_commands.command(name="seviye", description="Seviye ve XP bilgini gösterir.")
    async def seviye(self, interaction: discord.Interaction, kullanici: discord.Member | None = None):
        target = kullanici or interaction.user
        data = self.user_data(interaction.guild_id, target.id)
        needed = xp_for_level(data["level"])
        embed = make_embed(title=f"📊 {target.display_name} — Seviye {data['level']}")
        embed.add_field(name="XP", value=f"{data['xp']} / {needed}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="seviye-kanali", description="Seviye atlama duyurularının yapılacağı kanalı ayarlar.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def seviye_kanali(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        cfg = self.cfg(interaction.guild_id)
        cfg["announce_channel_id"] = kanal.id
        await self.store.save()
        await interaction.response.send_message(f"✅ Seviye duyuru kanalı: {kanal.mention}", ephemeral=True)

    @app_commands.command(name="seviye-rol-ekle", description="Belirli bir seviyeye ulaşınca verilecek rolü ayarlar.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def seviye_rol_ekle(self, interaction: discord.Interaction, seviye: int, rol: discord.Role):
        cfg = self.cfg(interaction.guild_id)
        cfg.setdefault("level_roles", {})[str(seviye)] = rol.id
        await self.store.save()
        await interaction.response.send_message(f"✅ Seviye {seviye} → {rol.mention}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
