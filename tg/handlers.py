import logging
from pyrogram import handlers, filters

from tg import tg_bot

_logger = logging.getLogger(__name__)


HANDLERS = [
    handlers.MessageHandler(
        tg_bot.echo,
        filters.group & filters.reply,
    ),
]
