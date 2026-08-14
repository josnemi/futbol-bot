import os
import sqlite3
import logging
from datetime import datetime
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
        [InlineKeyboardButton("✅ I Registered - Show VIP Coupons & Send ID", callback_data='registered')]
    ])

def registered_keyboard_bn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ আমি রেজিস্টার করেছি - কুপন দেখুন এবং ID দিন", callback_data='registered')]
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
        welcome_text = """🔥 <b>WELCOME TO ELITE VIP SPORTS INVESTORS!</b> 🔥

🎁 Our partner Mostbet is offering a <b>MASSIVE bonus</b> for all new users!
🏆 It is the #1 largest site in the country for user base and big wins.
💸 Right now, they are giving a Mega Bonus up to <b>25,000 BDT + 250 Free Spins</b> on your first deposit.

🚨 <b>How to get the offer:</b>
You MUST use our special promo code <b>KAAURA</b> during registration. (No code = No bonus!)
3️⃣ Make your first deposit (Minimum 500 BDT) (via bKash, Nagad, Rocket, or Crypto).
You will find many more attractive offers, tournaments, and huge bonuses on the site.

👉 <a href="https://3dqeka7xzlun7d5mst.com/qxOU">CLICK HERE TO GO TO OFFICIAL WEBSITE & GET 25,000 BDT BONUS</a> 👈"""

        await context.bot.send_photo(
            chat_id=user.id,
            photo=WELCOME_IMAGE_URL,
            caption=welcome_text,
            parse_mode='HTML',
            reply_markup=registered_keyboard_en()
        )

    elif query.data == 'lang_bn':
        add_user(user.id, user.username or "", user.first_name or "", "bn")
        welcome_text = """🔥 <b>এলিট ভিআইপি স্পোর্টস ইনভেস্টরদের স্বাগতম!</b> 🔥

🎁 আমাদের পার্টনার মোস্টবেট, বাংলাদেশের সকল নতুন ব্যবহারকারীদের জন্য একটি বিশাল বোনাস অফার করছে।
🏆 ব্যবহারকারীর সংখ্যা এবং বড় জয়ের দিক থেকে এটি দেশের এক নম্বর (১ম) এবং সবচেয়ে বড় সাইট।
💸 এই মুহূর্তে, তারা সকল নতুন ব্যবহারকারীদের প্রথম ডিপোজিটে <b>25,000 BDT + 250 ফ্রি স্পিন</b> পর্যন্ত মেগা বোনাস দিচ্ছে।

🚨 <b>অফারটি পেতে করণীয়:</b>
রেজিস্ট্রেশন করার সময় অবশ্যই আমাদের স্পেশাল প্রোমো কোড <b>KAAURA</b> ব্যবহার করতে হবে। (কোডটি না দিলে বোনাস পাবেন না!)
3️⃣ আপনার প্রথম ডিপোজিট সম্পন্ন করুন (সর্বনিম্ন 500 BDT)।
সাইটে আপনি আরও অনেক আকর্ষণীয় অফার, টুর্নামেন্ট এবং বিশাল বোনাস পাবেন।

👉 <a href="https://3dqeka7xzlun7d5mst.com/qxOU">অফিসিয়াল ওয়েবসাইটে যান (এখানে ক্লিক করুন) এবং 25,000 BDT বোনাস নিন</a> 👈"""

        await context.bot.send_photo(
            chat_id=user.id,
            photo=WELCOME_IMAGE_URL,
            caption=welcome_text,
            parse_mode='HTML',
            reply_markup=registered_keyboard_bn()
        )

    elif query.data == 'registered':
        row = get_user(user.id)
        lang = row[3] if row else 'en'
        update_user_status(user.id, 'awaiting_id')

        if lang == 'bn':
            caption = "📈 এখানে আমাদের কিছু +5 এবং +10 অডসের VIP জয় রয়েছে! অ্যাক্সেস পেতে এখন এই চ্যাটে আপনার Partner Site ID নম্বর লিখুন।"
        else:
            caption = "📈 Here are some of our +5 and +10 odds VIP wins! To get access, please type your Partner Site ID number in this chat now."

        await context.bot.send_photo(
            chat_id=user.id,
            photo=KUPON_IMAGE_URL,
            caption=caption,
            parse_mode='HTML'
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

    # ID validation: 3-20 digits only
    if not text.isdigit() or len(text) < 3 or len(text) > 20:
        if lang == 'bn':
            await update.message.reply_text("❌ অনুগ্রহ করে শুধুমাত্র ৩ থেকে ২০ সংখ্যার মধ্যে আপনার Partner Site ID নম্বরটি লিখুন।")
        else:
            await update.message.reply_text("❌ Please enter only a numeric Partner Site ID between 3 and 20 digits.")
        return

    update_user_status(user.id, 'pending', text)

    if lang == 'bn':
        await update.message.reply_text("✅ আপনার তথ্য ২৪ ঘণ্টার মধ্যে যাচাই করা হবে।")
    else:
        await update.message.reply_text("✅ Your information will be checked within 24 hours.")

    # Notify admin
    username = user.username or "No username"
    first_name = user.first_name or "No name"
    admin_msg = f"""🆕 NEW APPLICATION

👤 User: @{username}
📝 Name: {first_name}
🆔 Telegram ID: {user.id}
🔢 Partner Site ID: {text}
🌐 Language: {'Bengali' if lang == 'bn' else 'English'}

Approve with:
/onay {user.id}"""

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

    text = "⏳ PENDING APPLICATIONS:

"
    for row in pending:
        tid, username, first_name, partner_id, created_at = row
        text += f"👤 @{username or 'N/A'} | {first_name or 'N/A'}
"
        text += f"🆔 Telegram ID: {tid}
"
        text += f"🔢 Partner ID: {partner_id}
"
        text += f"📅 Date: {created_at}
"
        text += f"✅ Approve: /onay {tid}

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
        await update.message.reply_text(f"❌ User {target_id} not found.")
        return

    if row[4] != 'pending':
        await update.message.reply_text(f"❌ User {target_id} is not pending (status: {row[4]}).")
        return

    if not row[5]:
        await update.message.reply_text(f"❌ User {target_id} has no Partner Site ID.")
        return

    update_user_status(target_id, 'approved')
    lang = row[3]

    if lang == 'bn':
        msg = "🎉 আপনার ID অনুমোদিত হয়েছে। VIP অ্যাক্সেস টিম শীঘ্রই আপনার সাথে যোগাযোগ করবে।"
    else:
        msg = "🎉 Your ID has been approved. The VIP access team will contact you shortly."

    await context.bot.send_message(chat_id=target_id, text=msg)
    await update.message.reply_text(f"✅ User {target_id} approved successfully.")

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
