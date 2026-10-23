import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
BITRIX_WEBHOOK = os.environ.get("BITRIX_WEBHOOK")

flask_app = Flask(__name__)
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Хочу узнать подробнее о программе и условиях обучения Психология Эннеаграммы", callback_data="want_details")]]
    await update.message.reply_text("Здравствуйте! Нажмите кнопку ниже, чтобы узнать подробнее.", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "want_details":
        await query.edit_message_text("Спасибо, первый свободный менеджер с вами свяжется.. А пока напишите свой телефон, обещаем не спамить.")

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "/start": return
    
    user = update.effective_user
    full_name = user.full_name or "Не указано"
    
    # Отправка в Битрикс
    payload = {
        "fields": {
            "TITLE": "Заявка ТГ бота",
            "NAME": full_name,
            "SOURCE_ID": "TELEGRAM",
            "COMMENTS": f"Контакт: {text}",
            "PHONE": [{"VALUE": text, "VALUE_TYPE": "WORK"}]
        }
    }
    try:
        requests.post(BITRIX_WEBHOOK + "crm.lead.add.json", json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Ошибка Битрикса: {e}")
        
    await update.message.reply_text("Спасибо! Заявка принята, менеджер скоро свяжется с вами.")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, contact_handler))

@flask_app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    import asyncio
    asyncio.run(telegram_app.process_update(update))
    return "ok", 200

@flask_app.route("/", methods=["GET"])
def health(): return "Bot is running", 200

def main():
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={os.environ['RENDER_EXTERNAL_URL']}/webhook/{TELEGRAM_TOKEN}")
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()