from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Union
import json


class ProtocolError(ValueError):
    """Raised when a model message violates Tracker's protocol."""
    pass

@dataclass(frozen=True)
class ToolCall:
    id:str
    name:str
    arguments:Dict[str,Any]

    @classmethod
    def from_json(cls, payload:str)->"ToolCall":
        required_keys = {"id", "name", "arguments"}
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ProtocolError("Invalid JSON: Malformed JSON.") from exc

        if not isinstance(data, dict):
            raise ProtocolError("Invalid JSON: Expected a JSON object.")
        if not data.keys() == required_keys:
            raise ProtocolError("Invalid JSON: Missing or extra keys.")
        if not isinstance(data["id"], str) or not data["id"].strip():
            raise ProtocolError("Invalid JSON: 'id' must be a non-empty string.")
        if not isinstance(data["name"], str) or not data["name"].strip():
            raise ProtocolError("Invalid JSON: 'name' must be a non-empty string.")
        if not isinstance(data["arguments"], dict):
            raise ProtocolError("Invalid JSON: 'arguments' must be a dictionary.")

        return cls(**data)

@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    ok: bool
    output: Any = None
    error: Optional[str] = None

    def to_json(self) -> str:
        data = asdict(self)
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
        return payload


@dataclass(frozen=True)
class FinalAnswer:
    """A validated final response from the model."""

    answer: str


ModelResponse = Union[ToolCall, FinalAnswer]


def parse_model_response(payload: str) -> ModelResponse:
    """Parse the model's typed response without guessing at malformed output."""

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ProtocolError("Model response must be valid JSON.") from exc

    if not isinstance(data, dict):
        raise ProtocolError("Model response must be a JSON object.")

    response_type = data.get("type")
    if response_type == "tool_call":
        expected_keys = {"type", "id", "name", "arguments"}
        if set(data) != expected_keys:
            raise ProtocolError(
                "Tool response requires exactly: type, id, name, arguments."
            )
        tool_data = {
            "id": data["id"],
            "name": data["name"],
            "arguments": data["arguments"],
        }
        return ToolCall.from_json(json.dumps(tool_data))

    if response_type == "final":
        if set(data) != {"type", "answer"}:
            raise ProtocolError("Final response requires exactly: type, answer.")
        answer = data["answer"]
        if not isinstance(answer, str) or not answer.strip():
            raise ProtocolError("Final answer must be a non-empty string.")
        return FinalAnswer(answer=answer)

    raise ProtocolError("Model response type must be 'tool_call' or 'final'.")

        
        
