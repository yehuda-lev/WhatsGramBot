import logging
from pywa_async import types as wa_types, handlers, WhatsApp, filters, errors
from pyrogram import types as tg_types
from sqlalchemy.exc import NoResultFound

from wa import wa_bot
from db import repositoy
from data import clients, config, modules

_logger = logging.getLogger(__name__)
settings = config.get_settings()

tg_bot = clients.tg_bot


async def create_user(_: WhatsApp, msg: wa_types.Message | wa_types.ChatOpened) -> bool:
    wa_id = msg.sender
    name = msg.from_user.name

    try:  # try to get user and update status
        user = repositoy.get_user_by_wa_id(wa_id=wa_id)
        if not user.active:
            repositoy.update_user(wa_id=wa_id, active=True)
        if user.banned:
            return False
    except NoResultFound:  # if user not exists than create user
        try:  # get if wa_chat_opened_enable and if wa_welcome_msg
            db_settings = repositoy.get_settings()
            chat_opened_enable = db_settings.wa_chat_opened_enable
            welcome_msg = db_settings.wa_welcome_msg
        except NoResultFound:
            repositoy.create_settings()
            chat_opened_enable = False
            welcome_msg = False

        # get text welcome message
        text_welcome = None
        if welcome_msg:
            try:
                text_welcome = repositoy.get_message_to_send(
                    type_event=modules.EventType.MSG_WELCOME
                )
            except NoResultFound:
                pass

        if isinstance(msg, wa_types.ChatOpened) and not chat_opened_enable:
            return False

        if welcome_msg and text_welcome:
            if not (
                isinstance(msg, wa_types.Message) and not msg.text.startswith("/start")
            ):
                await msg.reply(text_welcome.text)

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


HANDLERS = [
    handlers.ChatOpenedHandler(
        wa_bot.get_chat_opened,
        create_user,
    ),
    handlers.MessageHandler(
        wa_bot.on_command_start,
        filters.text.command("start"),
        create_user,
    ),
    handlers.MessageHandler(
        wa_bot.get_message,
        filters.not_(filters.text.is_command),
        create_user,
    ),
    handlers.MessageStatusHandler(
        wa_bot.on_failed_status,
        filters.message_status.failed,
        factory=modules.Tracker,
    ),
]
