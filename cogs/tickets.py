"""
cogs/tickets.py
----------------
Destek Talebi (Ticket) Sistemi
Support Ticket System

Panel mesajındaki butona basan kullanıcı için özel bir metin kanalı açılır;
sadece kullanıcı, yetkili rolü ve bot bu kanalı görebilir. Kapat butonuyla kanal silinir.

Clicking the panel button opens a private text channel visible only to the user,
the staff role, and the bot. The close button deletes the channel.
"""

import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import make_embed


class TicketPanelView(discord.ui.View):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Destek Talebi Aç / Open Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="atasoft:open_ticket",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.create_ticket(interaction)


class TicketCloseView(discord.ui.View):
    def __init__(self, cog: "Tickets"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Kapat / Close",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="atasoft:close_ticket",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.close_ticket(interaction)


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = bot.store  # type: ignore[attr-defined]

    async def cog_load(self):
        self.bot.add_view(TicketPanelView(self))
        self.bot.add_view(TicketCloseView(self))

    def cfg(self, guild_id: int) -> dict:
        g = self.store.guild(guild_id)
        g.setdefault(
            "tickets",
            {"category_id": None, "staff_role_id": None, "counter": 0, "open_tickets": {}},
        )
        return g["tickets"]

    async def create_ticket(self, interaction: discord.Interaction):
        cfg = self.cfg(interaction.guild_id)
        existing = cfg.get("open_tickets", {}).get(str(interaction.user.id))
        if existing and interaction.guild.get_channel(existing):
            await interaction.response.send_message(
                f"❗ Zaten açık bir talebin var: <#{existing}>", ephemeral=True
            )
            return

        guild = interaction.guild
        category = guild.get_channel(cfg["category_id"]) if cfg.get("category_id") else None
        staff_role = guild.get_role(cfg["staff_role_id"]) if cfg.get("staff_role_id") else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        cfg["counter"] = cfg.get("counter", 0) + 1
        channel = await guild.create_text_channel(
            name=f"ticket-{cfg['counter']:04d}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket açıldı / Ticket opened by {interaction.user}",
        )
        cfg.setdefault("open_tickets", {})[str(interaction.user.id)] = channel.id
        await self.store.save()

        embed = make_embed(
            title=f"🎫 Destek Talebi #{cfg['counter']:04d}",
            description=(
                f"Merhaba {interaction.user.mention}, talebini kısaca özetle. Bir yetkili en kısa sürede yardımcı olacak.\n\n"
                f"Hi {interaction.user.mention}, briefly describe your issue. Staff will help you shortly."
            ),
        )
        await channel.send(
            content=staff_role.mention if staff_role else None,
            embed=embed,
            view=TicketCloseView(self),
        )
        await interaction.response.send_message(f"✅ Talebin oluşturuldu: {channel.mention}", ephemeral=True)

    async def close_ticket(self, interaction: discord.Interaction):
        cfg = self.cfg(interaction.guild_id)
        for user_id, channel_id in list(cfg.get("open_tickets", {}).items()):
            if channel_id == interaction.channel_id:
                cfg["open_tickets"].pop(user_id, None)
        await self.store.save()

        await interaction.response.send_message("🔒 Bu talep 5 saniye içinde kapatılacak...")
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket kapatıldı / Closed by {interaction.user}")

    # ---------- Komutlar / Commands ----------

    @app_commands.command(name="ticket-kur", description="Bu kanala destek talebi panelini kurar.")
    @app_commands.describe(kategori="Ticket kanallarının açılacağı kategori", yetkili_rol="Talepleri görecek yetkili rolü")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_kur(
        self,
        interaction: discord.Interaction,
        kategori: discord.CategoryChannel,
        yetkili_rol: discord.Role,
    ):
        cfg = self.cfg(interaction.guild_id)
        cfg["category_id"] = kategori.id
        cfg["staff_role_id"] = yetkili_rol.id
        await self.store.save()

        embed = make_embed(
            title="🎫 Destek Merkezi / Support Center",
            description="Yardıma mı ihtiyacın var? Aşağıdaki butona basarak özel bir destek kanalı aç.\n\nNeed help? Click below to open a private support channel.",
        )
        await interaction.channel.send(embed=embed, view=TicketPanelView(self))
        await interaction.response.send_message("✅ Ticket paneli kuruldu.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
