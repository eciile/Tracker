"""The orchestration loop for repository investigations."""

from .dispatcher import ToolDispatcher
from .model import ModelClient
from .protocol import FinalAnswer, ProtocolError, parse_model_response


SYSTEM_PROMPT = """You are Tracker, a repository investigation agent.

You may request exactly one tool at a time.

Available tools:
- list_files(relative_path=".", limit=200)
- read_file(relative_path, start=1, end=200)
- search_code(query, limit=50)

Every response must be exactly one JSON object with no Markdown or extra text.

To request a tool:
{"type":"tool_call","id":"unique-id","name":"tool_name","arguments":{}}

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
                model_response = parse_model_response(response)
            except ProtocolError as exc:
                raise AgentError(f"Model returned an invalid response: {exc}") from exc

            if isinstance(model_response, FinalAnswer):
                return model_response.answer

            result = self.dispatcher.execute_result(model_response)
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
