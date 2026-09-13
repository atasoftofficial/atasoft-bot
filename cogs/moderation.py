"""
cogs/moderation.py
-------------------
Temel moderasyon araçları: ban, tempban, kick, mute (timeout), uyarı, rol ver/al, mesaj sil.
Basic moderation tools: ban, tempban, kick, mute (timeout), warn, add/remove role, purge.
"""

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.embeds import make_embed


def parse_duration(text: str) -> timedelta | None:
    """'10m', '2h', '3d' gibi basit süre metinlerini ayrıştırır.
    Parses simple duration strings like '10m', '2h', '3d'."""
    units = {"m": "minutes", "s": "seconds", "h": "hours", "d": "days"}
    try:
        unit = text[-1].lower()
        value = int(text[:-1])
        if unit not in units or value <= 0:
            return None
        return timedelta(**{units[unit]: value})
    except (ValueError, IndexError):
        return None


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = bot.store  # type: ignore[attr-defined]
        self.expiry_loop.start()

    def cog_unload(self):
        self.expiry_loop.cancel()

    def cfg(self, guild_id: int) -> dict:
        g = self.store.guild(guild_id)
        g.setdefault("moderation", {"warnings": {}, "tempbans": {}})
        return g["moderation"]

    async def dm_safe(self, member: discord.Member, embed: discord.Embed):
        try:
            await member.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass  # DM kapalı olabilir / DMs might be closed

    # ---------- Ban / Kick / Mute ----------

    @app_commands.command(name="banla", description="Bir kullanıcıyı sunucudan yasaklar.")
    @app_commands.describe(kullanici="Yasaklanacak kullanıcı", sebep="Yasaklama sebebi", sure="Örn: 7d, 12h (boş = kalıcı)")
    @app_commands.checks.has_permissions(ban_members=True)
    async def banla(
        self,
        interaction: discord.Interaction,
        kullanici: discord.Member,
        sebep: str = "Sebep belirtilmedi",
        sure: str | None = None,
    ):
        duration = parse_duration(sure) if sure else None
        if sure and duration is None:
            await interaction.response.send_message("❌ Geçersiz süre formatı. Örn: 7d, 12h, 30m", ephemeral=True)
            return

        await self.dm_safe(
            kullanici,
            make_embed(title=f"🔨 {interaction.guild.name} sunucusundan yasaklandın", description=f"Sebep: {sebep}"),
        )
        await interaction.guild.ban(kullanici, reason=f"{interaction.user}: {sebep}")

        if duration:
            cfg = self.cfg(interaction.guild_id)
            unban_at = discord.utils.utcnow() + duration
            cfg.setdefault("tempbans", {})[str(kullanici.id)] = unban_at.timestamp()
            await self.store.save()

        desc = f"{kullanici.mention} yasaklandı.\nSebep: {sebep}"
        if duration:
            desc += f"\nSüre: {sure} (otomatik kalkacak)"
        await interaction.response.send_message(embed=make_embed(title="🔨 Ban", description=desc))

    @app_commands.command(name="yasagikaldir", description="Bir kullanıcının yasağını kaldırır.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def yasagikaldir(self, interaction: discord.Interaction, kullanici_id: str):
        try:
            user = discord.Object(id=int(kullanici_id))
            await interaction.guild.unban(user)
            cfg = self.cfg(interaction.guild_id)
            cfg.get("tempbans", {}).pop(str(kullanici_id), None)
            await self.store.save()
            await interaction.response.send_message("✅ Yasak kaldırıldı.", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ Bu ID yasaklı değil.", ephemeral=True)

    @app_commands.command(name="at", description="Bir kullanıcıyı sunucudan atar (kick).")
    @app_commands.checks.has_permissions(kick_members=True)
    async def at(self, interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
        await self.dm_safe(
            kullanici, make_embed(title=f"👢 {interaction.guild.name} sunucusundan atıldın", description=f"Sebep: {sebep}")
        )
        await kullanici.kick(reason=f"{interaction.user}: {sebep}")
        await interaction.response.send_message(embed=make_embed(title="👢 Kick", description=f"{kullanici.mention} atıldı.\nSebep: {sebep}"))

    @app_commands.command(name="sustur", description="Bir kullanıcıyı belirtilen süre boyunca susturur (timeout).")
    @app_commands.describe(sure="Örn: 10m, 1h, 1d")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def sustur(self, interaction: discord.Interaction, kullanici: discord.Member, sure: str, sebep: str = "Sebep belirtilmedi"):
        duration = parse_duration(sure)
        if duration is None:
            await interaction.response.send_message("❌ Geçersiz süre formatı. Örn: 10m, 1h, 1d", ephemeral=True)
            return
        await kullanici.timeout(duration, reason=f"{interaction.user}: {sebep}")
        await interaction.response.send_message(
            embed=make_embed(title="🔇 Susturuldu", description=f"{kullanici.mention} {sure} boyunca susturuldu.\nSebep: {sebep}")
        )

    @app_commands.command(name="susturmayikaldir", description="Bir kullanıcının susturmasını kaldırır.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def susturmayikaldir(self, interaction: discord.Interaction, kullanici: discord.Member):
        await kullanici.timeout(None, reason=f"{interaction.user} tarafından kaldırıldı")
        await interaction.response.send_message(f"✅ {kullanici.mention} kullanıcısının susturması kaldırıldı.", ephemeral=True)

    # ---------- Uyarı sistemi / Warning system ----------

    @app_commands.command(name="uyar", description="Bir kullanıcıya uyarı verir.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def uyar(self, interaction: discord.Interaction, kullanici: discord.Member, sebep: str):
        cfg = self.cfg(interaction.guild_id)
        warnings = cfg.setdefault("warnings", {}).setdefault(str(kullanici.id), [])
        warnings.append({"sebep": sebep, "yetkili": interaction.user.id, "zaman": discord.utils.utcnow().timestamp()})
        await self.store.save()

        await self.dm_safe(kullanici, make_embed(title=f"⚠️ {interaction.guild.name} sunucusunda uyarıldın", description=sebep))
        await interaction.response.send_message(
            embed=make_embed(title="⚠️ Uyarı", description=f"{kullanici.mention} uyarıldı. (Toplam: {len(warnings)})\nSebep: {sebep}")
        )

    @app_commands.command(name="uyarilar", description="Bir kullanıcının uyarılarını listeler.")
    async def uyarilar(self, interaction: discord.Interaction, kullanici: discord.Member):
        cfg = self.cfg(interaction.guild_id)
        warnings = cfg.get("warnings", {}).get(str(kullanici.id), [])
        if not warnings:
            await interaction.response.send_message("Bu kullanıcının uyarısı yok.", ephemeral=True)
            return
        desc = "\n".join(f"**{i + 1}.** {w['sebep']} — <@{w['yetkili']}>" for i, w in enumerate(warnings))
        await interaction.response.send_message(embed=make_embed(title=f"⚠️ {kullanici.display_name} — Uyarılar", description=desc))

    # ---------- Rol ver / al ----------

    @app_commands.command(name="rolver", description="Bir kullanıcıya rol verir.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def rolver(self, interaction: discord.Interaction, kullanici: discord.Member, rol: discord.Role):
        await kullanici.add_roles(rol, reason=f"{interaction.user} tarafından verildi")
        await interaction.response.send_message(f"✅ {rol.mention} rolü {kullanici.mention} kullanıcısına verildi.", ephemeral=True)

    @app_commands.command(name="rolal", description="Bir kullanıcıdan rol alır.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def rolal(self, interaction: discord.Interaction, kullanici: discord.Member, rol: discord.Role):
        await kullanici.remove_roles(rol, reason=f"{interaction.user} tarafından alındı")
        await interaction.response.send_message(f"✅ {rol.mention} rolü {kullanici.mention} kullanıcısından alındı.", ephemeral=True)

    # ---------- Mesaj sil ----------

    @app_commands.command(name="mesajsil", description="Bu kanaldan belirtilen sayıda mesajı siler.")
    @app_commands.describe(adet="Silinecek mesaj sayısı (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def mesajsil(self, interaction: discord.Interaction, adet: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=adet)
        await interaction.followup.send(f"🧹 {len(deleted)} mesaj silindi.", ephemeral=True)

    # ---------- Süreli ban süresi dolunca otomatik kaldırma / Tempban expiry ----------

    @tasks.loop(minutes=5)
    async def expiry_loop(self):
        now = discord.utils.utcnow().timestamp()
        for guild in self.bot.guilds:
            cfg = self.cfg(guild.id)
            tempbans = cfg.get("tempbans", {})
            for user_id, expires_at in list(tempbans.items()):
                if now >= expires_at:
                    try:
                        await guild.unban(discord.Object(id=int(user_id)), reason="Süreli ban süresi doldu")
                    except discord.NotFound:
                        pass
                    tempbans.pop(user_id, None)
            if tempbans != cfg.get("tempbans", {}):
                await self.store.save()

    @expiry_loop.before_loop
    async def _before_expiry_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
