"""Parse response stream events from the AG-UI servers"""
import json
import logging

logger = logging.getLogger(__name__)


def parse_sse_line(line: str) -> dict | None:
    """
    Parse a single SSE line into a dictionary
    :param line: A line from the SSE stream (e.g. "data: {...}")
    :return: Dictionary with the event data. Or None if line is invalid
    """
    # SSE lines start with "data: "
    if not line.startswith("data: "):
        return None

    json_str = line[6:]

    try:
        # Parse as JSON
        return json.loads(json_str)
    except json.JSONDecodeError as error:
        # Skip malformed JSON and throw a warning
        logger.warning(f"Malformed JSON in SSE stream: {json_str[:100]}...\nError: {error}")
        return None