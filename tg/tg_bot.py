import logging
import mimetypes

from pyrogram import types as tg_types, Client, enums
from pywa import types as wa_types, errors
from sqlalchemy.exc import NoResultFound

from data import clients, config, modules
from db import repositoy

_logger = logging.getLogger(__name__)

wa_bot = clients.wa_bot
settings = config.get_settings()


async def on_message(_: Client, msg: tg_types.Message):
    topic_id = (
        msg.message_thread_id if msg.message_thread_id else msg.reply_to_message_id
    )
    try:
        topic = repositoy.get_topic_by_topic_id(topic_id=topic_id)
    except NoResultFound:
        return

    if topic.user.banned:
        return

    reply_msg = None
    if msg.message_thread_id:
        reply_to = msg.reply_to_message_id
        try:
            reply_msg = repositoy.get_message(topic_msg_id=reply_to, wa_msg_id=None)
        except NoResultFound:
            pass

    wa_id = topic.user.wa_id
    sent = None

    kwargs = dict(to=wa_id, tracker=modules.Tracker(chat_id=msg.chat.id, msg_id=msg.id))

    try:
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
                await msg.reply(
                    "Media size is more than 20MB, can't send it to WhatsApp",
                    quote=True,
                )
                return

            download = await msg.download(in_memory=True)
            media_kwargs = dict(
                **kwargs,
                reply_to_message_id=reply_msg.wa_msg_id if reply_msg else None,
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
                        **kwargs,
                        audio=download,
                        mime_type=media.mime_type or "audio/mpeg",
                    )
                case enums.MessageMediaType.VOICE:
                    sent = wa_bot.send_audio(
                        **kwargs,
                        audio=download,
                        mime_type=media.mime_type or "audio/ogg",
                    )
                case enums.MessageMediaType.STICKER:
                    if media.is_animated:
                        await msg.reply(
                            "Animated stickers are not supported", quote=True
                        )
                        return

                    sent = wa_bot.send_sticker(
                        **kwargs,
                        sticker=download,
                        mime_type=media.mime_type or "image/webp",
                    )
                case _:
                    _logger.warning(f"Unsupported media type: {msg.media}")
                    return

        else:
            if msg.text:
                sent = wa_bot.send_message(
                    **kwargs,
                    text=msg.text,
                    reply_to_message_id=reply_msg.wa_msg_id if reply_msg else None,
                )
            elif msg.location or msg.venue:
                sent = wa_bot.send_location(
                    **kwargs,
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
                    **kwargs,
                    reply_to_message_id=reply_msg.wa_msg_id if reply_msg else None,
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
    except errors.WhatsAppError as e:
        _logger.error(e)
        if e.error_code == 100:
            await msg.reply("__Unsupported media type__", quote=True)
        else:
            await msg.reply(f"Error: __{e}__", quote=True)

    if sent:
        repositoy.create_message(
            topic_id=topic_id,
            topic_msg_id=msg.id,
            wa_msg_id=sent,
            wa_id=wa_id,
        )


async def on_reaction(_: Client, reaction: tg_types.MessageReactionUpdated):
    if not reaction.new_reaction:
        try:
            msg = repositoy.get_message(
                topic_msg_id=reaction.message_id, wa_msg_id=None
            )
            wa_bot.remove_reaction(
                to=msg.user.wa_id,
                message_id=msg.wa_msg_id,
                tracker=modules.Tracker(
                    chat_id=reaction.chat.id, msg_id=reaction.message_id
                ),
            )
        except NoResultFound:
            return
    else:
        if not reaction.new_reaction[-1].emoji:
            return

        try:
            msg = repositoy.get_message(
                topic_msg_id=reaction.message_id, wa_msg_id=None
            )
            wa_bot.send_reaction(
                to=msg.user.wa_id,
                message_id=msg.wa_msg_id,
                emoji=reaction.new_reaction[-1].emoji,
                tracker=modules.Tracker(
                    chat_id=reaction.chat.id, msg_id=reaction.message_id
                ),
            )
        except NoResultFound:
            return


async def on_message_service(_: Client, msg: tg_types.Message):
    topic_id = (
        msg.message_thread_id if msg.message_thread_id else msg.reply_to_message_id
    )

    try:
        topic = repositoy.get_topic_by_topic_id(topic_id=topic_id)
    except NoResultFound:
        return

    match msg.service:
        case enums.MessageServiceType.FORUM_TOPIC_CLOSED:
            if not topic.user.banned:
                repositoy.update_user(wa_id=topic.user.wa_id, banned=True)
                await msg.reply("User banned", quote=True)

        case enums.MessageServiceType.FORUM_TOPIC_REOPENED:
            if topic.user.banned:
                repositoy.update_user(wa_id=topic.user.wa_id, banned=False)
                await msg.reply("User unbanned", quote=True)


async def on_command(_: Client, msg: tg_types.Message):
    if not msg.text:
        return

    topic_id = (
        msg.message_thread_id if msg.message_thread_id else msg.reply_to_message_id
    )

    try:
        topic = repositoy.get_topic_by_topic_id(topic_id=topic_id)
    except NoResultFound:
        topic = None

    if msg.text.startswith("/info"):
        if topic is None:
            await msg.reply("No topic found", quote=True)
            return

        await msg.reply(
            text=f"**Name:** __{topic.user.name}__\n"
            f"**WhatsApp ID:** `{topic.user.wa_id}`\n"
            f"**Topic ID:** `{topic.topic_id}`\n"
            f"**Banned:** __{topic.user.banned}__\n"
            f"**Active:** __{topic.user.active}__\n"
            f"**Created:** __{topic.created_at}__\n",
            quote=True,
            reply_markup=tg_types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        tg_types.InlineKeyboardButton(
                            text="WhatsApp", url=f"https://wa.me/{topic.user.wa_id}"
                        ),
                        tg_types.InlineKeyboardButton(
                            text="Topic",
                            url=f"https://t.me/c/{str(settings.tg_group_topic_id).replace('-100', '')}"
                            f"/{topic.topic_id}",
                        ),
                    ]
                ]
            ),
        )
