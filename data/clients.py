import logging
import httpx
from pyrogram import Client
from pywa_async import WhatsApp
from fastapi import FastAPI

from data import config


_logger = logging.getLogger(__name__)

settings = config.get_settings()


# telegram
tg_bot: Client = None
wa_bot: WhatsApp = None
