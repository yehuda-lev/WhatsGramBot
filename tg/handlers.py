import logging
from pyrogram import handlers, filters

from tg import tg_bot

_logger = logging.getLogger(__name__)

HANDLERS = [
    handlers.MessageHandler(
        tg_bot.echo,
        filters.group & filters.reply & filters.chat(tg_bot.settings.tg_group_topic_id),
    ),
    handlers.MessageReactionUpdatedHandler(
        tg_bot.on_reaction,
        filters.group,
        # & filters.chat(tg_bot.settings.tg_group_topic_id),
    ),
]
