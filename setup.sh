#!/bin/bash
# ════════════════════════════════════════════════════════
#  Secret Santa Bot — Tezkor o'rnatish skripti
#  Ishlatish: bash setup.sh
# ════════════════════════════════════════════════════════

set -e  # Xato bo'lsa to'xtat

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🎁 Secret Santa Bot — O'rnatish"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Python versiyasini tekshirish
echo ""
echo "🔍 Python versiyasi tekshirilmoqda..."
python3 --version || { echo "❌ Python3 topilmadi!"; exit 1; }

# 2. Virtual environment yaratish
echo ""
echo "📦 Virtual environment yaratilmoqda..."
python3 -m venv venv
echo "✅ venv tayyor"

# 3. Kutubxonalar o'rnatish
echo ""
echo "📥 Kutubxonalar o'rnatilmoqda..."
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q
echo "✅ Kutubxonalar o'rnatildi"

# 4. .env fayl tekshirish
echo ""
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  .env fayli yaratildi."
    echo "    ➡️  nano .env  — tokeningizni kiriting!"
else
    echo "✅ .env fayli mavjud"
fi

# 5. logs papkasini yaratish
mkdir -p logs
echo "✅ logs/ papkasi tayyor"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ O'rnatish tugadi!"
echo ""
echo "  Keyingi qadamlar:"
echo "  1️⃣   nano .env    ← BOT_TOKEN ni kiriting"
echo "  2️⃣   Ishga tushirish uchun:"
echo "       ./venv/bin/python bot.py"
echo ""
echo "  🖥️  Server (systemd) uchun:"
echo "       nano secret-santa.service  ← user va path ni o'zgartiring"
echo "       sudo cp secret-santa.service /etc/systemd/system/"
echo "       sudo systemctl daemon-reload"
echo "       sudo systemctl enable --now secret-santa"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"