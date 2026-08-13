from typing import Any
from .protocol import ToolCall
from .tools import RepositoryTools

class DispatchError(ValueError):
    """Raised when a tool call cannot be safely dispatched."""
    pass

class ToolDispatcher:
    ALLOWED_TOOLS = {
        "list_files",
        "read_file",
        "search_code",
    }

    def __init__(self, tools: RepositoryTools):
        self.tools = tools

    def execute(self, call: ToolCall) -> Any:
        if call.name not in self.ALLOWED_TOOLS:
            raise DispatchError(f"Tool '{call.name}' is not allowed.")
        if call.name in self.ALLOWED_TOOLS and call.name != "list_files":
            raise DispatchError(f"Tool '{call.name}' is not implemented yet.")
        allowed_arguments = {"relative_path", "limit"}
        unknown_arguments = set(call.arguments) - allowed_arguments
        relative_path = call.arguments.get("relative_path", ".")
        
        limit = call.arguments.get("limit", 200)
        
        if call.name == "list_files":
            if unknown_arguments:
                raise DispatchError("list_files only accepts 'relative_path' and 'limit' arguments.")
            if not isinstance(relative_path, str):
                raise DispatchError("'relative_path' must be a string.")
            if not isinstance(limit, int) or isinstance(limit, bool):
                raise DispatchError("'limit' must be an integer.")
            

        return self.tools.list_files(
            relative_path=relative_path,
            limit=limit,
        )