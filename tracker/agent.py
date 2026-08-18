"""The orchestration loop for repository investigations."""

from .dispatcher import ToolDispatcher
from .model import ModelClient
from .protocol import FinalAnswer, ProtocolError, parse_model_response

from typing import Callable, Optional

SYSTEM_PROMPT = """You are Tracker, a repository investigation agent.

You may request exactly one tool at a time.

Available tools:
- list_files(relative_path=".", limit=200)
- read_file(relative_path, start=1, end=200)
- search_code(query, limit=50)

Every response must be exactly one JSON object with no Markdown or extra text.

To request a tool:
{"type":"tool_call","id":"unique-id","name":"tool_name","arguments":{}}

Investigation requirements:
    1. Use search_code with exact identifiers, error messages, or phrases from the
    user's issue. Do not replace them with related names.
    2. Read the relevant file returned by search_code.
    3. Do not return a final answer until both search_code and read_file have
    succeeded.
    4. Cite the relevant file path and line numbers in the final answer.
    
- When reading a definition, read enough lines to include the complete class or function before answering.
- If the first read_file result ends before the definition is complete, call read_file again for the remaining lines.
- Describe only validation rules visible in the tool results.

After gathering enough evidence, return:
{"type":"final","answer":"A concise evidence-based diagnosis."}

Never claim a tool ran until its tool result appears in the conversation. Use
only paths and evidence returned by tools. If a tool fails, correct the request
or explain the limitation in the final answer.
"""


class AgentError(RuntimeError):
    """Raised when Tracker cannot complete an investigation."""


class TrackerAgent:
    def __init__(
        self,
        client: ModelClient,
        dispatcher: ToolDispatcher,
        max_steps: int = 8,
        trace: Optional[Callable[[str], None]] = None,
    ):
        self.client = client
        self.dispatcher = dispatcher
        self.max_steps = max_steps
        self.trace = trace

    def run(self, issue: str) -> str:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": issue,
            },
        ]
        successful_tools = set()
        for _ in range(self.max_steps):
            response = self.client.complete(messages)
            if self.trace is not None:
                self.trace(f"MODEL: {response}")
            try:
                model_response = parse_model_response(response)
            except ProtocolError as exc:
                raise AgentError(f"Model returned an invalid response: {exc}") from exc

            if isinstance(model_response, FinalAnswer):
                required_tools = {"search_code", "read_file"}

                if required_tools.issubset(successful_tools):
                    return model_response.answer

                missing_tools = required_tools - successful_tools
                missing_text = ", ".join(sorted(missing_tools))

                if self.trace is not None:
                    self.trace(f"REJECTED: Final answer missing successful tools: {missing_text}")

                messages.append({
                    "role": "assistant",
                    "content": response,
                })
                messages.append({
                    "role": "user",
                    "content": (
                        "The investigation is incomplete. Before returning a final answer, "
                        f"successfully use these tools: {missing_text}. "
                        "Search using exact identifiers or error text from the user's issue, "
                        "then read the relevant matching file. Do not invent names or paths."
                    ),
                })
                continue

            result = self.dispatcher.execute_result(model_response)

            if self.trace is not None:
                self.trace(f"TOOL: {result.to_json()}")

            if result.ok:
                successful_tools.add(model_response.name)
            messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "content": result.to_json(),
                }
            )

        raise AgentError(f"Agent exceeded the maximum of {self.max_steps} steps")
