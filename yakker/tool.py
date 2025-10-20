import inspect
from typing import Callable, Optional

TYPE_MAPPING = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "dict": "object",
    "list": "array"
}

def get_json_type(annotation) -> str:
    if annotation == inspect.Parameter.empty:
        return "string"

    type_name = getattr(annotation, '__name__', str(annotation))

    return TYPE_MAPPING.get(type_name, "string")

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

        properties[name] = {
            "type": get_json_type(annotation),
            "description": f"The '{name}' parameter for this tool"
        }
        if param.default == inspect.Parameter.empty:
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
