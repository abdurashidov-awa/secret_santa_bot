# 🎁 Secret Santa Telegram Bot

Guruh uchun **Secret Santa** o'yinini boshqaruvchi Telegram bot.

---

## 📁 Fayl tuzilmasi

```
secret_santa_bot/
├── bot.py                 ← Asosiy bot kodi
├── .env                   ← Token (git ga qo'shilmaydi!)
├── .env.example           ← Token shablon
├── requirements.txt       ← Kutubxonalar
├── setup.sh               ← Avtomatik o'rnatish
├── secret-santa.service   ← systemd servisi (server uchun)
├── .gitignore
└── logs/                  ← Bot loglari (avtomatik yaratiladi)
    └── bot.log
```

---

## 🚀 O'rnatish

### 1. Reponi klonlash yoki fayllarni nusxalash

```bash
git clone <repo-url> secret_santa_bot
cd secret_santa_bot
```

### 2. Tezkor o'rnatish

```bash
bash setup.sh
```

### 3. Tokenni kiriting

```bash
nano .env
# BOT_TOKEN=7xxxxxxx:AAxxxxxxxxx
```

### 4. Ishga tushirish (local test)

```bash
./venv/bin/python bot.py
```

---

## 🖥️ Server (Linux VPS) — systemd bilan

### 1. `secret-santa.service` faylini tahrirlang

```bash
nano secret-santa.service
```
`User`, `WorkingDirectory`, `ExecStart` qatorlarini serveringizga mos o'zgartiring.

### 2. Serverni o'rnatib ishga tushiring

```bash
sudo cp secret-santa.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable secret-santa
sudo systemctl start secret-santa
```

### 3. Boshqaruv buyruqlari

```bash
sudo systemctl status secret-santa     # holat
sudo systemctl restart secret-santa    # qayta ishga tushirish
sudo systemctl stop secret-santa       # to'xtatish
journalctl -u secret-santa -f          # real-time loglar
```

---

## 🖥️ Server — `screen` bilan (soddaroq yo'l)

```bash
# screen o'rnatish (agar yo'q bo'lsa)
sudo apt install screen -y

# Yangi screen session
screen -S santabot

# Botni ishga tushirish
./venv/bin/python bot.py

# Screendan chiqish (bot ishlashda qoladi)
Ctrl+A, keyin D

# Qaytish
screen -r santabot
```

---

## 📋 Bot buyruqlari

| Buyruq | Tavsif |
|---|---|
| `/start` | Xush kelibsiz xabari |
| `/join` | O'yinga qo'shilish (ism + preferences) |
| `/list` | Barcha ishtirokchilarni ko'rish |
| `/start_game` | O'yinni boshlash va taqsimot |
| `/status` | O'yin holati |
| `/cancel` | Joriy jarayonni bekor qilish |

### 👑 Admin buyruqlari

| Buyruq | Tavsif |
|---|---|
| `/set_min_players` | Minimal ishtirokchilar sonini o'zgartirish |
| `/reset` | O'yinni xabarsiz tozalash |
| `/restart` | O'yinni tozalash + barcha ishtirokchilarga xabar yuborish |

> **Birinchi `/start` bosgn foydalanuvchi avtomatik admin bo'ladi.**

---

## 🔒 Xavfsizlik

- Token hech qachon `bot.py` ichiga yozilmasin — faqat `.env` orqali
- `.env` fayli `.gitignore` da — git ga yuklanmaydi
- Server da faylga faqat bot userida kirish huquqi bering:
  ```bash
  chmod 600 .env
  ```

---

## 🛠️ Talablar

- Python 3.10+
- `python-telegram-bot==21.6`
- `python-dotenv==1.0.1`