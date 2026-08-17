from typing import Dict, List, Protocol


class ModelClient(Protocol):
    """Interface implemented by language-model providers."""

    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Generate the next assistant message."""
        ...