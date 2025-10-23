import inspect
import logging
import re
from typing import Callable, Optional, get_origin, get_args, Union, Any

logger = logging.getLogger(__name__)

TYPE_MAPPING = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "dict": "object",
    "list": "array"
}

def get_json_type(annotation) -> str:
    # Default to string if no type hint was provided
    if annotation == inspect.Parameter.empty:
        return "string"

    type_name = ''

    origin = get_origin(annotation)

    if origin:

        if origin is Union:
            # Recursively unwrap Optional types until we get to a concrete type we can associate the tool arg with
            args = get_args(annotation)
            non_null_types = [arg for arg in args if arg is not type(None)]
            if len(non_null_types) == 1:
                return get_json_type(non_null_types[0])
            else:
                raise TypeError(
                    f"Union types are not supported: {annotation}"
                    f"Use Optional[T] for nullable types, or use a single type"
                )

        if origin is list:
            return 'array'
        if origin is dict:
            return 'object'
    else:
        type_name = getattr(annotation, '__name__', str(annotation))
        return TYPE_MAPPING.get(type_name, 'string')

def create_items(annotation) -> dict | None:
    origin = get_origin(annotation)

    if origin and origin is list:
        args = get_args(annotation)
        if len(args) > 0:
            # Recursively iterate through the annotation in case of nested lists
            inner_type = args[0]
            inner_json_type = get_json_type(inner_type)
            items_schema: dict[str, Any] = {
                'type': inner_json_type
            }

            inner_items = create_items(inner_type)
            if inner_items:
                items_schema['items'] = inner_items

            return items_schema

    return None

def build_tool(approval_handler: Optional[Callable]) -> dict | None:
    """
    Build a single tool to send to an agent in order to execute on an operation
    :param approval_handler: The handler containing the function to be turned into a tool
    :return:
    """
    if not approval_handler:
        return None

    properties = {}
    required_params = []
    param_properties = inspect.signature(approval_handler).parameters

    for name, param in param_properties.items():
        annotation = param.annotation

        property_schema: dict[str, Any] = {'type': get_json_type(annotation), 'description': f"The '{name}' parameter for this tool"}

        items = create_items(annotation)
        if items:
            property_schema['items'] = items

        properties[name] = property_schema
        if param.default == inspect.Parameter.empty:
            # Check for Optional type since that can't be listed as required (it could always be None as a fallback
            origin = get_origin(annotation)
            args = get_args(annotation)
            is_optional_type = origin is Union and type(None) in args

            if not is_optional_type:
                required_params.append(name)

    tool = {
            "name": approval_handler.__name__,
            "description": "Run this tool when you require approval from the user",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_params
            }
        }

    return tool

def validate_tools(tools: list[dict]) -> None:
    """
    Validates tool request payload structure
    :param tools: Tools to be validated
    :return: Nothing
    """
    if not isinstance(tools, list):
        raise TypeError(f"Tools must be a list, got {type(tools).__name__}")
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            raise TypeError(f"Tool at index {index} must be a dictionary, found {type(tool).__name__}")

        required_fields = ['name', 'description', 'parameters']
        missing_fields = [field for field in required_fields if field not in tool]
        if missing_fields:
            raise ValueError(f"Tool at index {index} is missing required fields: {missing_fields}")

        name = tool['name']
        if not isinstance(name, str) or not name:
            raise ValueError(f"Tool at index {index} has an invalid name")

        # Warn about non-standard names
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', name):
            logger.warning(f"Tool name' {name}' has special characters, this may cause issues")

        params = tool['parameters']
        if not isinstance(params, dict):
            raise TypeError(f"Tool '{name}' parameters must be a dictionary")
        if 'type' not in params or params['type'] != 'object':
            raise ValueError(f"Tool '{name}' parameters must have type='object'")