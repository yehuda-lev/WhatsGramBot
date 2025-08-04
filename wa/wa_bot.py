import asyncio
import io
import logging
import typing
import httpx
from pywa_async import types as wa_types, errors as wa_errors, WhatsApp, filters
from pyrogram import types as tg_types, errors as tg_errors
from sqlalchemy.exc import NoResultFound

from data import clients, config, utils, modules
from db import repositoy

_logger = logging.getLogger(__name__)

tg_bot = clients.tg_bot
settings = config.get_settings()
send_to = settings.tg_group_topic_id


async def _create_user(
    _: WhatsApp, msg: wa_types.Message | wa_types.ChatOpened
) -> bool:
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
        topic_id = await utils.create_topic(tg_bot, wa_id, name, is_new=True)
        repositoy.create_user_and_topic(
            wa_id=wa_id,
            name=name,
            topic_id=topic_id,
        )
    return True


create_user = filters.new(_create_user)


@WhatsApp.on_chat_opened(filters=create_user)
async def get_chat_opened(_: WhatsApp, __: wa_types.ChatOpened):
    pass


@WhatsApp.on_phone_number_change
async def on_phone_number_change(
    wa: WhatsApp,
    event: wa_types.PhoneNumberChange,
):
    topic = repositoy.get_user_by_wa_id(wa_id=event.sender).topic
    new_name = utils.get_topic_name(
        wa_id=event.new_wa_id, name=utils.get_user_name_from_topic_name(topic.name)
    )
    repositoy.update_wa_id(
        old_wa_id=event.old_wa_id,
        new_wa_id=event.new_wa_id,
    )
    repositoy.update_topic(tg_topic_id=topic.topic_id, name=new_name)
    await tg_bot.edit_forum_topic(
        chat_id=settings.tg_group_topic_id,
        topic_id=topic.topic_id,
        name=new_name,
    )
    # TODO edit the first message & button in the topic (pinned message)
    await tg_bot.send_message(
        chat_id=settings.tg_group_topic_id,
        text=f"__User {event.old_wa_id} changed phone number to {event.new_wa_id}__",
        reply_parameters=tg_types.ReplyParameters(message_id=topic.topic_id),
    )
    await wa.send_message(
        to=event.new_wa_id,
        text=f"_Your phone number has been changed to {event.new_wa_id}_",
    )


@WhatsApp.on_message_status(filters=filters.failed, factory=modules.Tracker)
async def on_failed_status(
    _: WhatsApp,
    status: wa_types.MessageStatus,  # TODO [modules.Tracker]
):
    await tg_bot.send_message(
        chat_id=status.tracker.chat_id,
        text=f"__Failed to send to WhatsApp.__\n> **{status.error.message}**\n{('> ' + status.error.details) if status.error.details else ''}",
        reply_parameters=tg_types.ReplyParameters(message_id=status.tracker.msg_id),
    )
    if isinstance(status.error, wa_errors.ReEngagementMessage):  # 24 hours passed
        repositoy.update_user(wa_id=status.sender, active=False)
    else:
        _logger.error(status.error)


@WhatsApp.on_message(filters=filters.command("start") & create_user)
async def on_command_start(_: WhatsApp, msg: wa_types.Message):
    # get text welcome message
    try:
        text_welcome = repositoy.get_message_to_send(
            type_event=modules.EventType.MSG_WELCOME
        )
    except NoResultFound:
        text_welcome = None

    if text_welcome:
        await msg.mark_as_read()
        await msg.reply(text_welcome.text)


@WhatsApp.on_message(filters=~filters.is_command & create_user)
async def get_message(_: WhatsApp, msg: wa_types.Message):
    try:
        repositoy.get_message(wa_msg_id=msg.id, topic_msg_id=None)
        return
    except NoResultFound:
        pass

    wa_id = msg.sender

    text = (
        utils.get_wa_text_to_tg(msg.text or msg.caption)
        if msg.text or msg.caption
        else None
    )
    if msg.forwarded:
        text_forwarded = f"__This message was forwarded {'many times' if msg.forwarded_many_times else ''}__"
        if not text:
            text = text_forwarded
        else:
            text = f"{text}\n\n{text_forwarded}"

    while True:
        user = repositoy.get_user_by_wa_id(wa_id=wa_id)
        topic_id = user.topic.topic_id
        sent = None
        reply_msg = None
        if msg.is_reply:
            try:
                reply_to = (
                    msg.reply_to_message.message_id
                    if not msg.reaction
                    else msg.message_id_to_reply
                )
                reply_msg = repositoy.get_message(wa_msg_id=reply_to, topic_msg_id=None)
            except NoResultFound:
                pass

        kwargs = dict(
            chat_id=send_to,
            reply_parameters=tg_types.ReplyParameters(
                message_id=reply_msg.topic_msg_id if reply_msg else topic_id
            ),
        )

        try:
            if msg.has_media:
                download = io.BytesIO(await msg.download_media(in_memory=True))
                download.name = f"{msg.type}{msg.media.extension or ''}"
                media_kwargs = dict(
                    **kwargs,
                    caption=text,
                )

                match msg.type:
                    case wa_types.MessageType.IMAGE:
                        sent = await tg_bot.send_photo(
                            **media_kwargs,
                            photo=download,
                        )
                    case wa_types.MessageType.VIDEO:
                        sent = await tg_bot.send_video(
                            **media_kwargs,
                            video=download,
                        )
                    case wa_types.MessageType.DOCUMENT:
                        sent = await tg_bot.send_document(
                            **media_kwargs,
                            document=download,
                            file_name=msg.media.filename,
                        )
                    case wa_types.MessageType.AUDIO:
                        if msg.media.voice:
                            sent = await tg_bot.send_voice(
                                **media_kwargs,
                                voice=download,
                            )
                        else:
                            sent = await tg_bot.send_audio(
                                **media_kwargs,
                                audio=download,
                            )
                    case wa_types.MessageType.STICKER:
                        sent = await tg_bot.send_sticker(
                            **media_kwargs,
                            sticker=download,
                        )
                    case _:
                        sent = await tg_bot.send_message(
                            **kwargs,
                            text=f"__User sent an unsupported media type {msg.type}__",
                        )
                        _logger.warning(f"Unsupported media type: {msg.type}")

            else:
                match msg.type:
                    case wa_types.MessageType.TEXT:
                        sent = await tg_bot.send_message(
                            **kwargs,
                            text=text,
                        )

                    case wa_types.MessageType.CONTACTS:
                        for contact in msg.contacts:
                            sent = await tg_bot.send_contact(
                                **kwargs,
                                first_name=contact.name.first_name,
                                last_name=contact.name.last_name,
                                phone_number=(
                                    typing.cast(tuple, contact.phones)[0].phone
                                    or typing.cast(tuple, contact.phones)[0].wa_id
                                ),
                                vcard=contact.as_vcard(),
                            )

                    case wa_types.MessageType.LOCATION:
                        sent = await tg_bot.send_location(
                            **kwargs,
                            latitude=msg.location.latitude,
                            longitude=msg.location.longitude,
                        )

                    case wa_types.MessageType.REACTION:
                        if msg.reaction.is_removed:
                            await tg_bot.set_reaction(
                                chat_id=send_to,
                                message_id=reply_msg.topic_msg_id,
                                reaction=None,
                            )
                        else:
                            if msg.reaction.emoji in EMOJIS:
                                await tg_bot.set_reaction(
                                    chat_id=send_to,
                                    message_id=reply_msg.topic_msg_id,
                                    reaction=[
                                        tg_types.ReactionTypeEmoji(
                                            emoji=msg.reaction.emoji
                                        )
                                    ],
                                )
                            else:
                                await tg_bot.send_message(
                                    **kwargs,
                                    text=f"__The user react with {msg.reaction.emoji}__",
                                )

                    case wa_types.MessageType.UNSUPPORTED:
                        sent = await tg_bot.send_message(
                            **kwargs,
                            text="__User sent unsupported message__",
                        )

                    case _:
                        sent = await tg_bot.send_message(
                            **kwargs,
                            text=f"__User sent unsupported message {msg.type}__",
                        )
                        _logger.warning(f"Unsupported message type: {msg.type}")

        except tg_errors.FloodWait as e:
            await asyncio.sleep(e.value)
            continue

        except tg_errors.ReactionEmpty:
            pass

        except tg_errors.TopicDeleted:
            # create new topic
            _logger.debug("his topic was deleted, creating new topic..")
            try:
                new_topic_id = await utils.create_topic(
                    tg_bot, wa_id, user.name, is_new=False
                )
                repositoy.update_topic(tg_topic_id=topic_id, topic_id=new_topic_id)
            except Exception:  # noqa
                _logger.exception(
                    "Error creating topic: ",
                )
                return
            continue

        except httpx.ReadTimeout:
            _logger.debug("Timeout sending message to telegram")
            sent = await tg_bot.send_message(
                **kwargs,
                text=f"__The user send {msg.type} message but the download failed because timeout set to {settings.httpx_timeout} __",
            )

        except Exception as e:  # noqa
            _logger.exception(
                "Error sending message: ",
            )

        if sent:
            repositoy.create_message(
                wa_id=wa_id,
                topic_id=topic_id,
                wa_msg_id=msg.id,
                topic_msg_id=sent.id,
                sent_from_tg=False,
            )
        break


EMOJIS = [
    "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯",
    "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩", "🙏", "👌",
    "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "❤‍🔥", "🌚", "🌭",
    "💯", "🤣", "⚡", "🍌", "🏆", "💔", "🤨", "😐", "🍓",
    "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻",
    "👀", "🎃", "🙈", "😇", "😨", "🤝", "✍", "🤗", "🫡",
    "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉",
    "🦄", "😘", "💊", "🙊", "😎", "👾", "🤷‍♂", "🤷", "🤷‍♀", "😡"
]  # fmt: off
