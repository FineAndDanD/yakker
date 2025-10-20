"""Sends requests to AG-UI servers"""
import inspect
import logging
from typing import Literal, Callable, Optional, AsyncGenerator

from .tool import build_tool
from .parser import parse_sse_line
from .request import build_request, send_request, send_request_stream
from .stream import parse_events, process_response
from .conversation import Conversation

logger = logging.getLogger(__name__)

class Client:
    """
    A conversation client to manage full conversations with LLM's through a AG-UI servers.

    This features an internal conversation history so that users don't have to manage their own context
    """
    def __init__(self, url: str, init_state: dict = None):
        self.conversation = Conversation(init_state)
        self.url = url
        self._approval_handler: Optional[Callable] = None
        self._approval_is_async = False

    def approval_handler(self, func: Callable) -> Callable:
        """
        Decorator to register an approval handler function.
        This is to be used when the agent is requesting approval for an action.
        This gives the end user the flexibility to define their own handler function to present the decision to their users

        Sync Usage:
            @client.approval_handler
            def handle_approval(action: str, details: dict) -> bool:
                return input("Approve? ") == 'y'

        Async Usage:
            TODO: Create example here
        :param func: handler function
        :return: The handler function itself, but that handler should return a True / False value for the agent
        """
        self._approval_handler = func
        self._approval_is_async = inspect.iscoroutinefunction(func)
        return func

    def send_message(self, content: str, role: Literal["user", "assistant", "system", "tool"] = "user", url: str = None) -> str:
        """
        Send a message to an AG-UI server while also including the full conversation history
        :param url: AG-UI server URL
        :param content: Message to send to the server
        :param role: Message role (default: "user")
        :return: Message response as text
        """
        if not url:
            url = self.url
        self.conversation.add_message(role=role, content=content)
        request_data = build_request(messages=self.conversation.get_messages(), state=self.conversation.get_state())
        response = send_request(url, request_data, timeout=60)
        events = parse_events(response.text)
        (agent_text, new_state) = process_response(events, self.conversation.state)

        # Update state in the conversation and add the message
        self.conversation.state.update(new_state)
        self.conversation.add_message(role="assistant", content=agent_text)
        return agent_text

    async def send_message_stream(self, content: str, role: Literal["user", "assistant", "system", "tool"] = "user", url: str = None) -> AsyncGenerator[str, None]:
        """
        Send a message to an AG-UI server while also including the full conversation history and state.
        The response comes back as an async stream of chunks
        :param content: Message to send to the server
        :param role: Message role (default: "user")
        :param url: AG-UI server URL
        :return:
        """
        if not url:
            url = self.url

        logger.info(f"Sending message to {url}")
        # Can build other tools later
        tools = []
        if self._approval_handler:
            tool = build_tool(self._approval_handler)
            if tool:
                tools.append(tool)

        self.conversation.add_message(role=role, content=content)
        request_data = build_request(messages=self.conversation.get_messages(), state=self.conversation.get_state(), tools=tools)
        full_response_text = ""
        new_state = {}

        tool_call = {}

        logger.debug("Executing response stream")
        async for line in send_request_stream(url, request_data, timeout=60):
            event = parse_sse_line(line)
            if not event:
                continue

            if event.get('type') == 'TEXT_MESSAGE_CONTENT':
                chunk = event.get('delta', '')
                full_response_text += chunk
                yield chunk
            elif event.get('type') == 'STATE_SNAPSHOT':
                new_state = event.get('snapshot', {})
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

        tool_calls = []

        if tool_call:
            for key, value in tool_call.items():
                tool_calls.append({
                    "id": key,
                    "type": "function",
                    "function": {
                        "name": value['name'],
                        "arguments": value['args']
                    }
                })

        if tool_calls:
            self.conversation.add_message(role="assistant", content=full_response_text, tool_calls=tool_calls)
        else:
            self.conversation.add_message(role="assistant", content=full_response_text)

        # Update state between requests just in case the LLM decided to change something before the tools get executed
        self.conversation.state.update(new_state)

        if tool_call and self._approval_handler:
            import json

            logger.debug(f"Received tool calls: {tool_call.items()}")
            for key, value in tool_call.items():
                result = str(False)
                try:
                    args = json.loads(value['args'])

                    if self._approval_handler and value['name'] == self._approval_handler.__name__:
                        logger.info("Executing requested tool calls")
                        if self._approval_is_async:
                            result = await self._approval_handler(**args)
                        else:
                            result = self._approval_handler(**args)

                except json.JSONDecodeError as error:
                    logger.error(f"Failed to decode JSON when decoding tool handler arguments: {error}")
                    result = json.dumps({"error": str(error)})
                except Exception as error:
                    logger.error(f"An error occurred when decoding tool handler arguments: {error}")
                    result = json.dumps({"error": str(error)})

                # The content for the message must always be a string
                self.conversation.add_message(role="tool", content=str(result), tool_call_id=key)

            logger.info("Calling the LLM again with follow up request and tool response information")
            # Call the LLM a second time with the tool call results
            # TODO: Enhance this to allow for multi-step execution. It'd be dope to handle all this at the library level so the consumer can just use it
            request_data = build_request(messages=self.conversation.get_messages(), state=self.conversation.get_state(),
                                         tools=tools)
            full_followup_response = ""
            async for line in send_request_stream(url, request_data, timeout=60):
                event = parse_sse_line(line)
                if not event:
                    continue

                if event.get('type') == 'TEXT_MESSAGE_CONTENT':
                    chunk = event.get('delta', '')
                    full_followup_response += chunk
                    yield chunk
                elif event.get('type') == 'STATE_SNAPSHOT':
                    new_state = event.get('snapshot', {})

            self.conversation.add_message(role="assistant", content=full_followup_response)
        elif tool_call and not self._approval_handler:
            logger.warning(
                f"Tool call received ('{list(tool_call.keys())}') but no approval handler is registered. "
                f"Register one with @client.approval_handler"
            )
        # Update the final state after everything is done
        self.conversation.state.update(new_state)
