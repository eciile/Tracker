import unittest
import tempfile
from pathlib import Path

from tracker.dispatcher import ToolDispatcher, DispatchError
from tracker.tools import RepositoryTools
from tracker.protocol import ToolCall


class TestToolDispatcher(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.tools = RepositoryTools(self.root)
        self.dispatcher = ToolDispatcher(self.tools)
        (self.root / "app.py").write_text("", encoding="utf-8")
        (self.root / "src").mkdir()
        (self.root / "src" / "auth.py").write_text("def login():\n    return True\n", encoding="utf-8")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_list_files_with_defaults_returns_all_files(self):
        call = ToolCall(
            id="call-1",
            name="list_files",
            arguments={},
        )
        result = self.dispatcher.execute(call)
        self.assertEqual(result, ["app.py", "src/auth.py"])

    def test_list_files_accepts_relative_path(self):
        call = ToolCall(
            id="call-2",
            name="list_files",
            arguments={"relative_path": "src"},
        )
        result = self.dispatcher.execute(call)
        self.assertEqual(result, ["src/auth.py"])

    def test_list_files_rejects_unknown_argument(self):
        call = ToolCall(
            id="call-3",
            name="list_files",
            arguments={"shell": "whoami"},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_list_files_rejects_string_limit(self):
        call = ToolCall(
            id="call-4",
            name="list_files",
            arguments={"limit": "10"},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_list_files_rejects_boolean_limit(self):
        call = ToolCall(
            id="call-5",
            name="list_files",
            arguments={"limit": True},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_read_file(self):
        call = ToolCall(
            id="call-6",
            name="read_file",
            arguments={"relative_path": "src/auth.py", "start": 1, "end": 2},            
        )

        result=self.dispatcher.execute(call)
        self.assertEqual(result,"1: def login():\n2:     return True"
        )

    def test_read_file_relative_path_missing(self):
        call = ToolCall(
            id="call-7",
            name="read_file",
            arguments={},            
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)
  
    def test_read_file_unknows_argument(self):
        call = ToolCall(
            id="call-8",
            name="read_file",
            arguments={"relative_path": "src/auth.py", "start": 1, "unknown": 2},            
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_read_file_type_relative_path(self):
        call = ToolCall(
            id="call-9",
            name="read_file",
            arguments={"relative_path": 0, "start": 1, "end": 2},            
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)  

    def test_read_file_string_start(self):
        call = ToolCall(
            id="call-9",
            name="read_file",
            arguments={"relative_path": "src/auth.py", "start": "1", "end": 2},            
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)  

    def test_read_file_bool_end(self):
        call = ToolCall(
            id="call-9",
            name="read_file",
            arguments={"relative_path": "src/auth.py", "start": 1, "end": True},            
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)  

    def test_allowed_but_unimplemented_tool_is_rejected(self):
        call = ToolCall(
            id="call-6",
            name="search_code",
            arguments={"query": "login"},
        )
        with self.assertRaisesRegex(DispatchError, "not implemented yet"):
            self.dispatcher.execute(call)

    def test_execute_disallowed_tool(self):
        call = ToolCall(
            id="call-7",
            name="delete_file",
            arguments={},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

