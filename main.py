import os
import sqlite3
import logging
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
REFERRAL_LINK = os.environ.get("REFERRAL_LINK", "")
PRIVATE_CHANNEL_ID = int(os.environ.get("PRIVATE_CHANNEL_ID", "0"))
WELCOME_IMAGE_URL = os.environ.get("WELCOME_IMAGE_URL", "")
KUPON_IMAGE_URL = os.environ.get("KUPON_IMAGE_URL", "")

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask('')

@app.route('/')
def home():
    return "Bot 7/24 Aktif"

def run_flask():
    port = int(os.environ.get("PORT", "10000"))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

DB_FILE = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, language TEXT DEFAULT 'en', status TEXT DEFAULT 'new', partner_id TEXT, created_at TEXT, updated_at TEXT)")
    conn.commit()
    conn.close()

def get_user(telegram_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_user(telegram_id, username, first_name, language):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT OR REPLACE INTO users (telegram_id, username, first_name, language, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'new', ?, ?)", (telegram_id, username, first_name, language, now, now))
    conn.commit()
    conn.close()

def update_user_status(telegram_id, status, partner_id=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().isoformat()
    if partner_id:
        c.execute("UPDATE users SET status = ?, partner_id = ?, updated_at = ? WHERE telegram_id = ?", (status, partner_id, now, telegram_id))
    else:
        c.execute("UPDATE users SET status = ?, updated_at = ? WHERE telegram_id = ?", (status, now, telegram_id))
    conn.commit()
    conn.close()

def get_pending_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT telegram_id, username, first_name, partner_id, created_at FROM users WHERE status = 'pending'")
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_by_id(telegram_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    return row

def language_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🇬🇧 English", callback_data='lang_en'), InlineKeyboardButton("🇧🇩 Bengali", callback_data='lang_bn')]])

def registered_keyboard_en():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ I Registered - Send My ID", callback_data='registered')]])

def registered_keyboard_bn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ আমি রেজিস্টার করেছি - আইডি পাঠান", callback_data='registered')]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username or "", user.first_name or "", "en")
    await update.message.reply_text("Please choose your language:", reply_markup=language_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == 'lang_en':
        add_user(user.id, user.username or "", user.first_name or "", "en")
        n = chr(10)
        welcome_text = "⚽ WELCOME TO THE ELITE ANALYSIS HUB" + n + n + "📊 Daily football statistics and data-driven predictions." + n + "🏆 Premier League, La Liga, Champions League coverage." + n + n + "🎯 HOW TO ACCESS VIP MODEL OUTPUTS:" + n + "1️⃣ Register on our partner platform using the link below." + n + "2️⃣ Complete your first transaction (Minimum 500 BDT)." + n + "3️⃣ Return here and click I Registered." + n + "4️⃣ Type your Partner Site ID in this chat." + n + "5️⃣ Our team will verify within 24 hours and send your private access link." + n + n + "🔗 LINK: " + REFERRAL_LINK + n + n + "⚠️ Important: Registration alone is not enough. Approval is given only after the first transaction is completed."
        if WELCOME_IMAGE_URL:
            await context.bot.send_photo(chat_id=user.id, photo=WELCOME_IMAGE_URL, caption=welcome_text, reply_markup=registered_keyboard_en())
        else:
            await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=registered_keyboard_en())

    elif query.data == 'lang_bn':
        add_user(user.id, user.username or "", user.first_name or "", "bn")
        n = chr(10)
        welcome_text = "⚽ এলিট অ্যানালাইসিস হাবে আপনাকে স্বাগতম" + n + n + "📊 প্রতিদিন ফুটবল পরিসংখ্যান এবং ডেটা-ভিত্তিক পূর্বাভাস।" + n + "🏆 প্রিমিয়ার লিগ, লা লিগা, চ্যাম্পিয়ন্স লিগ কভারেজ।" + n + n + "🎯 VIP মডেল আউটপুট কীভাবে পাবেন:" + n + "1️⃣ নিচের লিঙ্কে ক্লিক করে পার্টনার প্ল্যাটফর্মে রেজিস্টার করুন।" + n + "2️⃣ প্রথম ট্রানজাকশন সম্পন্ন করুন (সর্বনিম্ন ৫০০ BDT)।" + n + "3️⃣ এখানে ফিরে এসে 'আমি রেজিস্টার করেছি' তে ক্লিক করুন।" + n + "4️⃣ এই চ্যাটে আপনার পার্টনার সাইট আইডি টাইপ করুন।" + n + "5️⃣ আমাদের টিম ২৪ ঘন্টার মধ্যে যাচাই করবে এবং আপনার প্রাইভেট অ্যাক্সেস লিঙ্ক পাঠাবে।" + n + n + "🔗 লিঙ্ক: " + REFERRAL_LINK + n + n + "⚠️ গুরুত্বপূর্ণ: শুধু রেজিস্ট্রেশন করলেই হবে না। প্রথম ট্রানজাকশন সম্পন্ন করার পরেই অনুমোদন দেওয়া হবে।"
        if WELCOME_IMAGE_URL:
            await context.bot.send_photo(chat_id=user.id, photo=WELCOME_IMAGE_URL, caption=welcome_text, reply_markup=registered_keyboard_bn())
        else:
            await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=registered_keyboard_bn())

    elif query.data == 'registered':
        row = get_user(user.id)
        lang = row[3] if row else 'en'
        update_user_status(user.id, 'awaiting_id')
        if lang == 'bn':
            caption = "📈 এখানে কিছু হাই-অডস VIP অ্যানালাইসিস রেজাল্ট দেখুন! অ্যাক্সেস পেতে এই চ্যাটে আপনার পার্টনার সাইট আইডি নম্বর টাইপ করুন।"
        else:
            caption = "📈 Here are some of our high-odds VIP analysis results! To get access, please type your Partner Site ID number in this chat now."
        if KUPON_IMAGE_URL:
            await context.bot.send_photo(chat_id=user.id, photo=KUPON_IMAGE_URL, caption=caption)
        else:
            await context.bot.send_message(chat_id=user.id, text=caption)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    if text.startswith('/'):
        return
    row = get_user(user.id)
    if not row:
        await update.message.reply_text("Please choose your language first: /start")
        return
    lang = row[3]
    status = row[4]
    if status != 'awaiting_id':
        return
    if not text.isdigit() or len(text) < 3 or len(text) > 20:
        if lang == 'bn':
            await update.message.reply_text("❌ শুধুমাত্র সংখ্যাসূচক পার্টনার সাইট আইডি দিন (৩ থেকে ২০ ডিজিটের মধ্যে)।")
        else:
            await update.message.reply_text("❌ Please enter only a numeric Partner Site ID between 3 and 20 digits.")
        return
    update_user_status(user.id, 'pending', text)
    if lang == 'bn':
        await update.message.reply_text("✅ আপনার তথ্য ২৪ ঘন্টার মধ্যে যাচাই করা হবে। অনুমোদিত হলে আপনার প্রাইভেট VIP লিঙ্ক পাঠানো হবে।")
    else:
        await update.message.reply_text("✅ Your information will be checked within 24 hours. Once approved, your private VIP link will be sent.")
    n = chr(10)
    username = user.username or "No username"
    first_name = user.first_name or "No name"
    admin_msg = "🆕 NEW APPLICATION" + n + n + "👤 User: @" + username + n + "📝 Name: " + first_name + n + "🆔 Telegram ID: " + str(user.id) + n + "🔢 Partner Site ID: " + text + n + "🌐 Language: " + ('Bengali' if lang == 'bn' else 'English') + n + n + "✅ Approve with:" + n + "/onay " + str(user.id)
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    pending = get_pending_users()
    if not pending:
        await update.message.reply_text("📭 There are no pending ID submissions.")
        return
    n = chr(10)
    text = "⏳ PENDING APPLICATIONS:" + n + n
    for row in pending:
        tid, username, first_name, partner_id, created_at = row
        text += "👤 @" + (username or 'N/A') + " | " + (first_name or 'N/A') + n
        text += "🆔 Telegram ID: " + str(tid) + n
        text += "🔢 Partner ID: " + (partner_id or 'N/A') + n
        text += "📅 Date: " + created_at + n
        text += "✅ Approve: /onay " + str(tid) + n + n
    await update.message.reply_text(text)

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /onay [telegram_user_id]")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    row = get_user_by_id(target_id)
    if not row:
        await update.message.reply_text("❌ User " + str(target_id) + " not found.")
        return
    if row[4] != 'pending':
        await update.message.reply_text("❌ User " + str(target_id) + " is not pending (status: " + row[4] + ").")
        return
    if not row[5]:
        await update.message.reply_text("❌ User " + str(target_id) + " has no Partner Site ID.")
        return
    lang = row[3]
    try:
        invite_link = await context.bot.create_chat_invite_link(chat_id=PRIVATE_CHANNEL_ID, expire_date=datetime.now() + timedelta(hours=1), member_limit=1)
        update_user_status(target_id, 'approved')
        n = chr(10)
        if lang == 'bn':
            msg = "🎉 আপনার আইডি অনুমোদিত হয়েছে!" + n + n + "⚠️ নিরাপত্তা নিয়ম:" + n + "• এই লিঙ্ক শুধু আপনার জন্য।" + n + "• এটি শুধু একবার ব্যবহার করা যাবে।" + n + "• ১ ঘন্টার মধ্যে ব্যবহার করুন নাহলে মেয়াদ শেষ হয়ে যাবে।" + n + "• অন্য কাউকে শেয়ার করলে, তারা ঢুকবে, আপনি না।" + n + n + "🔗 আপনার VIP লিঙ্ক:" + n + invite_link.invite_link + n + n + "👉 দ্রুত ক্লিক করুন এবং চ্যানেলে জয়েন করুন!"
        else:
            msg = "🎉 Your ID has been approved!" + n + n + "⚠️ SECURITY RULES:" + n + "• This link is for YOU only." + n + "• It can only be used ONCE." + n + "• Use it within 1 hour or it will expire." + n + "• If you share it with someone else, THEY will enter, YOU will not." + n + n + "🔗 YOUR VIP LINK:" + n + invite_link.invite_link + n + n + "👉 Click quickly and join the channel!"
        await context.bot.send_message(chat_id=target_id, text=msg)
        await update.message.reply_text("✅ User " + str(target_id) + " approved. One-time invite link sent.")
    except Exception as e:
        await update.message.reply_text("❌ Error creating invite link: " + str(e) + n + n + "Make sure:" + n + "1. PRIVATE_CHANNEL_ID is correct" + n + "2. Bot is admin in the private channel" + n + "3. Bot has 'Invite Users via Link' permission")

def main():
    init_db()
    keep_alive()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("liste", list_pending))
    application.add_handler(CommandHandler("onay", approve))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot calisiyor...")
    application.run_polling()

if __name__ == "__main__":
    main()
