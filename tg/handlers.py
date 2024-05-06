import logging
from pyrogram import handlers, filters

from tg import tg_bot

_logger = logging.getLogger(__name__)

HANDLERS = [
    handlers.MessageHandler(
        tg_bot.on_message,
        filters.group
        & filters.create(lambda _, __, msg: msg.is_topic_message)
        & ~filters.service
        & ~filters.regex(r"^/")
        & filters.chat(tg_bot.settings.tg_group_topic_id),
    ),
    handlers.MessageHandler(
        tg_bot.on_message_service,
        filters.group
        & filters.create(lambda _, __, msg: msg.is_topic_message)
        & filters.service
        & filters.chat(tg_bot.settings.tg_group_topic_id),
    ),
    handlers.MessageHandler(
        tg_bot.on_command,
        filters.group
        & filters.regex(r"^/")
        & filters.chat(tg_bot.settings.tg_group_topic_id),
    ),
    handlers.MessageReactionUpdatedHandler(
        tg_bot.on_reaction,
        filters.group,
        # & filters.chat(tg_bot.settings.tg_group_topic_id),
    ),
]
