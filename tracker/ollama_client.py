import json
from typing import List, Dict
from urllib.request import Request, urlopen

class OllamaModelClient:
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, messages: List[Dict[str, str]]) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
        }
        body_encoded = json.dumps(body).encode("utf-8")

        request = Request(
        url=f"{self.base_url}/api/chat",
        data=body_encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            response_body = response.read()
            decoded = json.loads(response_body.decode("utf-8"))

        return decoded["message"]["content"]
