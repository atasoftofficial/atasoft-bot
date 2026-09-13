"""
cogs/onboarding.py
-------------------
Kayıt Sistemi + Kurallar Onayı
Registration System + Rules Acceptance

Akış / Flow:
1) Yönetici /kurallar-kur ile kurallar mesajını + "Kabul Ediyorum" butonunu kurar.
   Admin sets up the rules message + "I Accept" button with /kurallar-kur.
2) Kullanıcı butona basınca doğrulama rolü verilir ve kayıt formu (modal) açılır.
   When a user clicks the button, they get a verified role and a registration modal opens.
3) Doldurulan bilgiler kaydedilir, /profil ile görüntülenebilir.
   Submitted info is stored and viewable with /profil.
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import make_embed


class AcceptRulesView(discord.ui.View):
    """Kalıcı görünüm: bot yeniden başlasa bile buton çalışmaya devam eder.
    Persistent view: keeps working across bot restarts."""

    def __init__(self, cog: "Onboarding"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Kuralları Kabul Ediyorum / I Accept",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="atasoft:accept_rules",
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_accept(interaction)


class RegistrationModal(discord.ui.Modal, title="Kayıt Formu / Registration"):
    isim = discord.ui.TextInput(label="İsim / Name", max_length=32)
    yas = discord.ui.TextInput(label="Yaş / Age", max_length=3)
    hakkinda = discord.ui.TextInput(
        label="Kısaca kendinden bahset / About you",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=200,
    )

    def __init__(self, cog: "Onboarding"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.handle_registration_submit(interaction, self.isim.value, self.yas.value, self.hakkinda.value)


class Onboarding(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = bot.store  # type: ignore[attr-defined]

    async def cog_load(self):
        self.bot.add_view(AcceptRulesView(self))

    # ---------- Yardımcılar / Helpers ----------

    def cfg(self, guild_id: int) -> dict:
        g = self.store.guild(guild_id)
        g.setdefault("onboarding", {"rules_channel_id": None, "verified_role_id": None, "registrations": {}})
        return g["onboarding"]

    async def handle_accept(self, interaction: discord.Interaction):
        cfg = self.cfg(interaction.guild_id)
        role_id = cfg.get("verified_role_id")
        if role_id:
            role = interaction.guild.get_role(int(role_id))
            if role and role not in interaction.user.roles:
                try:
                    await interaction.user.add_roles(role, reason="Kuralları kabul etti / Accepted rules")
                except discord.Forbidden:
                    pass
        already = str(interaction.user.id) in cfg.get("registrations", {})
        if already:
            await interaction.response.send_message(
                "✅ Zaten kayıtlısın. / You're already registered.", ephemeral=True
            )
            return
        await interaction.response.send_modal(RegistrationModal(self))

    async def handle_registration_submit(self, interaction: discord.Interaction, isim: str, yas: str, hakkinda: str):
        cfg = self.cfg(interaction.guild_id)
        cfg.setdefault("registrations", {})[str(interaction.user.id)] = {
            "isim": isim,
            "yas": yas,
            "hakkinda": hakkinda,
        }
        await self.store.save()

        try:
            await interaction.user.edit(nick=isim[:32])
        except (discord.Forbidden, discord.HTTPException):
            pass

        embed = make_embed(
            title="🎉 Kayıt Tamamlandı / Registration Complete",
            description=f"Hoş geldin **{isim}**! Sunucuyu keşfetmeye başlayabilirsin.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---------- Komutlar / Commands ----------

    @app_commands.command(name="kurallar-kur", description="Kurallar + kabul et butonunu bu kanalda oluşturur.")
    @app_commands.describe(rol="Kabul edince verilecek doğrulama rolü", metin="Kurallar metni")
    @app_commands.checks.has_permissions(administrator=True)
    async def kurallar_kur(self, interaction: discord.Interaction, rol: discord.Role, metin: str):
        cfg = self.cfg(interaction.guild_id)
        cfg["verified_role_id"] = rol.id
        cfg["rules_channel_id"] = interaction.channel_id
        await self.store.save()

        embed = make_embed(title="📜 Sunucu Kuralları / Server Rules", description=metin)
        await interaction.channel.send(embed=embed, view=AcceptRulesView(self))
        await interaction.response.send_message("✅ Kurallar paneli oluşturuldu.", ephemeral=True)

    @app_commands.command(name="profil", description="Kayıt bilgilerini gösterir.")
    async def profil(self, interaction: discord.Interaction, kullanici: discord.Member | None = None):
        target = kullanici or interaction.user
        cfg = self.cfg(interaction.guild_id)
        data = cfg.get("registrations", {}).get(str(target.id))
        if not data:
            await interaction.response.send_message("Bu kullanıcı için kayıt bulunamadı.", ephemeral=True)
            return
        embed = make_embed(title=f"👤 {target.display_name}")
        embed.add_field(name="İsim / Name", value=data.get("isim", "-"), inline=True)
        embed.add_field(name="Yaş / Age", value=data.get("yas", "-"), inline=True)
        if data.get("hakkinda"):
            embed.add_field(name="Hakkında / About", value=data["hakkinda"], inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))
