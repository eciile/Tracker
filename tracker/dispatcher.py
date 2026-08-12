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
        return call.name
