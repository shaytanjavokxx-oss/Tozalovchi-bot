import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                           MessageHandler, ChatMemberHandler, filters, ContextTypes)
from config import *
from database import *

logging.basicConfig(level=logging.INFO)

# Kutayotgan foydalanuvchilar {user_id: message_id}
pending_users = {}

# ═══════════════════════════════════════
#         KANAL TEKSHIRISH
# ═══════════════════════════════════════
async def kanal_tekshir(bot, user_id):
    if user_id == ADMIN_ID:
        return True
    for kanal in KANALLAR:
        try:
            member = await bot.get_chat_member(kanal["username"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ═══════════════════════════════════════
#         YANGI A'ZO GURUHGA KIRDI
# ═══════════════════════════════════════
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    for user in update.message.new_chat_members:
        if user.is_bot:
            continue

        uid = user.id
        chat_id = update.message.chat_id
        name = user.first_name

        # Kanal tekshirish
        obunachi = await kanal_tekshir(context.bot, uid)

        if obunachi:
            # Allaqachon obunachi — qabul qilish
            member_qoshish(uid, user.username, user.first_name)

            # Kim taklif qildi?
            if update.message.from_user and update.message.from_user.id != uid:
                inviter_id = update.message.from_user.id
                invite_qoshish(inviter_id, uid)

            await update.message.reply_text(
                f"👋 Xush kelibsiz, {name}!\n"
                f"Guruhga qo'shildingiz."
            )
        else:
            # Obunachi emas — cheklash va xabar yuborish
            try:
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=uid,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False
                    )
                )
            except:
                pass

            btns = [[InlineKeyboardButton(f"➕ {k['nomi']}", url=k["url"])] for k in KANALLAR]
            btns.append([InlineKeyboardButton("✅ Tekshirish", callback_data=f"check_{uid}_{chat_id}")])

            msg = await update.message.reply_text(
                f"👋 Salom, {name}!\n\n"
                f"Guruhda yozish uchun quyidagi kanallarga a'zo bo'ling:\n\n"
                f"A'zo bo'lgach Tekshirish tugmasini bosing.",
                reply_markup=InlineKeyboardMarkup(btns)
            )

            pending_users[uid] = {"chat_id": chat_id, "msg_id": msg.message_id}

            # 2 daqiqadan keyin chiqarib yuborish
            asyncio.create_task(kick_if_not_subscribed(context.bot, uid, chat_id, msg.message_id))

# ═══════════════════════════════════════
#         CHIQARIB YUBORISH
# ═══════════════════════════════════════
async def kick_if_not_subscribed(bot, user_id, chat_id, msg_id):
    await asyncio.sleep(KICK_TIMEOUT)

    obunachi = await kanal_tekshir(bot, user_id)
    if not obunachi and user_id in pending_users:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            await bot.send_message(
                chat_id=chat_id,
                text=f"Foydalanuvchi kanallarga a'zo bo'lmaganligi sababli chiqarib yuborildi."
            )
        except:
            pass
        pending_users.pop(user_id, None)

# ═══════════════════════════════════════
#         TEKSHIRISH CALLBACK
# ═══════════════════════════════════════
async def check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    target_uid = int(parts[1])
    chat_id = int(parts[2])
    uid = query.from_user.id

    if uid != target_uid:
        await query.answer("Bu tugma siz uchun emas!", show_alert=True)
        return

    obunachi = await kanal_tekshir(context.bot, uid)

    if not obunachi:
        await query.answer("Hali barcha kanallarga a'zo bolmadingiz!", show_alert=True)
        return

    # Obunachi — cheklashni olib tashlash
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=uid,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
    except:
        pass

    member_qoshish(uid, query.from_user.username, query.from_user.first_name)
    pending_users.pop(uid, None)

    await query.edit_message_text(
        f"✅ {query.from_user.first_name} tekshirildi!\nGuruhga xush kelibsiz!"
    )

# ═══════════════════════════════════════
#         /START (shaxsiy chat)
# ═══════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    menu = admin_menyu() if uid == ADMIN_ID else user_menyu()

    from telegram import ReplyKeyboardMarkup
    await update.message.reply_text(
        f"🤖 Majburiy Azo Bot\n\n"
        f"Bot guruhga admin qilinsa, yangi a'zolardan kanal obunasini tekshiradi.\n\n"
        f"Obuna bo'lmaganlar {KICK_TIMEOUT} soniyada chiqarib yuboriladi.\n\n"
        f"Admin: {ADMIN_USERNAME}",
        reply_markup=menu
    )

def user_menyu():
    from telegram import ReplyKeyboardMarkup
    return ReplyKeyboardMarkup([
        ["📊 Reyting"],
        ["ℹ️ Malumot"],
    ], resize_keyboard=True)

def admin_menyu():
    from telegram import ReplyKeyboardMarkup
    return ReplyKeyboardMarkup([
        ["📊 Statistika", "👥 Azolar"],
        ["🏆 Top Inviters", "📢 Xabar yuborish"],
        ["📊 Reyting", "ℹ️ Malumot"],
    ], resize_keyboard=True)

# ═══════════════════════════════════════
#         REYTING
# ═══════════════════════════════════════
async def reyting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = top_inviters(10)
    if not top:
        await update.message.reply_text("Hozircha malumot yoq.")
        return

    medals = ["🥇","🥈","🥉","4.","5.","6.","7.","8.","9.","10."]
    text = "🏆 TOP 10 TAKLIF QILGANLAR\n━━━━━━━━━━━━━━\n\n"
    for i, u in enumerate(top):
        name = u[2] or u[1] or "Anonim"
        un = f"@{u[1]}" if u[1] else ""
        text += f"{medals[i]} {name} {un} — {u[3]} kishi\n"

    await update.message.reply_text(text)

# ═══════════════════════════════════════
#         ADMIN BUYRUQLAR
# ═══════════════════════════════════════
async def statistika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    jami = jami_members()
    top = top_inviters(3)
    medals = ["🥇","🥈","🥉"]
    text = f"📊 STATISTIKA\n━━━━━━━━━━━━━━\n\nJami azolar: {jami}\n\nTOP 3:\n"
    for i, u in enumerate(top):
        name = u[2] or u[1] or "Anonim"
        text += f"{medals[i]} {name} — {u[3]} kishi taklif qildi\n"
    await update.message.reply_text(text)

async def azolar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    members = barcha_members()
    if not members:
        await update.message.reply_text("Hozircha azolar yoq.")
        return
    text = f"👥 AZOLAR ({len(members)} kishi)\n━━━━━━━━━━━━━━\n\n"
    for i, m in enumerate(members[:30], 1):
        name = m[2] or "Anonim"
        un = f"@{m[1]}" if m[1] else ""
        text += f"{i}. {name} {un}\n"
    await update.message.reply_text(text)

broadcast_mode = {}

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    broadcast_mode[ADMIN_ID] = True
    await update.message.reply_text("Xabar yozing — barcha azolarga yuboriladi.\nBekor: /cancel")

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broadcast_mode[ADMIN_ID] = False
    members = barcha_members()
    text = update.message.text
    ok = 0
    xato = 0
    await update.message.reply_text(f"Yuborilmoqda {len(members)} ta azoga...")
    for m in members:
        try:
            await context.bot.send_message(chat_id=m[0], text=text)
            ok += 1
        except:
            xato += 1
    await update.message.reply_text(f"Yuborildi!\nMuvaffaqiyatli: {ok}\nXato: {xato}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    broadcast_mode[ADMIN_ID] = False
    await update.message.reply_text("Bekor qilindi.")

async def malumot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"ℹ️ BOT MALUMOTI\n━━━━━━━━━━━━━━\n\n"
        f"Bot guruhga admin qilinsa:\n"
        f"Yangi azolar kanalga obuna bolganini tekshiradi.\n"
        f"Obuna bolmaganlar {KICK_TIMEOUT} soniyada chiqarib yuboriladi.\n\n"
        f"Kanallar:\n" + "\n".join([f"• {k['nomi']}" for k in KANALLAR])
    )

# ═══════════════════════════════════════
#         XABAR HANDLER
# ═══════════════════════════════════════
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    uid = update.message.from_user.id
    text = update.message.text

    if broadcast_mode.get(uid) and uid == ADMIN_ID:
        await broadcast_send(update, context)
        return

    handlers = {
        "📊 Reyting": reyting,
        "ℹ️ Malumot": malumot,
    }
    admin_handlers = {
        "📊 Statistika": statistika,
        "👥 Azolar": azolar,
        "🏆 Top Inviters": reyting,
        "📢 Xabar yuborish": broadcast_start,
    }

    if text in handlers:
        await handlers[text](update, context)
    elif text in admin_handlers and uid == ADMIN_ID:
        await admin_handlers[text](update, context)

# ═══════════════════════════════════════
#         MAIN
# ═══════════════════════════════════════
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(check_callback, pattern="^check_"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("✅ Majburiy Azo Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
