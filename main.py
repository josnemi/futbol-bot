import os
import sqlite3
import logging
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
REFERRAL_LINK = os.environ.get("REFERRAL_LINK", "")
PRIVATE_CHANNEL_ID = int(os.environ.get("PRIVATE_CHANNEL_ID", "0"))
WELCOME_IMAGE_URL = os.environ.get("WELCOME_IMAGE_URL", "")
KUPON_IMAGE_URL = os.environ.get("KUPON_IMAGE_URL", "")

# ============================================================
# FLASK KEEP-ALIVE (Render 7/24)
# ============================================================
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

# ============================================================
# SQLITE DATABASE
# ============================================================
DB_FILE = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            language TEXT DEFAULT 'en',
            status TEXT DEFAULT 'new',
            partner_id TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
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
    c.execute("""
        INSERT OR REPLACE INTO users (telegram_id, username, first_name, language, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'new', ?, ?)
    """, (telegram_id, username, first_name, language, now, now))
    conn.commit()
    conn.close()

def update_user_status(telegram_id, status, partner_id=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().isoformat()
    if partner_id:
        c.execute("UPDATE users SET status = ?, partner_id = ?, updated_at = ? WHERE telegram_id = ?",
                  (status, partner_id, now, telegram_id))
    else:
        c.execute("UPDATE users SET status = ?, updated_at = ? WHERE telegram_id = ?",
                  (status, now, telegram_id))
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

# ============================================================
# INLINE KEYBOARDS
# ============================================================
def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en'),
         InlineKeyboardButton("🇧🇩 Bengali", callback_data='lang_bn')]
    ])

def registered_keyboard_en():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I Registered - Send My ID", callback_data='registered')]
    ])

def registered_keyboard_bn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ আমি রেজিস্টার করেছি - ID দিন", callback_data='registered')]
    ])

# ============================================================
# COMMAND HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username or "", user.first_name or "", "en")
    await update.message.reply_text(
        "Please choose your language / অনুগ্রহ করে ভাষা নির্বাচন করুন:",
        reply_markup=language_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == 'lang_en':
        add_user(user.id, user.username or "", user.first_name or "", "en")
        welcome_text = ("⚽ WELCOME TO THE ELITE ANALYSIS HUB" + "

" +
                        "📊 Daily football statistics and data-driven predictions." + "
" +
                        "🏆 Premier League, La Liga, Champions League coverage." + "

" +
                        "🎯 HOW TO ACCESS VIP MODEL OUTPUTS:" + "
" +
                        "1️⃣ Register on our partner platform using the link below." + "
" +
                        "2️⃣ Complete your first transaction (Minimum 500 BDT)." + "
" +
                        "3️⃣ Return here and click 'I Registered'." + "
" +
                        "4️⃣ Type your Partner Site ID in this chat." + "
" +
                        "5️⃣ Our team will verify within 24 hours and send your private access link." + "

" +
                        "👉 CLICK HERE TO REGISTER 👈")
        if WELCOME_IMAGE_URL:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=WELCOME_IMAGE_URL,
                caption=welcome_text,
                reply_markup=registered_keyboard_en()
            )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text=welcome_text,
                reply_markup=registered_keyboard_en()
            )

    elif query.data == 'lang_bn':
        add_user(user.id, user.username or "", user.first_name or "", "bn")
        welcome_text = ("⚽ এলিট অ্যানালাইসিস হাবে আপনাকে স্বাগতম" + "

" +
                        "📊 দৈনিক ফুটবল পরিসংখ্যান এবং ডেটা-ভিত্তিক বিশ্লেষণ।" + "
" +
                        "🏆 প্রিমিয়ার লিগ, লা লিগা, চ্যাম্পিয়নস লিগ কভারেজ।" + "

" +
                        "🎯 VIP মডেল আউটপুট অ্যাক্সেস করার উপায়:" + "
" +
                        "1️⃣ নিচের লিঙ্কটি ব্যবহার করে আমাদের পার্টনার প্ল্যাটফর্মে নিবন্ধন করুন।" + "
" +
                        "2️⃣ আপনার প্রথম লেনদেন সম্পন্ন করুন (সর্বনিম্ন 500 BDT)।" + "
" +
                        "3️⃣ এখানে ফিরে 'আমি রেজিস্টার করেছি' তে ক্লিক করুন।" + "
" +
                        "4️⃣ এই চ্যাটে আপনার Partner Site ID টাইপ করুন।" + "
" +
                        "5️⃣ আমাদের টিম ২৪ ঘণ্টার মধ্যে যাচাই করবে এবং আপনার ব্যক্তিগত অ্যাক্সেস লিঙ্ক পাঠাবে।" + "

" +
                        "👉 নিবন্ধন করতে এখানে ক্লিক করুন 👈")
        if WELCOME_IMAGE_URL:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=WELCOME_IMAGE_URL,
                caption=welcome_text,
                reply_markup=registered_keyboard_bn()
            )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text=welcome_text,
                reply_markup=registered_keyboard_bn()
            )

    elif query.data == 'registered':
        row = get_user(user.id)
        lang = row[3] if row else 'en'
        update_user_status(user.id, 'awaiting_id')
        if lang == 'bn':
            caption = "📈 এখানে আমাদের কিছু উচ্চ-অডসের VIP বিশ্লেষণ রয়েছে! অ্যাক্সেস পেতে এখন এই চ্যাটে আপনার Partner Site ID নম্বর লিখুন।"
        else:
            caption = "📈 Here are some of our high-odds VIP analysis results! To get access, please type your Partner Site ID number in this chat now."
        if KUPON_IMAGE_URL:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=KUPON_IMAGE_URL,
                caption=caption
            )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text=caption
            )

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
            await update.message.reply_text("❌ অনুগ্রহ করে শুধুমাত্র ৩ থেকে ২০ সংখ্যার মধ্যে আপনার Partner Site ID নম্বরটি লিখুন।")
        else:
            await update.message.reply_text("❌ Please enter only a numeric Partner Site ID between 3 and 20 digits.")
        return
    update_user_status(user.id, 'pending', text)
    if lang == 'bn':
        await update.message.reply_text("✅ আপনার তথ্য ২৪ ঘণ্টার মধ্যে যাচাই করা হবে। অনুমোদিত হলে আপনার ব্যক্তিগত VIP লিঙ্ক পাঠানো হবে।")
    else:
        await update.message.reply_text("✅ Your information will be checked within 24 hours. Once approved, your private VIP link will be sent.")
    username = user.username or "No username"
    first_name = user.first_name or "No name"
    admin_msg = ("🆕 NEW APPLICATION" + "

" +
                 "👤 User: @" + username + "
" +
                 "📝 Name: " + first_name + "
" +
                 "🆔 Telegram ID: " + str(user.id) + "
" +
                 "🔢 Partner Site ID: " + text + "
" +
                 "🌐 Language: " + ('Bengali' if lang == 'bn' else 'English') + "

" +
                 "Approve with:" + "
" +
                 "/onay " + str(user.id))
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)

# ============================================================
# ADMIN COMMANDS
# ============================================================

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    pending = get_pending_users()
    if not pending:
        await update.message.reply_text("There are no pending ID submissions.")
        return
    text = "⏳ PENDING APPLICATIONS:" + "

"
    for row in pending:
        tid, username, first_name, partner_id, created_at = row
        text += "👤 @" + (username or 'N/A') + " | " + (first_name or 'N/A') + "
"
        text += "🆔 Telegram ID: " + str(tid) + "
"
        text += "🔢 Partner ID: " + (partner_id or 'N/A') + "
"
        text += "📅 Date: " + created_at + "
"
        text += "✅ Approve: /onay " + str(tid) + "

"
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
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=PRIVATE_CHANNEL_ID,
            expire_date=datetime.now() + timedelta(hours=1),
            member_limit=1
        )
        update_user_status(target_id, 'approved')
        if lang == 'bn':
            msg = ("🎉 আপনার ID অনুমোদিত হয়েছে!" + "

" +
                   "⚠️ GÜVENLİK KURALLARI:" + "
" +
                   "• এই লিঙ্কটি শুধুমাত্র আপনার জন্য।" + "
" +
                   "• এটি শুধুমাত্র ১ বার ব্যবহার করা যাবে।" + "
" +
                   "• ১ ঘণ্টার মধ্যে ব্যবহার করুন, নতুবা মেয়াদ শেষ হয়ে যাবে।" + "
" +
                   "• অন্যের সাথে শেয়ার করলে সে প্রবেশ করবে, আপনি করতে পারবেন না।" + "

" +
                   "🔗 আপনার VIP লিঙ্ক:" + "
" +
                   invite_link.invite_link + "

" +
                   "তাড়াতাড়ি ক্লিক করুন এবং ক্যানেলে যোগ দিন!")
        else:
            msg = ("🎉 Your ID has been approved!" + "

" +
                   "⚠️ SECURITY RULES:" + "
" +
                   "• This link is for YOU only." + "
" +
                   "• It can only be used ONCE." + "
" +
                   "• Use it within 1 hour or it will expire." + "
" +
                   "• If you share it with someone else, THEY will enter, YOU will not." + "

" +
                   "🔗 YOUR VIP LINK:" + "
" +
                   invite_link.invite_link + "

" +
                   "Click quickly and join the channel!")
        await context.bot.send_message(chat_id=target_id, text=msg)
        await update.message.reply_text("✅ User " + str(target_id) + " approved. One-time invite link sent.")
    except Exception as e:
        await update.message.reply_text("❌ Error creating invite link: " + str(e) + "

" +
                                        "Make sure:" + "
" +
                                        "1. PRIVATE_CHANNEL_ID is correct" + "
" +
                                        "2. Bot is admin in the private channel" + "
" +
                                        "3. Bot has 'Invite Users via Link' permission")

# ============================================================
# MAIN
# ============================================================
def main():
    init_db()
    keep_alive()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("liste", list_pending))
    application.add_handler(CommandHandler("onay", approve))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot calisiyor...")
    application.run_polling()

if __name__ == "__main__":
    main()
