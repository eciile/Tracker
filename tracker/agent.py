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
- Every final answer must include at least one evidence item.
- Evidence must refer only to files and line ranges returned successfully by read_file.
- Use repository-relative paths.
- start_line and end_line must be positive integers, and start_line must not exceed end_line.
- Cite the smallest line range that directly supports the answer.

After gathering enough evidence, return:
For a final answer, return exactly:
{"type":"final","answer":"...","evidence":[{"path":"relative/file.py","start_line":1,"end_line":10}]}

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

    def run(self, issue: str) -> FinalAnswer:
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
        successful_reads = []
        for _ in range(self.max_steps):
            response = self.client.complete(messages)
            if self.trace is not None:
                self.trace(f"MODEL: {response}")
            try:
                model_response = parse_model_response(response)
            except ProtocolError as exc:
                if self.trace is not None:
                    self.trace(f"REJECTED: Invalid model response: {exc}")
                read_hint = ""

                if successful_reads:
                    path, read_start, read_end = successful_reads[-1]
                    suggested_end = min(read_end, read_start + 24)

                    read_hint = (
                        f" You successfully read {path} from line {read_start} "
                        f"through line {read_end}. Use evidence contained within "
                        f"that range, with start_line not greater than end_line. "
                        f"A valid range would be start_line {read_start} and "
                        f"end_line {suggested_end}."
                    )
                messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your previous response was an invalid response: {exc} "
                            "Return exactly one valid JSON object matching either the "
                            "tool_call or final response schema. Do not include Markdown "
                            "or additional text."
                            f"{read_hint}"

                        ),
                    }
                )
                continue

            if isinstance(model_response, FinalAnswer):
                required_tools = {"search_code", "read_file"}

                if required_tools.issubset(successful_tools):
                    unsupported_evidence = []

                    for citation in model_response.evidence:
                        citation_is_supported = any(
                            citation.path == path
                            and citation.start_line >= read_start
                            and citation.end_line <= read_end
                            for path, read_start, read_end in successful_reads
                        )

                        if not citation_is_supported:
                            unsupported_evidence.append(citation)

                    if model_response.evidence and not unsupported_evidence:
                        return model_response

                    if self.trace is not None:
                        self.trace(
                            "REJECTED: Final answer contains missing or unsupported evidence."
                        )

                    messages.append(
                        {
                            "role": "assistant",
                            "content": response,
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "The final answer's evidence is missing or unsupported. "
                                "Cite only repository paths and line ranges returned by "
                                "successful read_file calls."
                            ),
                        }
                    )
                    continue

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
                read_is_complete = True

                if model_response.name == "read_file":
                    output_lines = [
                        line
                        for line in result.output.splitlines()
                        if line.strip()
                    ]

                    if output_lines:
                        last_line = output_lines[-1]
                        code_text = last_line.split(": ", 1)[-1]

                        if code_text.rstrip().endswith(":"):
                            read_is_complete = False

                            if self.trace is not None:
                                self.trace(
                                    "REJECTED: read_file stopped at a block opener."
                                )

                if read_is_complete:
                    successful_tools.add(model_response.name)

                    if model_response.name == "read_file":
                        successful_reads.append(
                            (
                                model_response.arguments["relative_path"],
                                model_response.arguments.get("start", 1),
                                model_response.arguments.get("end", 200),
                            )
                        )
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
            if not result.ok:
                correction = (
                    f"The tool call failed: {result.error} "
                    "Do not repeat the same failed call. Correct the arguments "
                    "and use a new tool-call ID."
                )

                if model_response.name == "read_file":
                    correction += (
                        " For read_file, use start and end, not start_line "
                        "and end_line."
                    )

                messages.append(
                    {
                        "role": "user",
                        "content": correction,
                    }
                )

        raise AgentError(f"Agent exceeded the maximum of {self.max_steps} steps")
