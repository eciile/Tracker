import unittest
from tracker.protocol import ToolCall, ProtocolError, ToolResult
import json

class TestToolCall(unittest.TestCase):
    def test_from_json_valid(self):
        payload = '{"id": "123", "name": "test_tool", "arguments": {"arg1": "value1"}}'
        tool_call = ToolCall.from_json(payload)
        self.assertEqual(tool_call.id, "123")
        self.assertEqual(tool_call.name, "test_tool")
        self.assertEqual(tool_call.arguments, {"arg1": "value1"})

    def test_from_json_invalid_json(self):
        payload = '{"id": "123", "name": "test_tool", "arguments": {"arg1": "value1"'
        with self.assertRaises(ProtocolError):
            ToolCall.from_json(payload)

    def test_from_json_missing_keys(self):
        payload = '{"id": "123", "name": "test_tool"}'
        with self.assertRaises(ProtocolError):
            ToolCall.from_json(payload)

    def test_from_json_extra_keys(self):
        payload = '{"id": "123", "name": "test_tool", "arguments": {"arg1": "value1"}, "extra_key": 42}'
        with self.assertRaises(ProtocolError):
            ToolCall.from_json(payload)

    def test_tool_result_serializes_success(self):
        result = ToolResult(
            tool_call_id="call-1",
            ok=True,
            output=["app.py"],
        )

        payload = result.to_json()
        decoded = json.loads(payload)

        self.assertEqual(decoded["tool_call_id"], "call-1")
        self.assertTrue(decoded["ok"])
        self.assertEqual(decoded["output"], ["app.py"])
        self.assertIsNone(decoded["error"])

    def test_result_serializes_failure(self):
        results = ToolResult(
            tool_call_id="call-2",
            ok=False,
            error="Tool is not allowed",
        )
        payload = results.to_json()
        decoded = json.loads(payload)
        self.assertEqual(decoded["tool_call_id"], "call-2")
        self.assertFalse(decoded["ok"])
        self.assertIsNone(decoded["output"])
        self.assertEqual(decoded["error"], "Tool is not allowed")

    def test_results_unicode_serialization(self):
        results = ToolResult(
            tool_call_id="call-3",
            ok=True,
            output={"message": "Fichier trouvé"},
        )
        payload = results.to_json()
        decoded = json.loads(payload)
        self.assertEqual(decoded["tool_call_id"], "call-3")
        self.assertTrue(decoded["ok"])
        self.assertIn("trouvé", payload)      
