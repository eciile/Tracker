import unittest
from tracker.protocol import ToolCall, ProtocolError

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