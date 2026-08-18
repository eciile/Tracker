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
class Evidence:
    path: str
    start_line: int
    end_line: int

@dataclass(frozen=True)
class FinalAnswer:
    """A validated final response from the model."""

    answer: str
    evidence: list[Evidence]


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
        expected_keys = {"type", "answer", "evidence"}
        if set(data) != expected_keys:
            raise ProtocolError(
                "Final response requires exactly: type, answer, evidence."
            )

        answer = data["answer"]
        if not isinstance(answer, str) or not answer.strip():
            raise ProtocolError("Final answer must be a non-empty string.")

        raw_evidence = data["evidence"]
        if not isinstance(raw_evidence, list):
            raise ProtocolError("Final evidence must be a list.")

        evidence = []
        expected_evidence_keys = {"path", "start_line", "end_line"}

        for item in raw_evidence:
            if not isinstance(item, dict):
                raise ProtocolError("Each evidence item must be a JSON object.")

            if set(item) != expected_evidence_keys:
                raise ProtocolError(
                    "Each evidence item requires exactly: path, start_line, end_line."
                )
            path = item["path"]
            start_line = item["start_line"]
            end_line = item["end_line"]

            if not isinstance(path, str) or not path.strip():
                raise ProtocolError("Evidence path must be a non-empty string.")

            if type(start_line) is not int or type(end_line) is not int:
                raise ProtocolError("Evidence line numbers must be integers.")

            if start_line < 1 or end_line < 1:
                raise ProtocolError("Evidence line numbers must be positive.")

            if start_line > end_line:
                raise ProtocolError(
                    "Evidence start_line cannot be greater than end_line."
                )
            evidence.append(
                Evidence(
                    path=item["path"],
                    start_line=item["start_line"],
                    end_line=item["end_line"],
                )
            )
        return FinalAnswer(answer=answer, evidence=evidence)

    raise ProtocolError("Model response type must be 'tool_call' or 'final'.")

        
        
