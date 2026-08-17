from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
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

        
        