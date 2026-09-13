"""
utils/storage.py
-----------------
Basit, bağımlılıksız JSON tabanlı veri katmanı.
Her guild (sunucu) kendi anahtarı altında saklanır; dosyaya asenkron kilit ile yazılır.

A tiny dependency-free JSON data layer.
Each guild's data lives under its own key; writes are protected with an asyncio lock.
"""

import json
import os
import asyncio
from typing import Any


class JsonStore:
    """Tek bir JSON dosyasını (ör. data/guilds.json) yöneten basit veri deposu.

    A minimal store that persists a single JSON file (e.g. data/guilds.json).
    """

    def __init__(self, path: str):
        self.path = path
        self.data: dict[str, Any] = {}
        self._lock = asyncio.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, OSError):
                # Bozuk dosya varsa sıfırdan başla ama eski dosyayı .bak olarak sakla
                # If the file is corrupted, start fresh but back up the old one
                try:
                    os.replace(self.path, self.path + ".bak")
                except OSError:
                    pass
                self.data = {}
        else:
            self.data = {}

    async def save(self) -> None:
        async with self._lock:
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)

    def guild(self, guild_id: int) -> dict:
        """İlgili guild için config dict'ini döner, yoksa oluşturur.

        Returns (and lazily creates) the config dict for a given guild.
        """
        key = str(guild_id)
        if key not in self.data:
            self.data[key] = {}
        return self.data[key]
