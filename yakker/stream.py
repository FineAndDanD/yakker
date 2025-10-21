from typing import Literal, Any

from .conversation import Conversation
from .request import build_request, send_request, send_request_stream
from .parser import parse_sse_line

def parse_events(response_text: str) -> list[dict]:
    """
    Parse all events in an SSE stream
    :param response_text: Raw text from an AG-UI server
    :return: List of event dictionaries
    """
    events = []

    lines = response_text.split('\n')

    for line in lines:
        event = parse_sse_line(line)
        if event is not None:
            events.append(event)

    return events

def extract_text(events: list[dict]) -> str:
    """
    Extract the response content from a list of streamed events
    :param events: A list of events from the AG-UI server
    :return: The complete response from the AG-UI server
    """
    text_parts = []

    for event in events:
        if event.get('type') == 'TEXT_MESSAGE_CONTENT':
            delta = event.get('delta', '')
            text_parts.append(delta)

    return ''.join(text_parts)

def process_response(events: list[dict], current_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    text_parts = []
    snapshot = current_state

    for event in events:
        if event.get('type') == 'TEXT_MESSAGE_CONTENT':
            delta = event.get('delta', '')
            text_parts.append(delta)
        if event.get('type') == 'STATE_SNAPSHOT':
            snapshot = event.get('snapshot', {})

    return ''.join(text_parts), snapshot

async def process_event_stream(url: str, request_data: dict, tool_call: dict, state: dict):
    async for line in send_request_stream(url, request_data, timeout=60):
        event = parse_sse_line(line)
        if not event:
            continue

        if event.get('type') == 'TEXT_MESSAGE_CONTENT':
            chunk = event.get('delta', '')
            yield chunk
        elif event.get('type') == 'STATE_SNAPSHOT':
            state.update(event.get('snapshot', {}))
        # Track tool calls
        elif event.get('type') == 'TOOL_CALL_START':
            tool_call_id = event.get('toolCallId')
            tool_call[tool_call_id] = {
                "name": event.get('toolCallName'),
                "args": ""
            }
        elif event.get('type') == 'TOOL_CALL_ARGS':
            tool_call_id = event.get('toolCallId')
            delta = event.get('delta')
            tool_call[tool_call_id]['args'] += delta
        elif event.get('type') == 'TOOL_CALL_END':
            tool_call_id = event.get('toolCallId')
            tool_call[tool_call_id]['complete'] = True


def send_message_simple(url: str, content: str, role: Literal["user", "assistant", "system", "tool"] = "user", state: dict = {}) -> str:
    """
    Send a message to an AG-UI server and get back the full text response
    :param url: The AG-UI server url and endpoint to hit
    :param content: Message content to send
    :param role: Message role (default: "user")
    :return: The complete text response from the AG-UI server
    """

    from yakker.message import Message
    from yakker.request import build_request

    msg = Message(role=role, content=content)
    request_data = build_request([msg], state=state)
    response = send_request(url, request_data, timeout=60)
    events = parse_events(response.text)
    return extract_text(events)

def send_message_with_history(url: str, conversation: Conversation, content: str, role: Literal["user", "assistant", "system", "tool"] = "user", state: dict = {}) -> str:
    conversation.add_message(role=role, content=content)
    request_data = build_request(messages=conversation.get_messages(), state=state)
    response = send_request(url, request_data, timeout=60)
    events = parse_events(response.text)
    agent_text = extract_text(events)
    conversation.add_message(role="assistant", content=agent_text)
    return agent_text