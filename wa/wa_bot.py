import asyncio
import functools
import io
import logging
import typing
import httpx
from pywa_async import types as wa_types, errors as wa_errors, WhatsApp
from pyrogram import types as tg_types, errors as tg_errors
from sqlalchemy.exc import NoResultFound

from data import clients, config, utils, modules
from db import repositoy

_logger = logging.getLogger(__name__)

tg_bot = clients.tg_bot
settings = config.get_settings()
send_to = settings.tg_group_topic_id


def check_if_update_in_process(
    func: typing.Callable[[WhatsApp, typing.Any], typing.Awaitable[typing.Any]],
):
    updates_in_process: set[str]() = set()

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        update = args[1]
        if update.id in updates_in_process:
            txt = f"Your function {func.__name__} is too slow, {update.__class__.__name__} (%s) is already in process"
            _logger.warning(txt, update.id)
            _logger.debug(txt, update)
            return
        updates_in_process.add(update.id)
        try:
            return await func(*args, **kwargs)
        finally:
            updates_in_process.remove(update.id)

    return wrapper


@check_if_update_in_process
async def get_chat_opened(_: WhatsApp, __: wa_types.ChatOpened):
    pass


@check_if_update_in_process
async def on_failed_status(
    _: WhatsApp,
    status: wa_types.MessageStatus,  # TODO [modules.Tracker]
):
    await tg_bot.send_message(
        chat_id=status.tracker.chat_id,
        text=f"__Failed to send to WhatsApp.__\n> **{status.error.message}**\n> {status.error.details}",
        reply_parameters=tg_types.ReplyParameters(message_id=status.tracker.msg_id),
    )
    if isinstance(status.error, wa_errors.ReEngagementMessage):  # 24 hours passed
        repositoy.update_user(wa_id=status.sender, active=False)
    else:
        _logger.error(status.error)


@check_if_update_in_process
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


@check_if_update_in_process
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
                download.name = f"{msg.type}{msg.media.extension}"
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
                new_topic_id = await utils.create_topic(tg_bot, wa_id, user.name, is_new=False)
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
