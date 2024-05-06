import logging
from pywa import types as wa_types, handlers, WhatsApp, filters, errors
from pyrogram import types as tg_types
from sqlalchemy.exc import NoResultFound

from wa import wa_bot
from db import repositoy
from data import clients, config, modules

_logger = logging.getLogger(__name__)
settings = config.get_settings()

tg_bot = clients.tg_bot


async def create_user(_: WhatsApp, msg: wa_types.Message) -> bool:
    wa_id = msg.sender
    name = msg.from_user.name
    try:
        user = repositoy.get_user_by_wa_id(wa_id=wa_id)
        if not user.active:
            repositoy.update_user(wa_id=wa_id, active=True)
        if user.banned:
            return False
    except NoResultFound:  # user not exists
        # create user and topic
        topic = await tg_bot.create_forum_topic(
            chat_id=settings.tg_group_topic_id,
            name=f"{name} | {wa_id}",
        )
        topic_id = topic.id
        repositoy.create_user_and_topic(
            wa_id=wa_id,
            name=name,
            topic_id=topic_id,
        )

        sent = await tg_bot.send_message(
            chat_id=settings.tg_group_topic_id,
            text=f"User {name} | {wa_id} created topic {topic.id}",
            reply_parameters=tg_types.ReplyParameters(message_id=topic.id),
            reply_markup=tg_types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        tg_types.InlineKeyboardButton(
                            text="WhatsApp", url=f"https://wa.me/{wa_id}"
                        )
                    ],
                ],
            ),
        )
        await sent.pin(disable_notification=True)

    return True


async def on_failed_status(
    _: WhatsApp, status: wa_types.MessageStatus[modules.Tracker]
):
    await tg_bot.send_message(
        chat_id=status.tracker.chat_id,
        text=f"__{status.error.details}__",
        reply_parameters=tg_types.ReplyParameters(message_id=status.tracker.msg_id),
    )
    if isinstance(status.error, errors.ReEngagementMessage):  # 24 hours passed
        repositoy.update_user(wa_id=status.sender, active=False)
    else:
        _logger.error(status.error)


HANDLERS = [
    handlers.MessageHandler(
        wa_bot.get_message,
        create_user,
    ),
    handlers.MessageStatusHandler(
        on_failed_status,
        filters.message_status.failed,
        factory=modules.Tracker,
    ),
]
