from pywa import types as wa_types
from dataclasses import dataclass


@dataclass
class Tracker(wa_types.CallbackData):
    """Tracker for messages."""

    chat_id: int
    msg_id: int
