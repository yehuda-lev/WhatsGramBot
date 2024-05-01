import logging
from pyrogram import Client, types

from data import clients, config


_logger = logging.getLogger(__name__)

wa_bot = clients.wa_bot
settings = config.get_settings()
send_to = settings.wa_phone_test


def echo(_: Client, msg: types.Message):
    wa_bot.send_message(
        to=send_to,
        text=msg.text,
    )
