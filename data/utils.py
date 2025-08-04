import re

from pyrogram import types as tg_types, Client

from data import config

settings = config.get_settings()


def get_tg_text_to_wa(text: str) -> str:
    """Convert Telegram text formatting to WhatsApp text formatting.
    Args:
        text (str): The text to convert.
        Returns:
        str: The converted text.
    """
    # Define regular expressions for Telegram formatting
    telegram_bold = re.compile(r"\*\*(.*?)\*\*")
    telegram_italic = re.compile(r"__(.*?)__")
    telegram_underline = re.compile(r"--(.*?)--")
    telegram_strike = re.compile(r"~~(.*?)~~")
    telegram_blockquote = re.compile(r">(.*?)")
    telegram_inline_code = re.compile(r"`(.*?)`")
    telegram_code_block = re.compile(r"```(.*?)```")
    telegram_spoiler = re.compile(r"\|\|(.*?)\|\|")
    telegram_mention = re.compile(r"\[([^\]]+)\]\(tg://user\?id=(\d+)\)")
    telegram_url = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    # Replace Telegram formatting with WhatsApp formatting
    text = re.sub(telegram_bold, r"*\1*", text)
    text = re.sub(telegram_italic, r"_\1_", text)
    text = re.sub(telegram_underline, r"_\1_", text)
    text = re.sub(telegram_strike, r"~\1~", text)
    text = re.sub(telegram_blockquote, r">\1", text)
    text = re.sub(telegram_inline_code, r"`\1`", text)
    text = re.sub(telegram_code_block, r"```\1```", text)
    text = re.sub(telegram_spoiler, r"~\1~", text)
    text = re.sub(telegram_mention, r"\1: @\2", text)
    text = re.sub(telegram_url, r"\1: \2", text)

    return text


def get_topic_name(wa_id: str, name: str) -> str:
    return f"{name} | {wa_id}"


def get_user_name_from_topic_name(topic_name: str) -> str:
    parts = topic_name.split(" | ")
    if len(parts) < 2:
        return topic_name
    return " | ".join(parts[:-1])


def get_wa_text_to_tg(text: str) -> str:
    """Convert WhatsApp text formatting to Telegram text formatting.
    Args:
        text (str): The text to convert.
        Returns:
        str: The converted text.
    """
    # Define regular expressions for WhatsApp formatting
    whatsapp_bold = re.compile(r"\*([^*]+)\*")
    whatsapp_italic = re.compile(r"_([^_]+)_")
    whatsapp_strikethrough = re.compile(r"~([^~]+)~")

    # Replace WhatsApp formatting with Telegram formatting
    text = re.sub(whatsapp_bold, r"**\1**", text)
    text = re.sub(whatsapp_italic, r"__\1__", text)
    text = re.sub(whatsapp_strikethrough, r"~~\1~~", text)

    return text


async def create_topic(tg_bot: Client, wa_id: str, name: str, is_new: bool) -> int:
    topic = await tg_bot.create_forum_topic(
        chat_id=settings.tg_group_topic_id,
        name=get_topic_name(wa_id, name),
    )

    sent = await tg_bot.send_message(
        chat_id=settings.tg_group_topic_id,
        text=f"User {name} | {wa_id} {'' if is_new else 're-'}created topic {topic.id}",
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

    return topic.id


# listener


user_id_to_state: dict[str | int : dict] = {}
"""example: {user_id: {answer_type: modules.EventType.MSG_WELCOME}}"""


def is_answer(**kwargs):
    """example: is_answer(answer_type=modules.EventType.MSG_WELCOME)"""

    def get_answer(_, __, msg) -> bool:
        user_id = msg.from_user.id
        exists = user_id_to_state.get(user_id)
        if exists:
            return all(exists.get(key, False) == value for key, value in kwargs.items())
        return False

    return get_answer


def add_listener(*, user_id: str | int, data: dict):
    """example: {9721234567: {answer_type: modules.EventType.MSG_WELCOME}}"""
    user_id_to_state.update({user_id: data})


def remove_listener(*, user_id: str | int):
    try:
        del user_id_to_state[user_id]
    except KeyError:
        pass


def get_listener(user_id: str | int) -> dict:
    return user_id_to_state[user_id]
