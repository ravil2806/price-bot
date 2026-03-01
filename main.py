import os
import json
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

def get_gs_client():
    creds_dict = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_price_text():
    sheet_id = os.environ["SHEET_ID"]
    gc = get_gs_client()
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet("TG")
    rows = ws.get("B2:B200")

    lines = []
    for row in rows:
        if row and row[0].strip():
            lines.append(row[0])

    return "\n\n".join(lines)

async def update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = get_price_text()
    channel = os.environ["CHANNEL_USERNAME"]
    await context.bot.send_message(chat_id=channel, text=text)
    await update.message.reply_text("Прайс отправлен в канал ✅")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает ✅")

def main():
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("update", update_price))
    app.add_handler(CommandHandler("ping", ping))
    app.run_polling()

if __name__ == "__main__":
    main()
