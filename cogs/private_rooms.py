"""
cogs/private_rooms.py
----------------------
Özel Oda Sistemi (Join to Create)
Private Voice Room System (Join to Create)

Kullanıcı belirlenen "oluşturucu" kanala katılınca, ona özel yeni bir ses kanalı
açılır ve otomatik olarak oraya taşınır. Kanal sahibi ismini/limitini değiştirebilir.
Kanal boşalınca otomatik silinir.

When a user joins the designated "creator" channel, a new voice channel is
created for them and they're moved into it automatically. The owner can rename
it or set a user limit. The channel is deleted automatically once it's empty.
"""

import discord
from discord import app_commands
from discord.ext import commands


class PrivateRooms(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = bot.store  # type: ignore[attr-defined]

    def cfg(self, guild_id: int) -> dict:
        g = self.store.guild(guild_id)
        g.setdefault("private_rooms", {"creator_channel_id": None, "category_id": None, "owned_channels": {}})
        return g["private_rooms"]

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        cfg = self.cfg(member.guild.id)
        creator_id = cfg.get("creator_channel_id")

        # Oluşturucu kanala katıldı / joined the creator channel
        if creator_id and after.channel and after.channel.id == creator_id:
            category = member.guild.get_channel(cfg["category_id"]) if cfg.get("category_id") else after.channel.category
            new_channel = await member.guild.create_voice_channel(
                name=f"🔊 {member.display_name}'nin Odası",
                category=category,
                overwrites={
                    member: discord.PermissionOverwrite(manage_channels=True, move_members=True, connect=True),
                },
                reason="Özel oda oluşturuldu / Private room created",
            )
            cfg.setdefault("owned_channels", {})[str(new_channel.id)] = member.id
            await self.store.save()
            try:
                await member.move_to(new_channel)
            except discord.HTTPException:
                pass

        # Bir kanaldan ayrıldı, boşaldıysa ve bizim oluşturduğumuz özel bir odaysa sil
        # Left a channel; if it's now empty and it's one of our private rooms, delete it
        if before.channel and str(before.channel.id) in cfg.get("owned_channels", {}):
            if len(before.channel.members) == 0:
                cfg["owned_channels"].pop(str(before.channel.id), None)
                await self.store.save()
                try:
                    await before.channel.delete(reason="Özel oda boşaldı / Private room emptied")
                except discord.HTTPException:
                    pass

    @app_commands.command(name="ozelodaayarla", description="Özel oda oluşturucu kanalı ve kategoriyi ayarlar.")
    @app_commands.describe(olusturucu_kanal="Kullanıcıların katılınca oda açacağı ses kanalı", kategori="Yeni odaların açılacağı kategori")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ozelodaayarla(
        self,
        interaction: discord.Interaction,
        olusturucu_kanal: discord.VoiceChannel,
        kategori: discord.CategoryChannel | None = None,
    ):
        cfg = self.cfg(interaction.guild_id)
        cfg["creator_channel_id"] = olusturucu_kanal.id
        cfg["category_id"] = kategori.id if kategori else olusturucu_kanal.category_id
        await self.store.save()
        await interaction.response.send_message(f"✅ {olusturucu_kanal.mention} kanalına katılanlar artık özel oda alacak.", ephemeral=True)

    @app_commands.command(name="odaismi", description="İçinde bulunduğun özel odanın adını değiştirir.")
    async def odaismi(self, interaction: discord.Interaction, yeni_isim: str):
        cfg = self.cfg(interaction.guild_id)
        channel = interaction.user.voice.channel if interaction.user.voice else None
        if not channel or cfg.get("owned_channels", {}).get(str(channel.id)) != interaction.user.id:
            await interaction.response.send_message("❌ Kendi özel odanda olman gerekiyor.", ephemeral=True)
            return
        await channel.edit(name=yeni_isim[:100])
        await interaction.response.send_message("✅ Oda ismi güncellendi.", ephemeral=True)

    @app_commands.command(name="odalimit", description="İçinde bulunduğun özel odanın kullanıcı limitini ayarlar.")
    async def odalimit(self, interaction: discord.Interaction, limit: app_commands.Range[int, 0, 99]):
        cfg = self.cfg(interaction.guild_id)
        channel = interaction.user.voice.channel if interaction.user.voice else None
        if not channel or cfg.get("owned_channels", {}).get(str(channel.id)) != interaction.user.id:
            await interaction.response.send_message("❌ Kendi özel odanda olman gerekiyor.", ephemeral=True)
            return
        await channel.edit(user_limit=limit)
        await interaction.response.send_message(f"✅ Oda limiti {limit if limit else 'sınırsız'} olarak ayarlandı.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PrivateRooms(bot))
