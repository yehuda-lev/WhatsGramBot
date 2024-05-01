import logging
from pyrogram import Client
from pywa import WhatsApp
from fastapi import FastAPI

from data import config


_logger = logging.getLogger(__name__)

settings = config.get_settings()


# telegram
tg_bot = Client(
    name="whtsgram_bot",
    api_id=settings.tg_api_id,
    api_hash=settings.tg_api_hash,
    bot_token=settings.tg_bot_token,
)

# whatsapp
app = FastAPI()

wa_bot = WhatsApp(
    phone_id=settings.wa_phone_id,
    token=settings.wa_token,
    server=app,
    verify_token=settings.wa_verify_token,
    callback_url=settings.callback_url,
    webhook_endpoint=settings.webhook_endpoint,
    app_id=settings.app_id,
    app_secret=settings.app_secret,
    verify_timeout=10,
)
