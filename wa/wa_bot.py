import asyncio
import io
import logging
import typing
from pywa_async import types as wa_types, WhatsApp
from pyrogram import types as tg_types, errors
from sqlalchemy.exc import NoResultFound

from data import clients, config, utils, modules
from db import repositoy

_logger = logging.getLogger(__name__)

tg_bot = clients.tg_bot
settings = config.get_settings()
send_to = settings.tg_group_topic_id


async def get_chat_opened(_: WhatsApp, __: wa_types.ChatOpened):
    pass


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


async def get_message(_: WhatsApp, msg: wa_types.Message):
    wa_id = msg.sender
    user = repositoy.get_user_by_wa_id(wa_id=wa_id)
    topic_id = user.topic.topic_id
    sent = None
    reply_msg = None
    if msg.is_reply:
        try:
            reply_to = msg.reply_to_message.message_id
            reply_msg = repositoy.get_message(wa_msg_id=reply_to, topic_msg_id=None)
        except NoResultFound:
            pass

    kwargs = dict(
        chat_id=send_to,
        reply_parameters=tg_types.ReplyParameters(
            message_id=reply_msg.topic_msg_id if reply_msg else topic_id
        ),
    )

    text = (
        utils.get_wa_text_to_tg(msg.text or msg.caption)
        if msg.text or msg.caption
        else None
    )

    while True:
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
                        _logger.warning(f"Unsupported media type: {msg.type}")
                        return

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
                                phone_number=typing.cast(tuple, contact.phones)[
                                    0
                                ].phone,
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
                                    text=f"the user react {msg.reaction.emoji}",
                                )

                    case _:
                        _logger.warning(f"Unsupported message type: {msg.type}")
                        return

        except errors.FloodWait as e:
            await asyncio.sleep(e.value)
            continue

        except errors.ReactionEmpty:
            pass

        except Exception as e:
            _logger.exception(e)

        if sent:
            repositoy.create_message(
                wa_id=wa_id, topic_id=topic_id, wa_msg_id=msg.id, topic_msg_id=sent.id
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
