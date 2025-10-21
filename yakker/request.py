"""Build AG-UI protocol compliant request"""
import uuid
from typing import Any

import httpx

from .message import Message

def build_request(
        messages: list[Message],
        thread_id: str = None,
        state: dict[str, Any] = None,
        tools: list[dict] = None,
        tool_results: list[dict] = None
) -> dict:
    """
    Build an AG-UI request from messages
    :param tools: Additional capabilities to pass to the agent by way of functions
    :param messages: List of message objects
    :param thread_id: Optional thread ID for conversation correlation (will autogenerate if omitted)
    :param state: Optional state dictionary
    :return: Dictionary ready to send to an AG-UI server
    """

    return {
        "threadId": thread_id or str(uuid.uuid4()),
        "runId": str(uuid.uuid4()),
        "messages": [msg.to_dict() for msg in messages],
        "state": state or {},
        "tools": tools or [],
        # "toolResults": tool_results or [],
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