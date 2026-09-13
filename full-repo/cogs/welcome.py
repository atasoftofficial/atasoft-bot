"""
cogs/welcome.py
----------------
Giriş/Çıkış mesajları + Otorol + Saatlik Selam + Otomatik Mesaj
Join/Leave messages + Auto-role + Hourly greeting + Scheduled auto-message
"""

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.embeds import make_embed


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = bot.store  # type: ignore[attr-defined]
        self.hourly_greeting_loop.start()
        self.auto_message_loop.start()

    def cog_unload(self):
        self.hourly_greeting_loop.cancel()
        self.auto_message_loop.cancel()

    def cfg(self, guild_id: int) -> dict:
        g = self.store.guild(guild_id)
        g.setdefault(
            "welcome",
            {
                "join_leave_channel_id": None,
                "welcome_text": "{mention} sunucuya hoş geldin! 🎉",
                "leave_text": "{name} sunucudan ayrıldı. 👋",
                "auto_role_id": None,
                "greeting_channel_id": None,
                "greeting_last_hour": None,
                "auto_message_channel_id": None,
                "auto_message_text": None,
                "auto_message_interval_minutes": 60,
            },
        )
        return g["welcome"]

    # ---------- Join / Leave ----------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = self.cfg(member.guild.id)

        role_id = cfg.get("auto_role_id")
        if role_id:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role, reason="Otorol / Auto-role")
                except discord.Forbidden:
                    pass

        channel_id = cfg.get("join_leave_channel_id")
        channel = member.guild.get_channel(channel_id) if channel_id else None
        if channel:
            text = cfg.get("welcome_text", "").format(mention=member.mention, name=member.display_name)
            await channel.send(embed=make_embed(title="👋 Hoş Geldin! / Welcome!", description=text))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        cfg = self.cfg(member.guild.id)
        channel_id = cfg.get("join_leave_channel_id")
        channel = member.guild.get_channel(channel_id) if channel_id else None
        if channel:
            text = cfg.get("leave_text", "").format(mention=member.mention, name=member.display_name)
            await channel.send(embed=make_embed(title="😢 Görüşürüz / Goodbye", description=text))

    # ---------- Saatlik selam / Hourly greeting ----------

    @tasks.loop(minutes=15)
    async def hourly_greeting_loop(self):
        """Her saat başı, ayarlanmış kanala Türkiye saatine göre bir selam mesajı atar.
        Every hour on the hour, sends a greeting to the configured channel (based on server time)."""
        now = datetime.now(timezone.utc)
        if now.minute >= 15:
            return  # sadece saat başına yakın çalış / only fire near the top of the hour

        for guild in self.bot.guilds:
            cfg = self.cfg(guild.id)
            channel_id = cfg.get("greeting_channel_id")
            if not channel_id:
                continue
            if cfg.get("greeting_last_hour") == now.hour:
                continue
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            hour = now.hour
            if 5 <= hour < 12:
                text = "☀️ Günaydın! / Good morning!"
            elif 12 <= hour < 18:
                text = "🌤️ İyi günler! / Good afternoon!"
            elif 18 <= hour < 23:
                text = "🌆 İyi akşamlar! / Good evening!"
            else:
                text = "🌙 İyi geceler! / Good night!"
            await channel.send(embed=make_embed(title="🕒 Saatlik Selam", description=text))
            cfg["greeting_last_hour"] = now.hour
            await self.store.save()

    @hourly_greeting_loop.before_loop
    async def _before_greeting(self):
        await self.bot.wait_until_ready()

    # ---------- Otomatik mesaj / Auto message ----------

    @tasks.loop(minutes=10)
    async def auto_message_loop(self):
        now_ts = discord.utils.utcnow().timestamp()
        for guild in self.bot.guilds:
            cfg = self.cfg(guild.id)
            channel_id = cfg.get("auto_message_channel_id")
            text = cfg.get("auto_message_text")
            interval = int(cfg.get("auto_message_interval_minutes", 60))
            if not channel_id or not text:
                continue
            last_sent = cfg.get("auto_message_last_sent", 0)
            if now_ts - last_sent < interval * 60:
                continue
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.send(embed=make_embed(title="📢 Duyuru / Announcement", description=text))
                cfg["auto_message_last_sent"] = now_ts
                await self.store.save()

    @auto_message_loop.before_loop
    async def _before_auto_message(self):
        await self.bot.wait_until_ready()

    # ---------- Komutlar / Commands ----------

    @app_commands.command(name="giriscikiskanali", description="Giriş/çıkış mesajlarının atılacağı kanalı ayarlar.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giriscikiskanali(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        self.cfg(interaction.guild_id)["join_leave_channel_id"] = kanal.id
        await self.store.save()
        await interaction.response.send_message(f"✅ Giriş/çıkış kanalı: {kanal.mention}", ephemeral=True)

    @app_commands.command(name="otorol", description="Sunucuya katılanlara otomatik verilecek rolü ayarlar.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def otorol(self, interaction: discord.Interaction, rol: discord.Role):
        self.cfg(interaction.guild_id)["auto_role_id"] = rol.id
        await self.store.save()
        await interaction.response.send_message(f"✅ Otorol: {rol.mention}", ephemeral=True)

    @app_commands.command(name="selamkanali", description="Saatlik selam mesajlarının atılacağı kanalı ayarlar.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def selamkanali(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        self.cfg(interaction.guild_id)["greeting_channel_id"] = kanal.id
        await self.store.save()
        await interaction.response.send_message(f"✅ Selam kanalı: {kanal.mention}", ephemeral=True)

    @app_commands.command(name="otomesaj", description="Belirli aralıklarla otomatik mesaj atılmasını ayarlar.")
    @app_commands.describe(kanal="Mesajın atılacağı kanal", metin="Mesaj içeriği", dakika="Kaç dakikada bir atılsın")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def otomesaj(self, interaction: discord.Interaction, kanal: discord.TextChannel, metin: str, dakika: int = 60):
        cfg = self.cfg(interaction.guild_id)
        cfg["auto_message_channel_id"] = kanal.id
        cfg["auto_message_text"] = metin
        cfg["auto_message_interval_minutes"] = max(10, dakika)
        await self.store.save()
        await interaction.response.send_message(f"✅ Otomatik mesaj her {dakika} dakikada bir {kanal.mention} kanalına atılacak.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
