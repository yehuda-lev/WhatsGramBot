import io
import logging
import typing

from pywa import types as wa_types, WhatsApp
from pyrogram import types as tg_types, errors
from sqlalchemy.exc import NoResultFound

from data import clients, config
from db import repositoy

_logger = logging.getLogger(__name__)

tg_bot = clients.tg_bot
settings = config.get_settings()
send_to = settings.tg_group_topic_id


def echo(_: WhatsApp, msg: wa_types.Message):
    _logger.exception("Message_id: %s", msg.id)
    wa_id = msg.sender
    user = repositoy.get_user_by_wa_id(wa_id=wa_id)
    topic_id = user.topic.topic_id
    send = None
    reply_msg = None
    if msg.is_reply:
        try:
            reply_to = msg.message_id_to_reply
            reply_msg = repositoy.get_message(wa_msg_id=reply_to, topic_msg_id=None)
        except NoResultFound:
            pass

    try:
        if msg.has_media:
            download = io.BytesIO(msg.download_media(in_memory=True))
            download.name = f"{msg.type}{msg.media.extension}"
            media_kwargs = dict(
                chat_id=send_to,
                caption=msg.text,
                reply_parameters=tg_types.ReplyParameters(
                    message_id=reply_msg.topic_msg_id if reply_msg else topic_id
                ),
            )
            match msg.type:
                case wa_types.MessageType.IMAGE:
                    send = tg_bot.send_photo(
                        **media_kwargs,
                        photo=download,
                    )
                case wa_types.MessageType.VIDEO:
                    send = tg_bot.send_video(
                        **media_kwargs,
                        video=download,
                    )
                case wa_types.MessageType.DOCUMENT:
                    send = tg_bot.send_document(
                        **media_kwargs,
                        document=download,
                    )
                case wa_types.MessageType.AUDIO:
                    if msg.media.voice:
                        send = tg_bot.send_voice(
                            **media_kwargs,
                            voice=download,
                        )
                    else:
                        send = tg_bot.send_audio(
                            **media_kwargs,
                            audio=download,
                        )
                case wa_types.MessageType.STICKER:
                    send = tg_bot.send_sticker(
                        **media_kwargs,
                        sticker=download,
                    )
                case _:
                    _logger.warning(f"Unsupported media type: {msg.type}")
                    return
        else:
            kwargs = dict(
                chat_id=send_to,
                reply_parameters=tg_types.ReplyParameters(
                    message_id=reply_msg.topic_msg_id if reply_msg else topic_id
                ),
            )
            match msg.type:
                case wa_types.MessageType.TEXT:
                    send = tg_bot.send_message(
                        **kwargs,
                        text=msg.text,
                    )

                case wa_types.MessageType.CONTACTS:
                    for contact in msg.contacts:
                        send = tg_bot.send_contact(
                            **kwargs,
                            first_name=contact.name.first_name,
                            last_name=contact.name.last_name,
                            phone_number=typing.cast(tuple, contact.phones)[0].phone,
                            vcard=contact.as_vcard(),
                        )

                case wa_types.MessageType.LOCATION:
                    send = tg_bot.send_location(
                        **kwargs,
                        latitude=msg.location.latitude,
                        longitude=msg.location.longitude,
                    )

                case wa_types.MessageType.REACTION:
                    if msg.reaction.is_removed:
                        tg_bot.set_reaction(
                            chat_id=send_to,
                            message_id=reply_msg.topic_msg_id,
                            reaction=None,
                        )
                    else:
                        if msg.reaction.emoji in EMOJIS:
                            tg_bot.set_reaction(
                                chat_id=send_to,
                                message_id=reply_msg.topic_msg_id,
                                reaction=[
                                    tg_types.ReactionTypeEmoji(emoji=msg.reaction.emoji)
                                ],
                            )
                        else:
                            tg_bot.send_message(
                                **kwargs,
                                text=f"the user react {msg.reaction.emoji}",
                            )

                case _:
                    _logger.warning(f"Unsupported message type: {msg.type}")
                    return

    except errors.BadRequest as e:
        # TODO errors.exceptions.bad_request_400.ReactionEmpty
        _logger.error(e)

    if send:
        repositoy.create_message(
            wa_id=wa_id, topic_id=topic_id, wa_msg_id=msg.id, topic_msg_id=send.id
        )


EMOJIS = [
    "👍", "👎", "❤", "🔥",
    "🥰", "👏", "😁", "🤔",
    "🤯", "😱", "🤬", "😢",
    "🎉", "🤩", "🤮", "💩",
    "🙏", "👌", "🕊", "🤡",
    "🥱", "🥴", "😍", "🐳",
    "❤‍🔥", "🌚", "🌭", "💯",
    "🤣", "⚡", "🍌", "🏆",
    "💔", "🤨", "😐", "🍓",
    "🍾", "💋", "🖕", "😈",
    "😴", "😭", "🤓", "👻",
    "👨‍💻", "👀", "🎃", "🙈",
    "😇", "😨", "🤝", "✍",
    "🤗", "🫡", "🎅", "🎄",
    "☃", "💅", "🤪", "🗿",
    "🆒", "💘", "🙉", "🦄",
    "😘", "💊", "🙊", "😎",
    "👾", "🤷‍♂", "🤷", "🤷‍♀",
    "😡"
]
