"""
cogs/suggestions.py
--------------------
Öneri Sistemi + Anket Sistemi + Self-Rol Menüsü
Suggestion System + Poll System + Self-Assignable Role Menu
"""

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import make_embed


class SuggestionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👍", style=discord.ButtonStyle.success, custom_id="atasoft:suggest_up")
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._vote(interaction, "up")

    @discord.ui.button(label="👎", style=discord.ButtonStyle.danger, custom_id="atasoft:suggest_down")
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._vote(interaction, "down")

    async def _vote(self, interaction: discord.Interaction, direction: str):
        embed = interaction.message.embeds[0]
        up = int((embed.footer.text or "0|0").split("|")[0])
        down = int((embed.footer.text or "0|0").split("|")[1])
        # Not: basit gösterim amaçlı sayaç; kimin oy verdiğini tekilleştirmek için
        # gerçek bir üründe kullanıcı listesi tutulmalı.
        # Note: simplified counter for demo purposes; a real product should
        # track voter IDs to prevent double-voting.
        if direction == "up":
            up += 1
        else:
            down += 1
        embed.set_footer(text=f"{up}|{down}  •  👍 {up}  👎 {down}")
        await interaction.response.edit_message(embed=embed)


class PollView(discord.ui.View):
    def __init__(self, option_labels: list[str]):
        super().__init__(timeout=None)
        self.votes: dict[int, int] = {}  # user_id -> option_index
        self.counts = [0] * len(option_labels)
        for idx, label in enumerate(option_labels):
            self.add_item(self._make_button(idx, label))

    def _make_button(self, index: int, label: str) -> discord.ui.Button:
        button = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id=f"poll_opt_{index}")

        async def callback(interaction: discord.Interaction):
            previous = self.votes.get(interaction.user.id)
            if previous is not None:
                self.counts[previous] -= 1
            self.votes[interaction.user.id] = index
            self.counts[index] += 1
            await interaction.response.send_message(f"✅ Oyun kaydedildi: **{label}**", ephemeral=True)

        button.callback = callback
        return button


class RoleMenuSelect(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption], multi: bool):
        super().__init__(
            placeholder="Rol seç / Choose a role",
            min_values=0,
            max_values=len(options) if multi else 1,
            options=options,
            custom_id="atasoft:role_menu_select",
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        selected_ids = {int(v) for v in self.values}
        all_ids = {int(opt.value) for opt in self.options}

        to_add = [interaction.guild.get_role(rid) for rid in selected_ids if rid]
        to_remove = [interaction.guild.get_role(rid) for rid in (all_ids - selected_ids) if rid]

        to_add = [r for r in to_add if r]
        to_remove = [r for r in to_remove if r]

        if to_add:
            await member.add_roles(*to_add, reason="Self-rol menüsü / Self-role menu")
        if to_remove:
            await member.remove_roles(*to_remove, reason="Self-rol menüsü / Self-role menu")

        await interaction.response.send_message("✅ Rollerin güncellendi.", ephemeral=True)


class RoleMenuView(discord.ui.View):
    def __init__(self, options: list[discord.SelectOption], multi: bool):
        super().__init__(timeout=None)
        self.add_item(RoleMenuSelect(options, multi))


class Suggestions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = bot.store  # type: ignore[attr-defined]

    async def cog_load(self):
        self.bot.add_view(SuggestionView())

    def cfg(self, guild_id: int) -> dict:
        g = self.store.guild(guild_id)
        g.setdefault("suggestions", {"channel_id": None})
        return g["suggestions"]

    # ---------- Öneri / Suggestions ----------

    @app_commands.command(name="oneri-kanali", description="Önerilerin gönderileceği kanalı ayarlar.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def oneri_kanali(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        self.cfg(interaction.guild_id)["channel_id"] = kanal.id
        await self.store.save()
        await interaction.response.send_message(f"✅ Öneri kanalı: {kanal.mention}", ephemeral=True)

    @app_commands.command(name="oneri", description="Yeni bir öneri gönderir.")
    async def oneri(self, interaction: discord.Interaction, metin: str):
        cfg = self.cfg(interaction.guild_id)
        channel_id = cfg.get("channel_id")
        channel = interaction.guild.get_channel(channel_id) if channel_id else interaction.channel

        embed = make_embed(title="💡 Yeni Öneri / New Suggestion", description=metin)
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="0|0  •  👍 0  👎 0")
        await channel.send(embed=embed, view=SuggestionView())
        await interaction.response.send_message("✅ Önerin gönderildi, teşekkürler!", ephemeral=True)

    # ---------- Anket / Poll ----------

    @app_commands.command(name="anket-kur", description="Butonlu bir anket oluşturur (seçenekleri virgülle ayır).")
    @app_commands.describe(soru="Anket sorusu", secenekler="Virgülle ayrılmış seçenekler (en fazla 5)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def anket_kur(self, interaction: discord.Interaction, soru: str, secenekler: str):
        options = [s.strip() for s in secenekler.split(",") if s.strip()][:5]
        if len(options) < 2:
            await interaction.response.send_message("❌ En az 2 seçenek gerekli.", ephemeral=True)
            return
        embed = make_embed(title=f"📊 {soru}", description="Oy vermek için bir butona tıkla.")
        await interaction.response.send_message(embed=embed, view=PollView(options))

    # ---------- Self-rol menüsü / Self-role menu ----------

    @app_commands.command(name="rolmenu", description="Kullanıcıların kendi rollerini seçebileceği bir menü oluşturur.")
    @app_commands.describe(
        baslik="Menü başlığı",
        roller="Rol etiketleri virgülle ayrılmış (ör: @Oyuncu, @Sanatçı, @Müzisyen)",
        coklu_secim="Kullanıcı birden fazla rol seçebilsin mi?",
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def rolmenu(self, interaction: discord.Interaction, baslik: str, roller: str, coklu_secim: bool = True):
        role_mentions = [r.strip() for r in roller.split(",") if r.strip()]
        parsed_roles: list[discord.Role] = []
        for mention in role_mentions:
            role_id = mention.strip("<@&>")
            role = interaction.guild.get_role(int(role_id)) if role_id.isdigit() else discord.utils.get(interaction.guild.roles, name=mention)
            if role:
                parsed_roles.append(role)
        if not parsed_roles:
            await interaction.response.send_message("❌ Geçerli rol bulunamadı.", ephemeral=True)
            return

        options = [discord.SelectOption(label=r.name, value=str(r.id)) for r in parsed_roles[:25]]
        embed = make_embed(title=baslik, description="Aşağıdaki menüden rollerini seç.")
        await interaction.response.send_message(embed=embed, view=RoleMenuView(options, coklu_secim))


async def setup(bot: commands.Bot):
    await bot.add_cog(Suggestions(bot))
