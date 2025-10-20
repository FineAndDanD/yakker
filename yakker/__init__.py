"""Yakker - A Python client for the AG-UI protocol"""

from .message import Message
from .conversation import Conversation
from .client import Client
from .request import build_request, send_request
from .stream import send_message_simple, send_message_with_history

__version__ = "0.1.0"

__all__ = [
    "Message",
    "Conversation",
    "Client",
    "build_request",
    "send_request",
    "send_message_simple",
    "send_message_with_history"
]