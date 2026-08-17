from dataclasses import asdict
from typing import Any
from .protocol import ToolCall, ToolResult
from .tools import RepositoryTools, ToolError

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
        
        if call.name == "list_files":
            allowed_arguments = {"relative_path", "limit"}
            unknown_arguments = set(call.arguments) - allowed_arguments
            relative_path = call.arguments.get("relative_path", ".")
            limit = call.arguments.get("limit", 200)
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

        if call.name == "read_file":
            allowed_arguments = {"relative_path", "start", "end"}
            unknown_arguments = set(call.arguments) - allowed_arguments
            if "relative_path" not in call.arguments:
                raise DispatchError("'relative_path' is required")
            relative_path = call.arguments.get("relative_path")
            start = call.arguments.get("start", 1)
            end = call.arguments.get("end", 200)

            if unknown_arguments:
                raise DispatchError("read_file only accepts 'relative_path','start' and 'end' arguments.")
            if not isinstance(relative_path, str):
                raise DispatchError("'relative_path' must be a string.")
            if not isinstance(start, int) or isinstance(start, bool):
                raise DispatchError("'start' must be an integer.")
            if not isinstance(end, int) or isinstance(end, bool):
                raise DispatchError("'end' must be an integer")

            return self.tools.read_file(
                relative_path=relative_path,
                start=start,
                end=end,
            )

        if call.name == "search_code":
            allowed_arguments = {"query", "limit"}
            unknown_arguments = set(call.arguments) - allowed_arguments
            if "query" not in call.arguments:
                raise DispatchError("'query' is required")
            query = call.arguments.get("query")
            limit = call.arguments.get("limit", 50)

            if unknown_arguments:
                raise DispatchError("search_code only accepts 'query' and 'limit' arguments.")
            if not isinstance(query, str):
                raise DispatchError("'query' must be a string.")
            if not isinstance(limit, int) or isinstance(limit, bool):
                raise DispatchError("'limit' must be an integer.")


            matches = self.tools.search_code(
                query=query,
                limit=limit,
            )
            return [asdict(match) for match in matches]

    def execute_result(self,call: ToolCall) -> ToolResult:
        try:
            output = self.execute(call)
            return ToolResult(
                tool_call_id=call.id,
                ok=True,
                output=output,
            )
        except (DispatchError, ToolError) as exc:
            return ToolResult(
                tool_call_id=call.id,
                ok=False,
                error=str(exc),
            )
