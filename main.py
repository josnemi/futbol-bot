import os
import json
import logging
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
REFERRAL_LINK = os.environ.get("REFERRAL_LINK", "")
PRIVATE_CHANNEL_ID = int(os.environ.get("PRIVATE_CHANNEL_ID", "0"))

# ============================================================
# FLASK KEEP-ALIVE
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
# VERI YONETIMI
# ============================================================
DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"pending": {}, "approved": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# KOMUTLAR
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = f"""⚽ HOS GELDIN!

Ben otomatik erisim asistaniyim.
Sana kimseyle konusmadan ozel iceriklere erisim saglarim.

Baslamak icin:
1️⃣ Asagidaki linkten kayit ol
2️⃣ Ilk islemini tamamla (onerilen: 500 BDT)
3️⃣ Bana site icindeki kullanici bilgini gonder
4️⃣ 24 saat icinde kontrol edilip onaylanirsin
5️⃣ Onay sonrasi ozel kanala ozel davet linkin otomatik iletilir

🔗 KAYIT LINKI: {REFERRAL_LINK}

⚠️ Onemli: Sadece kayit olmak yetmez.
Ilk islem tamamlanmadan onay verilmez."""
    
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    if text.startswith('/') or user.id == ADMIN_ID:
        return
    
    data = load_data()
    user_id = str(user.id)
    
    data["pending"][user_id] = {
        "username": user.username or "Belirtilmemis",
        "site_info": text,
        "first_name": user.first_name or ""
    }
    save_data(data)
    
    await update.message.reply_text(
        "✅ Bilgin alindi.\n\n"
        "⏳ 24 saat icinde sistem tarafindan kontrol edilecek.\n"
        "Ilk islemin onaylandiginda ozel davet linkin otomatik olarak iletilecek.\n\n"
        "Lutfen bekleyin."
    )

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu komuta erisiminiz yok.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Kullanim: /onay kullanici_bilgisi")
        return
    
    site_info = " ".join(context.args)
    data = load_data()
    
    found_user = None
    for uid, info in data["pending"].items():
        if info["site_info"].lower() == site_info.lower():
            found_user = uid
            break
    
    if not found_user:
        await update.message.reply_text(f"❌ '{site_info}' bilgisiyle eslesen kullanici bulunamadi.")
        return
    
    user_info = data["pending"].pop(found_user)
    data["approved"][found_user] = user_info
    save_data(data)
    
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=PRIVATE_CHANNEL_ID,
            expire_date=datetime.now() + timedelta(hours=1),
            member_limit=1
        )
        
        await context.bot.send_message(
            chat_id=int(found_user),
            text=f"""🎉 ONAYLANDIN.

Ozel kanala erisim icin davet linkin hazir.

⚠️ ONEMLI GUVENLIK KURALLARI:
• Bu link sadece SENIN icin olusturuldu
• Sadece 1 kez kullanilabilir
• 1 saat icinde kullanmazsan gecersiz olur
• Baskasiyla paylasirsen o girer, SEN giremezsin
• Ekran goruntusu alma, kanal guvenlik sistemi aktif

🔗 DAVET LINKIN: {invite_link.invite_link}

Hemen tikla ve kanala katil."""
        )
        
        await update.message.reply_text(f"✅ {site_info} onaylandi. Tek kullanimlik davet linki gonderildi.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Davet linki olusturulurken hata: {str(e)}")

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    data = load_data()
    pending = data["pending"]
    
    if not pending:
        await update.message.reply_text("📭 Bekleyen kullanici yok.")
        return
    
    text = "⏳ BEKLEYEN KULLANICILAR:\n\n"
    for uid, info in pending.items():
        username = info.get("username", "Bilinmiyor")
        site_info = info.get("site_info", "")
        text += f"👤 @{username}\n📝 {site_info}\n\n"
    
    await update.message.reply_text(text)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Kullanim: /toplu mesajiniz")
        return
    
    message = " ".join(context.args)
    data = load_data()
    approved = data["approved"]
    
    if not approved:
        await update.message.reply_text("📭 Onayli kullanici yok.")
        return
    
    sent = 0
    failed = 0
    
    for uid in approved:
        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
            sent += 1
        except Exception as e:
            failed += 1
    
    await update.message.reply_text(f"✅ {sent} kisiye gonderildi.\n❌ {failed} kisiye gonderilemedi.")

def main():
    keep_alive()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("onay", approve))
    application.add_handler(CommandHandler("liste", list_pending))
    application.add_handler(CommandHandler("toplu", broadcast))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot calisiyor...")
    application.run_polling()

if __name__ == "__main__":
    main()
