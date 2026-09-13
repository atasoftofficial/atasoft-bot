"""
cogs/minecraft_status.py
-------------------------
Minecraft Sunucu Durum Kanalı
Minecraft Server Status Channel

Harici kütüphane kullanmadan, Minecraft'ın "Server List Ping" protokolüyle
sunucunun çevrimiçi olup olmadığını ve oyuncu sayısını sorgular; belirlenen
kanaldaki bir mesajı periyodik olarak günceller.

Queries a Minecraft server's online status and player count using the
"Server List Ping" protocol with no external dependencies, and periodically
updates a message in the configured channel.
"""

import asyncio
import struct
import json as _json

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.embeds import make_embed


def _pack_varint(value: int) -> bytes:
    out = b""
    value &= 0xFFFFFFFF
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out += struct.pack("B", byte | 0x80)
        else:
            out += struct.pack("B", byte)
            break
    return out


async def _read_varint(reader: asyncio.StreamReader) -> int:
    num_read = 0
    result = 0
    while True:
        data = await reader.readexactly(1)
        val = data[0]
        result |= (val & 0x7F) << (7 * num_read)
        num_read += 1
        if num_read > 5:
            raise ValueError("VarInt too big")
        if (val & 0x80) == 0:
            break
    return result


async def mc_status(host: str, port: int = 25565, timeout: float = 4.0):
    """(online, players_online, players_max, version) döner / returns."""
    if not host:
        return False, None, None, None
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, int(port)), timeout=timeout)

        protocol_version = 754
        host_bytes = host.encode("utf-8")
        handshake = (
            _pack_varint(0x00)
            + _pack_varint(protocol_version)
            + _pack_varint(len(host_bytes))
            + host_bytes
            + struct.pack(">H", int(port))
            + _pack_varint(0x01)
        )
        writer.write(_pack_varint(len(handshake)) + handshake)
        request = _pack_varint(0x00)
        writer.write(_pack_varint(len(request)) + request)
        await writer.drain()

        await _read_varint(reader)  # packet length
        packet_id = await _read_varint(reader)
        if packet_id != 0x00:
            raise ValueError("Unexpected packet id")

        str_len = await _read_varint(reader)
        payload = await reader.readexactly(str_len)
        data = _json.loads(payload.decode("utf-8", errors="ignore"))

        players_online = int(data.get("players", {}).get("online", 0))
        players_max = int(data.get("players", {}).get("max", 0))
        version = data.get("version", {}).get("name")

        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

        return True, players_online, players_max, version
    except Exception:
        return False, None, None, None


class MinecraftStatus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = bot.store  # type: ignore[attr-defined]
        self.status_loop.start()

    def cog_unload(self):
        self.status_loop.cancel()

    def cfg(self, guild_id: int) -> dict:
        g = self.store.guild(guild_id)
        g.setdefault("minecraft_status", {"channel_id": None, "message_id": None, "host": None, "port": 25565})
        return g["minecraft_status"]

    @tasks.loop(seconds=60)
    async def status_loop(self):
        for guild in self.bot.guilds:
            cfg = self.cfg(guild.id)
            if not cfg.get("host") or not cfg.get("channel_id"):
                continue
            await self._update_status_message(guild, cfg)

    @status_loop.before_loop
    async def _before_status_loop(self):
        await self.bot.wait_until_ready()

    async def _update_status_message(self, guild: discord.Guild, cfg: dict):
        channel = guild.get_channel(cfg["channel_id"])
        if not channel:
            return

        online, players, max_players, version = await mc_status(cfg["host"], cfg.get("port", 25565))
        embed = make_embed(
            title="⛏️ Minecraft Sunucu Durumu / Server Status",
            color=discord.Color.green() if online else discord.Color.red(),
        )
        embed.add_field(name="Adres / Address", value=f"`{cfg['host']}:{cfg.get('port', 25565)}`", inline=False)
        embed.add_field(name="Durum / Status", value="🟢 Çevrimiçi / Online" if online else "🔴 Çevrimdışı / Offline", inline=True)
        if online:
            embed.add_field(name="Oyuncular / Players", value=f"{players}/{max_players}", inline=True)
            if version:
                embed.add_field(name="Sürüm / Version", value=str(version), inline=True)

        message_id = cfg.get("message_id")
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
                return
            except discord.NotFound:
                pass

        message = await channel.send(embed=embed)
        cfg["message_id"] = message.id
        await self.store.save()

    @app_commands.command(name="minecraftkanali", description="Minecraft sunucu durum kanalını ayarlar.")
    @app_commands.describe(kanal="Durum mesajının atılacağı kanal", adres="Sunucu IP / domain", port="Sunucu portu (varsayılan 25565)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def minecraftkanali(
        self, interaction: discord.Interaction, kanal: discord.TextChannel, adres: str, port: int = 25565
    ):
        cfg = self.cfg(interaction.guild_id)
        cfg["channel_id"] = kanal.id
        cfg["host"] = adres
        cfg["port"] = port
        cfg["message_id"] = None
        await self.store.save()
        await interaction.response.send_message(f"✅ Minecraft durum kanalı {kanal.mention} olarak ayarlandı.", ephemeral=True)
        await self._update_status_message(interaction.guild, cfg)


async def setup(bot: commands.Bot):
    await bot.add_cog(MinecraftStatus(bot))
