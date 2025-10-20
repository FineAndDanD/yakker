"""Basic message representation using the AG-UI protocol"""
import uuid
from typing import Literal

class Message:
    """Represents a single message in a conversation"""
    def __init__(
            self,
            role: Literal["user", "assistant", "system", "tool"],
            content: str,
            message_id: str = None,
            tool_calls: list[dict] = None,
            tool_call_id: str = None
    ):
        self.role = role
        self.content = content
        self.id = message_id or str(uuid.uuid4())
        self.tool_calls = tool_calls or None
        self.tool_call_id = tool_call_id or None

    def to_dict(self):
        """Convert to Dictionary for AG-UI request"""
        formatted_message = {
            "id": self.id,
            "role": self.role,
            "content": self.content
        }

        if self.tool_calls and self.role == 'assistant':
            formatted_message['toolCalls'] = self.tool_calls
        if self.tool_call_id and self.role == 'tool':
            formatted_message['toolCallId'] = self.tool_call_id
        return formatted_message
