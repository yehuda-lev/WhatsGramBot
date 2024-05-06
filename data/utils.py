import re


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
