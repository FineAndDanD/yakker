"""Manage conversation history"""
from typing import Literal, Any

from .message import Message


class Conversation:
    """
    Maintains conversation history for multi-message and multi-step chats
    """
    def __init__(self, init_state: dict = None):
        """Initialize empty conversation"""
        self.messages: list = []
        self.state: dict[str, Any] = init_state or {}

    def set_state(self, new_state: dict) -> None:
        """
        Add the key/value pairs of any valid dictionary into the existing state dictionary
        :param new_state: Any dictionary
        :return: Nothing
        """
        for key, value in new_state:
            setattr(self.state, key, value)

    def add_message(self, content: str, role: Literal["user", "assistant", "system", "tool"] = "user", tool_calls: list[dict] = None, tool_call_id: str = None) -> Message:
        """
        Add a message to the conversation history
        :param role: Message role ("user", "assistant", "system", "tool")
        :param content: Message content
        :return: The created message object
        """
        msg = Message(role=role, content=content, tool_calls=tool_calls, tool_call_id=tool_call_id)
        self.messages.append(msg)
        return msg

    def get_messages(self) -> list[Message]:
        """
        Get all messages in the conversation
        :return: List of all Message objects
        """
        return self.messages

    def clear_message(self) -> None:
        """
        Clear all messages from the conversation
        :return: Nothing
        """
        self.messages = []

    def get_state(self) -> dict[str, Any]:
        """
        Get the entire state dictionary for the conversation
        :return: Internal custom state dictionary
        """
        return self.state

    def update_state(self, new_state: dict) -> dict:
        """
        Perform a shallow merge of the new state with the existing state
        :param new_state: The new state dictionary to merge
        :return: The updated custom state dictionary
        """
        self.state.update(new_state)
        return self.state

    def remove_state_item(self, key) -> dict:
        """
        Remove a specific item from state by key
        :param key: The key representing the item to remove
        :return: The updated custom state object
        """
        self.state.pop(key)
        return self.state

    def clear_state(self):
        """
        Empty the custom state dictionary
        :return: Nothing
        """
        self.state = {}