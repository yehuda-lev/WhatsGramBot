import logging
import mimetypes

from pyrogram import types as tg_types, Client, enums
from pywa_async import types as wa_types, errors
from sqlalchemy.exc import NoResultFound

from data import clients, config, modules, utils
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

    text = (
        utils.get_tg_text_to_wa((msg.text or msg.caption).markdown)
        if msg.text or msg.caption
        else None
    )

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
                    "__Media size is more than 20MB, can't send it to WhatsApp__",
                    quote=True,
                )
                return

            download = await msg.download(in_memory=True)
            media_kwargs = dict(
                **kwargs,
                reply_to_message_id=reply_msg.wa_msg_id if reply_msg else None,
                caption=text,
            )

            match msg.media:
                case enums.MessageMediaType.PHOTO:
                    sent = await wa_bot.send_image(
                        **media_kwargs, image=download, mime_type="image/jpeg"
                    )

                case enums.MessageMediaType.VIDEO:
                    sent = await wa_bot.send_video(
                        **media_kwargs,
                        video=download,
                        mime_type=msg.video.mime_type or "video/mp4",
                    )

                case enums.MessageMediaType.STORY:
                    if msg.story.video:
                        sent = await wa_bot.send_video(
                            **media_kwargs,
                            video=download,
                            mime_type=media.mime_type or "video/mp4",
                        )
                    elif msg.story.photo:
                        sent = await wa_bot.send_image(
                            **media_kwargs, photo=download, mime_type="image/jpeg"
                        )
                    else:
                        await msg.reply("__Unsupported story type__", quote=True)
                        _logger.warning(f"Unsupported story type: {msg.story}")
                        return

                case enums.MessageMediaType.ANIMATION:
                    sent = await wa_bot.send_video(
                        **media_kwargs,
                        video=download,
                        mime_type=media.mime_type or "video/mp4",
                    )

                case enums.MessageMediaType.VIDEO_NOTE:
                    sent = await wa_bot.send_video(
                        **media_kwargs,
                        video=download,
                        mime_type=media.mime_type or "video/mp4",
                    )

                case enums.MessageMediaType.DOCUMENT:
                    sent = await wa_bot.send_document(
                        **media_kwargs,
                        document=download,
                        filename=media.file_name,
                        mime_type=media.mime_type
                        or mimetypes.guess_type(media.file_name)[0]
                        or "application/octet-stream",
                    )

                # with no caption
                case enums.MessageMediaType.AUDIO:
                    sent = await wa_bot.send_audio(
                        **kwargs,
                        audio=download,
                        mime_type=media.mime_type or "audio/mpeg",
                    )
                case enums.MessageMediaType.VOICE:
                    sent = await wa_bot.send_audio(
                        **kwargs,
                        audio=download,
                        mime_type=media.mime_type or "audio/ogg",
                    )
                case enums.MessageMediaType.STICKER:
                    if media.is_animated:
                        await msg.reply(
                            "__Animated stickers are not supported__", quote=True
                        )
                        return

                    sent = await wa_bot.send_sticker(
                        **kwargs,
                        sticker=download,
                        mime_type=media.mime_type or "image/webp",
                    )
                case _:
                    return

        else:
            if msg.text:
                sent = await wa_bot.send_message(
                    **kwargs,
                    text=text,
                    preview_url=msg.link_preview_options.is_disabled
                    if msg.link_preview_options
                    else None,
                    reply_to_message_id=reply_msg.wa_msg_id if reply_msg else None,
                )
            elif msg.location or msg.venue:
                sent = await wa_bot.send_location(
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
                sent = await wa_bot.send_contact(
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
        if e.error_code == 100:
            await msg.reply("__Unsupported media type__", quote=True)
        else:
            _logger.exception(e)
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
            await wa_bot.remove_reaction(
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
            await wa_bot.send_reaction(
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
        case _:
            pass


async def on_command(client: Client, msg: tg_types.Message):
    topic_id = (
        msg.message_thread_id if msg.message_thread_id else msg.reply_to_message_id
    )

    try:
        topic = repositoy.get_topic_by_topic_id(topic_id=topic_id)
    except NoResultFound:
        topic = None

    if msg.text == "/info":
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

    elif msg.text in ["/settings", "/ban", "/unban"]:
        # check if the user is admin in the group
        user = await client.get_chat_member(msg.chat.id, msg.from_user.id)
        if user.status not in (
            enums.ChatMemberStatus.OWNER,
            enums.ChatMemberStatus.ADMINISTRATOR,
        ):
            await msg.reply("You are not admin in the group", quote=True)
            return

        if msg.text == "/settings":
            try:
                db_settings = repositoy.get_settings()
                chat_opened_enable = db_settings.chat_opened_enable
                welcome_msg = db_settings.welcome_msg
            except NoResultFound:
                repositoy.create_settings()
                chat_opened_enable = False
                welcome_msg = False

            await msg.reply(
                text=f"**Settings**\n"
                f"**Chat opened enable:** __{chat_opened_enable}__\n"
                f"> if chat opened is active - the bot will create topic when user open chat. "
                f"else - the bot will create topic only if user send message\n\n"
                f"**Welcome message:** __{welcome_msg}__\n"
                f"> if welcome message is active - the bot will send welcome message when the topic is created\n\n"
                f"__Tap on the button to change the settings__",
                quote=True,
                reply_markup=tg_types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            tg_types.InlineKeyboardButton(
                                text=f"Chat opened: {'❌' if chat_opened_enable else '✅'}",
                                callback_data=f"settings_chat_opened_enable_{'Disable' if chat_opened_enable else 'Enable'}",
                            ),
                        ],
                        [
                            tg_types.InlineKeyboardButton(
                                text=f"Welcome message {'❌' if welcome_msg else '✅'}",
                                callback_data=f"settings_welcome_msg_{'Disable' if welcome_msg else 'Enable'}",
                            ),
                        ],
                        [
                            tg_types.InlineKeyboardButton(
                                text="Change message welcome",
                                callback_data="settings_change_msg_welcome",
                            ),
                        ],
                    ]
                ),
            )

        elif msg.text == "/ban":
            if not topic:
                await msg.reply("No topic found", quote=True)
                return

            if topic.user.banned:
                await msg.reply("User already banned", quote=True)
                return

            repositoy.update_user(wa_id=topic.user.wa_id, banned=True)
            await msg.reply("User banned", quote=True)

        elif msg.text == "/unban":
            if not topic:
                await msg.reply("No topic found", quote=True)
                return

            if not topic.user.banned:
                await msg.reply("User already unbanned", quote=True)
                return

            repositoy.update_user(wa_id=topic.user.wa_id, banned=False)
            await msg.reply("User unbanned", quote=True)


async def on_callback_query(_: Client, cbd: tg_types.CallbackQuery):
    cbd_data = cbd.data

    if cbd_data.startswith("settings"):
        if cbd_data.startswith("settings_chat_opened_enable"):
            chat_opened_enable = cbd_data.split("_")[-1].lower() == "enable"
            repositoy.update_settings(chat_opened_enable=chat_opened_enable)

            # update the chat_opened in the bot on WhatsApp
            await wa_bot.update_conversational_automation(
                enable_chat_opened=chat_opened_enable,
                ice_breakers=None,
                commands=[wa_types.Command("start", "start")],
            )

            await cbd.message.edit_text(
                f"Chat opened is {'enabled' if chat_opened_enable else 'disabled'} now"
            )

        elif cbd_data.startswith("settings_welcome_msg"):
            welcome_msg = cbd_data.split("_")[-1].lower() == "enable"
            repositoy.update_settings(welcome_msg=welcome_msg)
            await cbd.message.edit_text(
                f"Welcome message is {'enabled' if welcome_msg else 'disabled'} now"
            )

        elif cbd_data.startswith("settings_change_msg_welcome"):
            message_to_send = None
            try:
                message_to_send = repositoy.get_message_to_send(
                    type_event=modules.EventType.MSG_WELCOME
                )
            except NoResultFound:
                await cbd.answer("No welcome message found")

            if message_to_send:  # send the message tht exist
                await cbd.message.reply(text="__The current welcome message is:__")
                await cbd.message.reply(text=message_to_send.text)

            await cbd.message.reply(
                text="Send the new welcome message",
                reply_markup=tg_types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            tg_types.InlineKeyboardButton(
                                text="Cancel", callback_data="cancel_listen"
                            )
                        ]
                    ]
                ),
            )
            await cbd.message.edit_text("⚡️")

            # start listening
            utils.add_listener(
                user_id=cbd.from_user.id,
                data={"answer_type": modules.EventType.MSG_WELCOME},
            )

    elif cbd_data == "cancel_listen":
        utils.remove_listener(user_id=cbd.from_user.id)  # remove listener
        await cbd.message.reply("Canceled")


async def on_listen(_: Client, msg: tg_types.Message):
    if not msg.from_user:
        await msg.reply("User not found")
        return
    user_id = msg.from_user.id
    data = utils.get_listener(user_id=user_id)
    utils.remove_listener(user_id=user_id)

    if data.get("answer_type") == modules.EventType.MSG_WELCOME:
        text = msg.text.markdown or msg.caption.markdown

        try:
            repositoy.get_message_to_send(type_event=modules.EventType.MSG_WELCOME)
            repositoy.update_message_to_send(
                type_event=modules.EventType.MSG_WELCOME, text=text
            )
        except NoResultFound:
            repositoy.create_message_to_send(
                type_event=modules.EventType.MSG_WELCOME, text=text
            )

        await msg.reply("Welcome message updated", quote=True)
