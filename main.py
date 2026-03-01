import os
import json
import asyncio
import gspread
from google.oauth2.service_account import Credentials

from telegram import Update
from telegram.error import TimedOut, NetworkError, RetryAfter
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest


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

    parts = []
    for row in rows:
        if row and str(row[0]).strip():
            parts.append(str(row[0]).strip())

    return "\n\n".join(parts).strip()


def chunk_text(text: str, limit: int = 3800):
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    blocks = text.split("\n\n")
    chunks = []
    current = ""
    for b in blocks:
        candidate = (current + "\n\n" + b).strip() if current else b
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(b) > limit:
                for i in range(0, len(b), limit):
                    chunks.append(b[i:i + limit])
                current = ""
            else:
                current = b
    if current:
        chunks.append(current)
    return chunks


async def safe_send(bot, chat_id, text):
    try:
        return await bot.send_message(chat_id=chat_id, text=text)
    except RetryAfter as e:
        await asyncio.sleep(int(e.retry_after) + 1)
        return await bot.send_message(chat_id=chat_id, text=text)
    except (TimedOut, NetworkError):
        await asyncio.sleep(2)
        return await bot.send_message(chat_id=chat_id, text=text)


async def update_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel = os.environ["CHANNEL_USERNAME"]

    text = get_price_text()
    if not text:
        await update.message.reply_text("В листе TG в колонке B (с B2) пусто. Нечего отправлять.")
        return

    chunks = chunk_text(text)
    for ch in chunks:
        await safe_send(context.bot, channel, ch)

    await update.message.reply_text(f"Готово ✅ Отправил сообщений: {len(chunks)}")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает ✅")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if isinstance(err, (TimedOut, NetworkError)):
        return
    print("ERROR:", repr(err))


def main():
    request = HTTPXRequest(connect_timeout=30, read_timeout=60, write_timeout=60, pool_timeout=60)
    app = Application.builder().token(os.environ["BOT_TOKEN"]).request(request).build()

    app.add_handler(CommandHandler("update", update_price))
    app.add_handler(CommandHandler("ping", ping))
    app.add_error_handler(error_handler)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
