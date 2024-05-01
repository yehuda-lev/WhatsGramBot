import logging
from pywa import handlers, filters

from wa import wa_bot

_logger = logging.getLogger(__name__)


HANDLERS = [handlers.MessageHandler(wa_bot.echo, filters.text)]
