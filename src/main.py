import logging
import json
import os
import asyncio
from logging.handlers import RotatingFileHandler
from store import Store
from typing import Optional, Tuple
from datetime import timedelta
from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, MaybeInaccessibleMessage, Message, ShippingOption, Update, User
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    ShippingQueryHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)

#dataPath = os.path.join(os.path.dirname(__file__), "data")
#sitePath = os.path.join(os.path.dirname(__file__), "site")

dataPath = "/data"
sitePath = "/site"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
        handlers=[
        RotatingFileHandler(os.path.join(dataPath, "log", "log.txt"), maxBytes=10 * 1024 * 1024, backupCount=10),
        logging.StreamHandler()
    ]
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("main")

def to_local_time(time):
    dt_local = time + timedelta(hours=3)
    return dt_local.strftime("%Y-%m-%d %H:%M:%S")

def is_admin(user: User) -> bool:
    return user.id == config["admin_id"]

async def get_user_message(update: Update) -> Tuple[Optional[User], Optional[Message | MaybeInaccessibleMessage]]:
    if update.message:
        user = update.message.from_user
        message = update.message
    elif update.callback_query:
        user = update.callback_query.from_user
        message = update.callback_query.message
        await update.callback_query.answer()
    else:
        return None, None

    return user, message

async def get_user_message_query(update: Update) -> Tuple[Optional[CallbackQuery], Optional[User], Optional[Message | MaybeInaccessibleMessage]]:
    query = update.callback_query
    user = update.callback_query.from_user
    message = update.callback_query.message
    await update.callback_query.answer()
    return query, user, message

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = await get_user_message(update)
    logger.info("Start callback for (id {}, username {}, name {})".format(user.id, user.username, user.full_name))

    if not is_admin(user):
        return

    msg = f"Last update: {to_local_time(store.last_update)}\n"
    msg += f"Next update: {to_local_time(store.next_update)}\n"

    await message.reply_text(msg, parse_mode='Markdown')

async def update_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = await get_user_message(update)
    logger.info("Update callback for (id {}, username {}, name {})".format(user.id, user.username, user.full_name))

    if not is_admin(user):
        return

    msg = await message.reply_text("Updating...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, store.manual_update)
    await msg.edit_text("Update finished.")

async def reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = await get_user_message(update)
    logger.info("Reset callback for (id {}, username {}, name {})".format(user.id, user.username, user.full_name))

    if not is_admin(user):
        return

    msg = await message.reply_text("Updating...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, store.hard_reset_update)
    await msg.edit_text("Update finished.")

def main() -> None:
    application = Application.builder().token(config["token"]).build()
    application.add_handler(CommandHandler("start", start_callback))
    application.add_handler(CommandHandler("update", update_callback))
    application.add_handler(CommandHandler("reset", reset_callback))
    store.start()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    with open(os.path.join(dataPath, "config.json"), 'r') as config_file:
        config = json.load(config_file)

    store = Store(config["server"], sitePath)
    main()