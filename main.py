import logging
from logging.handlers import RotatingFileHandler
import uvicorn
from pyrogram import __version__ as tg_version, idle, raw, types as tg_types
from pywa_async import __version__ as wa_version

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

# handlers
tg_bot = clients.tg_bot
wa_bot = clients.wa_bot

for tg_handler in tg_handlers.HANDLERS:
    tg_bot.add_handler(tg_handler)

wa_bot.load_handlers_modules(wa_bot_handlers_module)


# run server
def run_wa():
    uvicorn.run(clients.app, port=settings.port, host="0.0.0.0", access_log=False)


if __name__ == "__main__":
    tg_bot.start()
    tg_bot.set_bot_commands(
        [
            tg_types.BotCommand(command="info", description="Get info about this user"),
            tg_types.BotCommand(
                command="request_location", description="Ask for location"
            ),
            tg_types.BotCommand(command="ban", description="Ban user"),
            tg_types.BotCommand(command="unban", description="Unban user"),
            tg_types.BotCommand(command="settings", description="Update settings"),
        ],
        scope=tg_types.BotCommandScopeChat(settings.tg_group_topic_id),
    )
    tg_bot.loop.run_in_executor(tg_bot.executor, run_wa)
    idle()
