import json
import unittest
from unittest.mock import MagicMock, patch

from tracker.ollama_client import OllamaModelClient


class OllamaModelClientTests(unittest.TestCase):
    @patch("tracker.ollama_client.urlopen")
    def test_complete_sends_chat_request_and_returns_content(self, mock_urlopen):
        response_data = {
            "message": {
                "role": "assistant",
                "content": "READY",
            }
        }
        response_bytes = json.dumps(response_data).encode("utf-8")
        fake_response = MagicMock()
        fake_response.__enter__.return_value.read.return_value = response_bytes
        mock_urlopen.return_value = fake_response

        client = OllamaModelClient(
            model="qwen2.5-coder:3b-instruct",
            timeout=30.0,
        )
        messages = [
            {
                "role": "user",
                "content": "Reply READY",
            }
        ]

        result = client.complete(messages)

        self.assertEqual(result, "READY")
        request = mock_urlopen.call_args.args[0]
        timeout = mock_urlopen.call_args.kwargs["timeout"]
        self.assertEqual(request.full_url, "http://localhost:11434/api/chat")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(timeout, 30.0)

        sent_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sent_body["model"], "qwen2.5-coder:3b-instruct")
        self.assertEqual(sent_body["messages"], messages)
        self.assertFalse(sent_body["stream"])
        self.assertEqual(sent_body["format"], "json")


if __name__ == "__main__":
    unittest.main()
