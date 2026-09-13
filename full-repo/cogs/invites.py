"""
cogs/invites.py
----------------
Davet Takip Sistemi
Invite Tracking System

Bot açılışta her sunucunun davet kullanım sayılarını önbelleğe alır. Yeni bir üye
katıldığında, hangi davetin kullanıldığını bulmak için önbellekle güncel durumu
karşılaştırır ve kim tarafından davet edildiğini bildirir.

On startup, the bot caches each guild's invite usage counts. When a new member
joins, it diffs the cache against the current state to figure out which invite
was used, then announces who invited whom.
"""

import discord
from discord.ext import commands

from utils.embeds import make_embed


class Invites(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = bot.store  # type: ignore[attr-defined]
        self.invite_cache: dict[int, dict[str, int]] = {}  # guild_id -> {invite_code: uses}

    def cfg(self, guild_id: int) -> dict:
        g = self.store.guild(guild_id)
        g.setdefault("invites", {"log_channel_id": None, "inviter_of": {}})
        return g["invites"]

    async def _cache_guild_invites(self, guild: discord.Guild):
        try:
            invites = await guild.invites()
            self.invite_cache[guild.id] = {inv.code: inv.uses or 0 for inv in invites}
        except discord.Forbidden:
            self.invite_cache[guild.id] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self._cache_guild_invites(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        self.invite_cache.setdefault(invite.guild.id, {})[invite.code] = invite.uses or 0

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        self.invite_cache.get(invite.guild.id, {}).pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        before = self.invite_cache.get(guild.id, {})
        used_invite = None
        try:
            current_invites = await guild.invites()
        except discord.Forbidden:
            current_invites = []

        for invite in current_invites:
            if invite.uses and invite.uses > before.get(invite.code, 0):
                used_invite = invite
                break

        await self._cache_guild_invites(guild)

        cfg = self.cfg(guild.id)
        if used_invite and used_invite.inviter:
            cfg.setdefault("inviter_of", {})[str(member.id)] = used_invite.inviter.id
            await self.store.save()

            channel_id = cfg.get("log_channel_id")
            channel = guild.get_channel(channel_id) if channel_id else None
            if channel:
                await channel.send(
                    embed=make_embed(
                        title="📨 Yeni Üye / New Member",
                        description=(
                            f"{member.mention}, **{used_invite.inviter.mention}** kişisinin davetiyle katıldı "
                            f"(kod: `{used_invite.code}`, kullanım: {used_invite.uses})."
                        ),
                    )
                )

    @discord.app_commands.command(name="davetkanali", description="Davet bildirimlerinin gönderileceği kanalı ayarlar.")
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def davetkanali(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        self.cfg(interaction.guild_id)["log_channel_id"] = kanal.id
        await self.store.save()
        await interaction.response.send_message(f"✅ Davet log kanalı: {kanal.mention}", ephemeral=True)

    @discord.app_commands.command(name="davetedenkim", description="Bir üyeyi kimin davet ettiğini gösterir.")
    async def davetedenkim(self, interaction: discord.Interaction, kullanici: discord.Member):
        cfg = self.cfg(interaction.guild_id)
        inviter_id = cfg.get("inviter_of", {}).get(str(kullanici.id))
        if not inviter_id:
            await interaction.response.send_message("Bu üyenin davetçisi kayıtlı değil.", ephemeral=True)
            return
        await interaction.response.send_message(f"{kullanici.mention} kişisini <@{inviter_id}> davet etti.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Invites(bot))
