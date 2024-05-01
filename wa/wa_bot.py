import logging
from pywa import WhatsApp, types

from data import clients, config


_logger = logging.getLogger(__name__)

tg_bot = clients.tg_bot
settings = config.get_settings()
send_to = settings.tg_id_test


def echo(_: WhatsApp, msg: types.Message):
    tg_bot.send_message(
        chat_id=send_to,
        text=msg.text,
    )
