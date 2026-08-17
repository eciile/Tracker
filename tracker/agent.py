"""The orchestration loop for repository investigations."""

from .dispatcher import ToolDispatcher
from .model import ModelClient
from .protocol import ProtocolError, ToolCall


SYSTEM_PROMPT = """You are Tracker, a repository investigation agent.

You may request exactly one tool at a time.

Available tools:
- list_files(relative_path=".", limit=200)
- read_file(relative_path, start=1, end=200)
- search_code(query, limit=50)

To request a tool, reply with only a JSON object:
{"id":"unique-id","name":"tool_name","arguments":{}}

After gathering enough evidence, reply with a concise final diagnosis in plain
text. Do not wrap the final diagnosis in JSON.
"""


class AgentError(RuntimeError):
    """Raised when Tracker cannot complete an investigation."""


class TrackerAgent:
    def __init__(
        self,
        client: ModelClient,
        dispatcher: ToolDispatcher,
        max_steps: int = 8,
    ):
        self.client = client
        self.dispatcher = dispatcher
        self.max_steps = max_steps

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

        for _ in range(self.max_steps):
            response = self.client.complete(messages)
            try:
                call = ToolCall.from_json(response)
            except ProtocolError:
                return response

            result = self.dispatcher.execute_result(call)
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

