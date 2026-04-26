import asyncio
import logging

import httpx
import uvicorn
from fastapi import FastAPI
from pyrogram import __version__ as tg_version, raw, Client
from pywa_async import __version__ as wa_version, WhatsApp

from data import config, clients
from wa import wa_bot as wa_bot_handlers_module
from tg import handlers as tg_handlers


# log config
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
file_handler = RotatingFileHandler(
    filename="bot.log", maxBytes=5 * (2**20), backupCount=1, mode="D", encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
    handlers=(console_handler, file_handler),
)
logging.getLogger().setLevel(logging.NOTSET)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pywa").setLevel(logging.INFO)

_logger = logging.getLogger(__name__)

settings = config.get_settings()


logging.info(
    f"The bot is up and running on Pyrogram v{tg_version} (Layer {raw.all.layer}), PyWa v{wa_version}"
)

async def start_telegram_bot(bot: Client):
    for tg_handler in tg_handlers.HANDLERS:
        bot.add_handler(tg_handler)

    await bot.start()

async def main():

    clients.tg_bot = Client(
        name="whtsgram_bot",
        api_id=settings.tg_api_id,
        api_hash=settings.tg_api_hash,
        bot_token=settings.tg_bot_token,
    )

    # whatsapp
    app = FastAPI()

    httpx_session = httpx.AsyncClient(timeout=httpx.Timeout(timeout=settings.httpx_timeout))
    clients.wa_bot = WhatsApp(
        phone_id=settings.wa_phone_id,
        token=settings.wa_token,
        server=app,
        verify_token=settings.wa_verify_token,
        # callback_url=settings.wa_callback_url,
        webhook_endpoint=settings.wa_webhook_endpoint,
        app_id=settings.wa_app_id,
        app_secret=settings.wa_app_secret,
        webhook_challenge_delay=10,
        session=httpx_session,
        handlers_modules=[wa_bot_handlers_module],
        filter_updates=False,
    )


    await start_telegram_bot(clients.tg_bot)

    uvicorn_config = uvicorn.Config(
        app=app,
        port=settings.port,
        host="0.0.0.0",
        access_log=False,
        log_level=False,
        log_config=None,
    )
    server = uvicorn.Server(uvicorn_config)

    try:
        await server.serve()
    except asyncio.CancelledError:
        pass
    finally:
        await clients.tg_bot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
