[![AtasoftBot Logo](https://atasoft.xyz/atasoft.png)](https://bot.atasoft.xyz)

# AtasoftBot — Açık Kaynak Özellik Vitrini / Open-Source Feature Showcase

> 🇹🇷 Bu repo, [**ATASOFTBOT**](https://bot.atasoft.xyz) adlı özel/ticari Discord botunun kendisi değildir. Botun genel amaçlı, tekrar kullanılabilir özelliklerinin temiz ve bağımsız bir şekilde yeniden yazılmış hâlidir — öğrenmek, örnek almak veya kendi botunuzda kullanmak isteyenler için hazırlanmıştır.
>
> 🇬🇧 This repository is **not** the [ATASOFTBOT](https://bot.atasoft.xyz) commercial product itself. It's a clean, independent reimplementation of its general-purpose, reusable features — meant for learning, reference, or building your own bot on top of.

---

## 🇹🇷 Türkçe

### Bu repo nedir, ne değildir?

* **Nedir:** Genel amaçlı, herhangi bir Discord sunucusunda işe yarayabilecek topluluk yönetim özelliklerinin sade, okunabilir `discord.py` kodu.
* **Ne değildir:** Ticari ATASOFTBOT ürününün tam kaynak kodu değildir. Anti-nuke, sunucu yedekleme, web paneli entegrasyonu, çoklu dil motoru gibi ürüne özel / güvenlik açısından hassas sistemler **kasıtlı olarak dahil edilmemiştir**.

### Özellikler

| Modül | Açıklama |
| :--- | :--- |
| 📋 Kayıt Sistemi + Kurallar | Kurallar mesajına "Kabul Ediyorum" butonu, ardından açılan formla üye kaydı |
| 📈 Seviye Sistemi | Mesaj ve sesli sohbet süresine göre XP, seviye atlama duyurusu, seviye rolleri |
| 🎫 Ticket Sistemi | Panel butonuyla özel destek kanalı açma/kapatma |
| 💡 Öneri + 📊 Anket + 🎭 Self-Rol Menüsü | Butonlu öneri oylaması, çoklu seçenekli anket, kullanıcıların kendi rolünü seçmesi |
| 👋 Giriş/Çıkış + Otorol + Saatlik Selam + Otomatik Mesaj | Katılım/ayrılış mesajları, otomatik rol, saat başı selam, zamanlanmış duyuru |
| 🔨 Temel Moderasyon | Ban, süreli ban, kick, sustur (timeout), uyarı sistemi, rol ver/al, mesaj sil |
| 🔊 Özel Oda Sistemi | Bir kanala katılınca otomatik özel ses odası açılması, boşalınca silinmesi |
| 📨 Davet Takip Sistemi | Yeni üyenin hangi davetle ve kim tarafından davet edildiğini bulma |
| ⛏️ Minecraft Sunucu Durumu | Harici kütüphane olmadan sunucu durumu/oyuncu sayısı sorgulama ve kanalda gösterme |

### Kurulum

```bash
# Projeyi klonlayın
git clone <bu-repo-linki>
cd atasoft-bot

# Sanal ortam oluşturun ve aktif edin
python3 -m venv .venv
source .venv/bin/activate      # Windows için: .venv\Scripts\activate

# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt

# Çevre değişkenlerini ayarlayın
cp .env.example .env
```

1. `.env` dosyasını açıp `ATASOFTBOT_TOKEN` alanına Discord Developer Portal'dan aldığınız bot token'ını yapıştırın.
   > ⚠️ **Token'ı asla GitHub'da veya herhangi bir açık platformda paylaşmayın.** Token sızarsa Developer Portal'dan *Reset Token* yaparak hemen geçersiz kılın.
2. Discord Developer Portal'da botunuz için şu **Privileged Gateway Intents** ayarlarını açın:
   * `Server Members Intent`
   * `Message Content Intent`
3. Botu çalıştırın:
```bash
python3 main.py
```

### Ortam Değişkenleri

| Değişken | Açıklama | Varsayılan |
| :--- | :--- | :--- |
| `ATASOFTBOT_TOKEN` | Discord bot token'ı (zorunlu) | — |
| `ATASOFTBOT_PREFIX` | Metin komut ön eki | `!` |
| `ATASOFTBOT_DATA_PATH` | JSON veri dosyasının yolu | `data/guilds.json` |

### Klasör Yapısı

```text
atasoft-bot/
├── main.py                  # Giriş noktası, cog yükleme
├── cogs/                    # Her özellik kendi dosyasında
│   ├── onboarding.py        # Kayıt + kurallar
│   ├── leveling.py          # Seviye sistemi
│   ├── tickets.py           # Ticket sistemi
│   ├── suggestions.py       # Öneri + anket + self-rol
│   ├── welcome.py           # Giriş/çıkış + otorol + selam + otomesaj
│   ├── moderation.py        # Ban/kick/mute/uyarı/rol/mesaj sil
│   ├── private_rooms.py     # Özel ses odaları
│   ├── invites.py           # Davet takibi
│   └── minecraft_status.py  # Minecraft sunucu durumu
├── utils/
│   ├── storage.py           # Basit JSON veri katmanı
│   └── embeds.py            # Ortak embed stili
└── data/                    # Çalışma zamanında oluşan veri (git'e dahil değil)
```

### Neden bazı özellikler yok?

Anti-nuke, sunucu yedekleme, join-gate, spam/scam koruması, sızıntı tespiti gibi güvenlik sistemleri kasıtlı olarak dışarıda bırakıldı çünkü:
1. Bunlar botun asıl ticari değerini oluşturuyor.
2. Çoğu özel altyapıya (web API, harici veritabanı) bağımlı çalışıyor.
3. Yanlış/eksik kopyalanmış güvenlik kodu, gerçek bir güvenlik açığı oluşturup sahte bir güven duygusu yaratabilir. 

Kendi güvenlik ihtiyaçlarınız için test edilmiş, bakımı sürekli yapılan resmi çözümler kullanmanızı öneririz.

### Katkıda Bulunma

Pull request'ler ve issue'lar memnuniyetle karşılanır. Yeni bir özelliği kendi `cogs/` dosyanız olarak eklemeniz yeterlidir; ardından eklediğiniz modülü `main.py` içindeki `EXTENSIONS` listesine dahil etmeyi unutmayın.

### Lisans

Bu repo eğitim/referans amaçlıdır; kendi projenizde dilediğiniz gibi kullanabilir, değiştirebilir ve dağıtabilirsiniz.

---

## 🇬🇧 English

### What this is, and isn't

* **What it is:** Clean, readable `discord.py` code for general-purpose community-management features that could be useful in any Discord server.
* **What it isn't:** The full source of the commercial ATASOFTBOT product. Product-specific and security-sensitive systems — anti-nuke, server backups, web-panel integration, the multi-language engine — are **intentionally excluded**.

### Features

| Module | Description |
| :--- | :--- |
| 📋 Registration + Rules | "I Accept" button on the rules message, followed by a registration modal |
| 📈 Leveling | XP from messages and voice time, level-up announcements, level-based roles |
| 🎫 Ticket System | Open/close a private support channel via a panel button |
| 💡 Suggestions + 📊 Polls + 🎭 Self-Role Menu | Button-voted suggestions, multi-option polls, self-assignable roles |
| 👋 Join/Leave + Auto-role + Hourly Greeting + Auto-message | Join/leave messages, automatic role assignment, hourly greeting, scheduled announcements |
| 🔨 Basic Moderation | Ban, temp-ban, kick, timeout, warnings, role add/remove, message purge |
| 🔊 Private Voice Rooms | Join-to-create voice channels that auto-delete when empty |
| 📨 Invite Tracking | Figure out which invite (and inviter) brought in a new member |
| ⛏️ Minecraft Server Status | Query server status/player count with no external library, post it to a channel |

### Setup

```bash
# Clone the repository
git clone <this-repo-url>
cd atasoft-bot

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # For Windows: .venv\Scripts\activate

# Install the required dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

1. Open `.env` and paste your bot token from the Discord Developer Portal into `ATASOFTBOT_TOKEN`.
   > ⚠️ **Never commit your token or share it anywhere.** If it ever leaks, reset it immediately from the Developer Portal (*Reset Token*).
2. In the Developer Portal, enable these **Privileged Gateway Intents** for your bot:
   * `Server Members Intent`
   * `Message Content Intent`
3. Run the bot:
```bash
python3 main.py
```

### Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ATASOFTBOT_TOKEN` | Discord bot token (required) | — |
| `ATASOFTBOT_PREFIX` | Text command prefix | `!` |
| `ATASOFTBOT_DATA_PATH` | Path to the JSON data file | `data/guilds.json` |

### Project Structure

```text
atasoft-bot/
├── main.py                  # Entry point, loads cogs
├── cogs/                    # One file per feature
│   ├── onboarding.py        # Registration + rules
│   ├── leveling.py          # Leveling system
│   ├── tickets.py           # Ticket system
│   ├── suggestions.py       # Suggestions + polls + self-roles
│   ├── welcome.py           # Join/leave + auto-role + greeting + auto-message
│   ├── moderation.py        # Ban/kick/mute/warn/role/purge
│   ├── private_rooms.py     # Private voice rooms
│   ├── invites.py           # Invite tracking
│   └── minecraft_status.py  # Minecraft server status
├── utils/
│   ├── storage.py           # Minimal JSON data layer
│   └── embeds.py            # Shared embed styling
└── data/                    # Runtime data (not committed to git)
```

### Why are some features missing?

Security-oriented systems (anti-nuke, server backups, join-gate, spam/scam protection, secret-leak detection) were intentionally left out because:
1. They represent the bot's core commercial value.
2. Most depend on private infrastructure (such as a web API or a specific database).
3. Partially-copied security code can look like real protection while providing none, creating a false sense of safety.

For your own security needs, we highly recommend using a maintained, properly tested solution.

### Contributing

PRs and issues are welcome. To add a new feature, drop it in as its own file under `cogs/` and add it to the `EXTENSIONS` list in `main.py`.

### License

This repo is for learning/reference purposes — feel free to use, modify, and redistribute it in your own projects.
