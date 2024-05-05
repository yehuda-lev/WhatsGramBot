import logging
import mimetypes

from pyrogram import types as tg_types, Client, enums
from pywa import types as wa_types
from sqlalchemy.exc import NoResultFound

from data import clients, config
from db import repositoy

_logger = logging.getLogger(__name__)

wa_bot = clients.wa_bot
settings = config.get_settings()


def echo(_: Client, msg: tg_types.Message):
    topic_id = (
        msg.message_thread_id if msg.message_thread_id else msg.reply_to_message_id
    )
    try:
        topic = repositoy.get_topic_by_topic_id(topic_id=topic_id)
    except NoResultFound:
        return

    if topic.user.banned:
        return

    wa_id = topic.user.wa_id
    sent = None

    if msg.media in (
        enums.MessageMediaType.PHOTO,
        enums.MessageMediaType.VIDEO,
        enums.MessageMediaType.ANIMATION,
        enums.MessageMediaType.VIDEO_NOTE,
        enums.MessageMediaType.DOCUMENT,
        enums.MessageMediaType.AUDIO,
        enums.MessageMediaType.VOICE,
        enums.MessageMediaType.STICKER,
        enums.MessageMediaType.STORY,
    ):
        # check if media is more than 20MB
        media = getattr(msg, msg.media.name.lower())
        if (media.file_size or 0) > (20 * 1024 * 1024):
            msg.reply(
                "Media size is more than 20MB, can't send it to WhatsApp", quote=True
            )
            return

        download = msg.download(in_memory=True)
        media_kwargs = dict(
            to=wa_id,
            caption=msg.caption,
        )

        match msg.media:
            case enums.MessageMediaType.PHOTO:
                sent = wa_bot.send_image(
                    **media_kwargs, image=download, mime_type="image/jpeg"
                )

            case enums.MessageMediaType.VIDEO:
                sent = wa_bot.send_video(
                    **media_kwargs,
                    video=download,
                    mime_type=msg.video.mime_type or "video/mp4",
                )

            case enums.MessageMediaType.STORY:
                if msg.story.video:
                    sent = wa_bot.send_video(
                        **media_kwargs,
                        video=download,
                        mime_type=media.mime_type or "video/mp4",
                    )
                elif msg.story.photo:
                    sent = wa_bot.send_image(
                        **media_kwargs, photo=download, mime_type="image/jpeg"
                    )
                else:
                    _logger.warning(f"Unsupported story type: {msg.story}")
                    return

            case enums.MessageMediaType.ANIMATION:
                sent = wa_bot.send_video(
                    **media_kwargs,
                    video=download,
                    mime_type=media.mime_type or "video/mp4",
                )

            case enums.MessageMediaType.VIDEO_NOTE:
                sent = wa_bot.send_video(
                    **media_kwargs,
                    video=download,
                    mime_type=media.mime_type or "video/mp4",
                )

            case enums.MessageMediaType.DOCUMENT:
                sent = wa_bot.send_document(
                    **media_kwargs,
                    document=download,
                    filename=media.file_name,
                    mime_type=media.mime_type
                    or mimetypes.guess_type(media.file_name)[0]
                    or "application/octet-stream",
                )

            # with no caption
            case enums.MessageMediaType.AUDIO:
                sent = wa_bot.send_audio(
                    to=wa_id,
                    audio=download,
                    mime_type=media.mime_type or "audio/mpeg",
                )
            case enums.MessageMediaType.VOICE:
                sent = wa_bot.send_audio(
                    to=wa_id,
                    audio=download,
                    mime_type=media.mime_type or "audio/ogg",
                )
            case enums.MessageMediaType.STICKER:
                if media.is_animated:
                    msg.reply("Animated stickers are not supported", quote=True)
                    return

                sent = wa_bot.send_sticker(
                    to=wa_id,
                    sticker=download,
                    mime_type=media.mime_type or "image/webp",
                )
            case _:
                _logger.warning(f"Unsupported media type: {msg.media}")
                return

    else:
        if msg.text:
            sent = wa_bot.send_message(
                to=wa_id,
                text=msg.text,
            )
        elif msg.location or msg.venue:
            sent = wa_bot.send_location(
                to=wa_id,
                latitude=msg.location.latitude
                if msg.location
                else msg.venue.location.latitude,
                longitude=msg.location.longitude
                if msg.location
                else msg.venue.location.longitude,
                name=msg.venue.title if msg.venue else None,
                address=msg.venue.address if msg.venue else None,
            )
        elif msg.contact:
            _logger.exception(msg.contact.phone_number)
            sent = wa_bot.send_contact(
                to=wa_id,
                contact=wa_types.Contact(
                    name=wa_types.Contact.Name(
                        formatted_name=msg.contact.first_name
                        + (
                            (" " + msg.contact.last_name)
                            if msg.contact.last_name
                            else ""
                        ),
                        first_name=msg.contact.first_name,
                        last_name=msg.contact.last_name,
                    ),
                    phones=[
                        wa_types.Contact.Phone(
                            phone=msg.contact.phone_number,
                            wa_id=msg.contact.phone_number.replace("+", ""),
                        )
                    ],
                ),
            )

    if sent:
        repositoy.create_message(
            topic_id=topic_id,
            topic_msg_id=msg.id,
            wa_msg_id=sent,
            wa_id=wa_id,
        )
