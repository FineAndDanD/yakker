"""Build AG-UI protocol compliant request"""
import logging
import uuid
from typing import Any

import httpx

from .tool import validate_tools
from .message import Message

logger = logging.getLogger(__name__)

def build_request(
        messages: list[Message],
        thread_id: str = None,
        state: dict[str, Any] = None,
        tools: list[dict] = None
) -> dict:
    """
    Build an AG-UI request from messages

    Raises:
        ValueError: If messages is empty or tools are malformed
        TypeError: If parameters have wrong types
    :param tools: Additional capabilities to pass to the agent by way of functions
    :param messages: List of message objects
    :param thread_id: Optional thread ID for conversation correlation (will autogenerate if omitted)
    :param state: Optional state dictionary
    :return: Dictionary ready to send to an AG-UI server
    """

    if not messages:
        raise ValueError("Messages list cannot be empty")
    if not isinstance(messages, list):
        raise TypeError(f"Messages must be of type list, got {type(messages).__name__}")
    if not all(isinstance(message, Message) for message in messages):
        invalid = [type(message).__name__ for message in messages if not isinstance(message, Message)]
        raise TypeError(f"All messages must be message instances, got {set(invalid)}")

    if tools:
        validate_tools(tools)

    if state is not None and not isinstance(state, dict):
        raise TypeError(f"State must be a dictionary, got {type(state).__name__}")

    if not any(message.role == 'user' for message in messages):
        logger.warning("No user messages in the conversation - may produce unexpected results")

    return {
        "threadId": thread_id or str(uuid.uuid4()),
        "runId": str(uuid.uuid4()),
        "messages": [msg.to_dict() for msg in messages],
        "state": state or {},
        "tools": tools or [],
        "context": [],
        "forwardedProps": {}
    }


def send_request(url: str, request_data: dict, timeout: float = 30.0) -> httpx.Response:
    """
    Sends a request to an AG-UI server
    :param timeout: Request will fail after this timeout threshold (default 30 seconds)
    :param url: The AG-UI server URL
    :param request_data: The data to send to the server (from build_request). Follows the request pattern for the AG-UI protocol
    :return: The HTTP response object
    """
    response = httpx.post(
        url,
        json=request_data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        },
        timeout=timeout
    )

    # Check if request was successful
    response.raise_for_status()

    return response

async def send_request_stream(http_client: httpx.AsyncClient, url: str, request_data: dict, timeout: float = 30.0):
    """
    Sends a request to an AG-UI server and streams back the response async
    :param http_client:
    :param url: The AG-UI server URL
    :param request_data: The data to send to the server (from build_request). Follows the request pattern for the AG-UI protocol
    :param timeout: Request will fail after this timeout threshold (default 30 seconds)
    :return: The HTTP response object
    """
    async with http_client.stream(
        'POST',
        url,
        json=request_data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        },
        timeout=timeout,
    ) as response:
        async for line in response.aiter_lines():
            if line:
                yield line