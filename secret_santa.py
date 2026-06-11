"""
Secret Santa Telegram Bot
Ishlab chiqaruvchi: Takomillashtirilgan versiya
Deployment: systemd yoki screen orqali server
"""

import logging
import logging.handlers
import os
import random
import json
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────
# Muhit o'zgaruvchilarini yuklash
# ─────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN .env faylida topilmadi!")

# ─────────────────────────────────────────
# Logging sozlamalari (fayl + konsol)
# ─────────────────────────────────────────
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("SecretSantaBot")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

# Konsol handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Fayl handler (har kuni yangi fayl, 7 kun saqlanadi)
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, "bot.log"),
    when="midnight",
    backupCount=7,
    encoding="utf-8",
)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# ─────────────────────────────────────────
# Conversatsiya bosqichlari
# ─────────────────────────────────────────
NAME, PREFERENCES, SET_MIN_PLAYERS = range(3)

# ─────────────────────────────────────────
# Ma'lumot modellari
# ─────────────────────────────────────────
@dataclass
class Participant:
    user_id: int
    username: str
    full_name: str
    preferences: str = "Belgilanmagan"
    secret_santa_for: Optional["Participant"] = field(default=None, repr=False)


@dataclass
class GameState:
    """Barcha o'yin holati shu classda — global o'zgaruvchi yo'q"""
    participants: list = field(default_factory=list)
    admin_ids: list = field(default_factory=list)
    game_started: bool = False
    min_players: int = 4

    def reset(self):
        self.participants = []
        self.game_started = False

    def find_participant(self, user_id: int) -> Optional[Participant]:
        return next((p for p in self.participants if p.user_id == user_id), None)

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids

    def remaining_slots(self) -> int:
        return max(0, self.min_players - len(self.participants))

    def can_start(self) -> bool:
        return len(self.participants) >= self.min_players and not self.game_started


# Yagona global instance
state = GameState()

# ─────────────────────────────────────────
# Yordamchi funksiyalar
# ─────────────────────────────────────────
def build_status_text() -> str:
    remaining = state.remaining_slots()
    if remaining > 0:
        return f"⏳ O'yinni boshlash uchun yana *{remaining}* kishi kerak!"
    return "✅ O'yinni boshlash mumkin\\! /start\\_game"


def build_admin_help(user_id: int) -> str:
    if not state.is_admin(user_id):
        return ""
    return (
        "\n\n👑 *Admin buyruqlari:*\n"
        f"/set\\_min\\_players — Minimal ishtirokchilar \\(hozir: {state.min_players}\\)\n"
        "/reset — Tez tozalash \\(xabarsiz\\)\n"
        "/restart — To'liq qaytadan boshlash \\(xabar bilan\\)"
    )


# ─────────────────────────────────────────
# /start
# ─────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not state.admin_ids:
        state.admin_ids.append(user.id)
        logger.info(f"Yangi admin: {user.id} ({user.full_name})")
        admin_msg = "\n\n🔑 Siz botning admini sifatida belgilandingiz!"
    else:
        admin_msg = ""

    text = (
        f"Salom, *{user.first_name}*\\! 🎁🎄\n\n"
        "Secret Santa o'yiniga xush kelibsiz\\!\n\n"
        "📋 *Buyruqlar:*\n"
        "/join — O'yinga qo'shilish\n"
        "/list — Ishtirokchilar ro'yxati\n"
        f"/start\\_game — O'yinni boshlash \\({state.min_players}\\+ kishi\\)\n"
        "/cancel — Bekor qilish"
        + build_admin_help(user.id)
        + admin_msg
    )
    await update.message.reply_markdown_v2(text)


# ─────────────────────────────────────────
# /set_min_players
# ─────────────────────────────────────────
async def cmd_set_min_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not state.is_admin(user.id):
        await update.message.reply_text("❌ Bu buyruq faqat admin uchun!")
        return ConversationHandler.END

    if state.game_started:
        await update.message.reply_text(
            "❌ O'yin ketayotganida sozlamalarni o'zgartirib bo'lmaydi!\n"
            "Avval /reset bilan o'yinni tugatib, keyin o'zgartiring."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"🔢 Minimal ishtirokchilar sonini kiriting:\n\n"
        f"📌 Hozirgi: {state.min_players} kishi\n"
        f"💡 Tavsiya: 4–10 oralig'ida\n\n"
        "Bekor qilish: /cancel"
    )
    return SET_MIN_PLAYERS


async def cmd_set_min_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_min = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Faqat raqam kiriting! Masalan: 5")
        return SET_MIN_PLAYERS

    if not (3 <= new_min <= 100):
        await update.message.reply_text(
            "❌ Son 3 dan 100 gacha bo'lishi kerak!\nQaytadan kiriting:"
        )
        return SET_MIN_PLAYERS

    state.min_players = new_min
    logger.info(f"min_players o'zgartirildi: {new_min}")
    await update.message.reply_text(
        f"✅ Minimal ishtirokchilar soni: *{new_min}* kishiga o'zgartirildi!",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# ─────────────────────────────────────────
# /join — Conversatsiya
# ─────────────────────────────────────────
async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if state.game_started:
        await update.message.reply_text(
            "😔 O'yin allaqachon boshlangan!\nKeyingi o'yinni kuting."
        )
        return ConversationHandler.END

    user = update.effective_user
    if state.find_participant(user.id):
        await update.message.reply_text("✅ Siz allaqachon ro'yxatdasiz!")
        return ConversationHandler.END

    await update.message.reply_text(
        "Ajoyib! Keling, sizni ro'yxatga olamiz 📝\n\n"
        "Iltimos, *ism va familiyangizni* kiriting:\n"
        "_(Masalan: Akmal Karimov yoki faqat Akmal)_\n\n"
        "Bekor qilish: /cancel",
        parse_mode="Markdown",
    )
    return NAME


async def handler_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = update.message.text.strip()

    if len(full_name) < 2:
        await update.message.reply_text("❌ Ism juda qisqa! Qaytadan kiriting:")
        return NAME

    context.user_data["full_name"] = full_name

    keyboard = [
        [KeyboardButton("✅ Ha, yozmoqchiman")],
        [KeyboardButton("⏭️ Yo'q, o'tkazib yuboraman")],
    ]
    await update.message.reply_text(
        f"Ajoyib, *{full_name}*\\! 😊\n\n"
        "Nimalarni yoqtirasiz? 🎁\n\n"
        "Bu ma'lumot sizga sovg'a beruvchiga yuboriladi\\.\n\n"
        "💡 _Masalan: Kitoblar 📚, Shokoladlar 🍫, Parfyum 💐_\n\n"
        "Yozmoqchimisiz?",
        parse_mode="MarkdownV2",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return PREFERENCES


async def handler_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    full_name = context.user_data["full_name"]

    if text == "✅ Ha, yozmoqchiman":
        await update.message.reply_text(
            "Yaxshi! Yoqtirgan narsalaringizni yozing:\n"
            "_(Masalan: Kitoblar, shokoladlar, qo'g'irchoqlar)_",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return PREFERENCES

    if text == "⏭️ Yo'q, o'tkazib yuboraman":
        preferences = "🤷 Istalgan narsa ham bo'ladi"
    else:
        preferences = text

    participant = Participant(
        user_id=user.id,
        username=user.username or user.first_name,
        full_name=full_name,
        preferences=preferences,
    )
    state.participants.append(participant)
    logger.info(f"Yangi ishtirokchi: {full_name} (id={user.id}), jami={len(state.participants)}")

    await update.message.reply_text(
        f"🎉 Tabriklaymiz! Muvaffaqiyatli ro'yxatdan o'tdingiz!\n\n"
        f"💰 Sovg'a narxi: kamida *100 000 so'm*\n\n"
        f"👤 Ism: {full_name}\n"
        f"🎁 Yoqtiradi: {preferences}\n\n"
        f"📊 Ishtirokchilar: *{len(state.participants)}* / {state.min_players}+\n\n"
        + build_status_text(),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ─────────────────────────────────────────
# /list
# ─────────────────────────────────────────
async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not state.participants:
        await update.message.reply_text(
            "😔 Hali hech kim ro'yxatdan o'tmagan!\n/join bilan qo'shiling!"
        )
        return

    lines = [f"🎁 *Secret Santa ishtirokchilari* ({len(state.participants)} kishi):\n"]
    for i, p in enumerate(state.participants, 1):
        lines.append(f"*{i}.* {p.full_name}")
        lines.append(f"   💝 _{p.preferences}_\n")

    lines.append(build_status_text())
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─────────────────────────────────────────
# /start_game
# ─────────────────────────────────────────
async def cmd_start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if state.game_started:
        await update.message.reply_text("O'yin allaqachon boshlangan! 🎁")
        return

    if not state.can_start():
        await update.message.reply_text(
            f"❌ O'yinni boshlash uchun kamida *{state.min_players}* kishi kerak!\n"
            f"📊 Hozir: {len(state.participants)}/{state.min_players}",
            parse_mode="Markdown",
        )
        return

    # Aylanma taqsimlash (derangement — hech kim o'ziga tushmasligi kafolatlangan)
    shuffled = state.participants.copy()
    random.shuffle(shuffled)
    for i, participant in enumerate(shuffled):
        participant.secret_santa_for = shuffled[(i + 1) % len(shuffled)]

    state.game_started = True
    logger.info(f"O'yin boshlandi! Ishtirokchilar: {len(state.participants)}")

    await update.message.reply_text(
        "🎉 O'yin boshlandi! Har bir ishtirokchiga maxfiy xabar yuborilmoqda… ⏳"
    )

    SUCCESS_MESSAGES = [
        (
            "🎁 *SECRET SANTA* 🎁\n\n"
            "Tabriklaymiz\\! Siz ushbu kishiga sovg'a berasiz:\n\n"
            "👤 *{name}*\n"
            "💝 Yoqtiradi: _{prefs}_\n\n"
            "🤫 Bu sirni hech kimga aytmang\\!\n"
            "💰 Sovg'a narxi: kamida *100 000 so'm*\n"
            "🎄 Bayram kuni uni quvontiring\\!\n\n"
            "Omad\\! 🌟"
        ),
        (
            "🕵️ *Maxfiy missiya qabul qilindi\\!* 🕵️\n\n"
            "Siz quyidagi kishiga sovg'a tayyorlaysiz:\n\n"
            "👤 *{name}*\n"
            "⭐ Qiziqishlari: _{prefs}_\n\n"
            "🔒 Sir saqlang\\!\n"
            "💰 Minimal narx: *100 000 so'm*\n"
            "🎊 Bayramda ajablantiring\\!\n\n"
            "🫶 Omad tilayman\\!"
        ),
        (
            "🎄 *Sizning Santa bo'lishingiz kerak\\!* 🎄\n\n"
            "Sovg'a egasi:\n\n"
            "👤 *{name}*\n"
            "🌈 Yoqtiradigan narsalari: _{prefs}_\n\n"
            "🤐 Shshsh… bu faqat sizga sir\\!\n"
            "💰 Sovg'a narxi: *100 000 so'm* dan kam bo'lmasin\n"
            "🥳 Bayram muborak bo'lsin\\!\n\n"
            "✨ Baxt sizga\\!"
        ),
    ]

    success_count = 0
    failed_users = []

    for participant in shuffled:
        receiver = participant.secret_santa_for
        msg_template = random.choice(SUCCESS_MESSAGES)
        msg = msg_template.format(
            name=receiver.full_name,
            prefs=receiver.preferences,
        )
        try:
            await context.bot.send_message(
                chat_id=participant.user_id,
                text=msg,
                parse_mode="MarkdownV2",
            )
            success_count += 1
        except Exception as e:
            logger.warning(f"Xabar yuborilmadi — {participant.full_name}: {e}")
            failed_users.append(participant.full_name)

    result = (
        f"✅ *{success_count}/{len(state.participants)}* kishiga xabar yuborildi!\n\n"
        "🎁 Endi har kim o'z sovg'asini tayyorlashi mumkin!\n"
        "🤐 Sirni saqlang va bayramda topshiring!\n\n"
        "Bosing jigar! 🎁"
    )
    if failed_users:
        result += "\n\n⚠️ Quyidagilarga yuborilmadi (bot bilan muloqot qilmaganlar):\n"
        result += "\n".join(f"• {n}" for n in failed_users)

    await update.message.reply_text(result, parse_mode="Markdown")


# ─────────────────────────────────────────
# /cancel
# ─────────────────────────────────────────
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Bekor qilindi. /join bilan qaytadan urinib ko'ring.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ─────────────────────────────────────────
# /reset (admin — xabarsiz)
# ─────────────────────────────────────────
async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not state.is_admin(user.id):
        await update.message.reply_text("❌ Bu buyruq faqat admin uchun!")
        return

    state.reset()
    logger.info(f"Admin {user.id} reset bajardi")
    await update.message.reply_text(
        "♻️ O'yin tozalandi!\nYangi ishtirokchilar /join bilan qo'shilishi mumkin."
    )


# ─────────────────────────────────────────
# /restart (admin — barcha ishtirokchilarga xabar bilan)
# ─────────────────────────────────────────
async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not state.is_admin(user.id):
        await update.message.reply_text("❌ Bu buyruq faqat admin uchun!")
        return

    if not state.participants:
        await update.message.reply_text(
            "ℹ️ Ishtirokchilar yo'q. /join bilan yangi o'yin boshlang."
        )
        return

    total = len(state.participants)
    await update.message.reply_text(
        f"📢 {total} ta ishtirokchiga xabar yuborilmoqda… ⏳"
    )

    restart_msg = (
        "🔄 *O'YIN QAYTADAN BOSHLANDI\\!*\n\n"
        "Admin Secret Santa o'yinini qaytadan boshladi\\.\n\n"
        "❌ Avvalgi ro'yxat bekor qilindi\\.\n\n"
        "💡 Qayta o'ynashni istasangiz:\n"
        "/join buyrug'i bilan ro'yxatdan o'ting\\!\n\n"
        "Rahmat\\! 🎁"
    )

    success = 0
    for p in state.participants:
        try:
            await context.bot.send_message(
                chat_id=p.user_id, text=restart_msg, parse_mode="MarkdownV2"
            )
            success += 1
        except Exception as e:
            logger.warning(f"restart xabar yuborilmadi — {p.full_name}: {e}")

    state.reset()
    logger.info(f"Admin {user.id} restart bajardi. Xabar: {success}/{total}")

    await update.message.reply_text(
        f"✅ Restart bajarildi!\n\n"
        f"📊 Xabar yuborildi: *{success}/{total}*\n\n"
        "♻️ O'yin tozalandi. /join bilan yangi o'yin boshlang!",
        parse_mode="Markdown",
    )


# ─────────────────────────────────────────
# /status — o'yin holati
# ─────────────────────────────────────────
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "🟢 Boshlangan" if state.game_started else "🔴 Boshlanmagan"
    await update.message.reply_text(
        f"📊 *O'yin holati:*\n\n"
        f"• Holat: {status}\n"
        f"• Ishtirokchilar: *{len(state.participants)}* kishi\n"
        f"• Minimal kerakli: *{state.min_players}* kishi\n"
        f"• Adminlar soni: {len(state.admin_ids)}\n",
        parse_mode="Markdown",
    )


# ─────────────────────────────────────────
# Noto'g'ri buyruq uchun xabar
# ─────────────────────────────────────────
async def handler_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Noto'g'ri buyruq. /start yozing va buyruqlar ro'yxatini ko'ring."
    )


# ─────────────────────────────────────────
# main()
# ─────────────────────────────────────────
def main():
    logger.info("🎁 Secret Santa Bot ishga tushmoqda...")

    app = Application.builder().token(TOKEN).build()

    # Join conversation
    join_conv = ConversationHandler(
        entry_points=[CommandHandler("join", cmd_join)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handler_name)],
            PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handler_preferences)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # set_min_players conversation
    set_min_conv = ConversationHandler(
        entry_points=[CommandHandler("set_min_players", cmd_set_min_start)],
        states={
            SET_MIN_PLAYERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_set_min_value)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(join_conv)
    app.add_handler(set_min_conv)
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("start_game", cmd_start_game))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(MessageHandler(filters.COMMAND, handler_unknown))

    logger.info(f"✅ Bot tayyor! min_players={state.min_players}")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()