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
        (self.root / "app.py").write_text(
            "def login_app():\n    pass\n",
            encoding="utf-8",
        )
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

    def test_search_code_returns_json_compatible_matches(self):
        call = ToolCall(
            id="call-10",
            name="search_code",
            arguments={"query": "login"},
        )
        result = self.dispatcher.execute(call)
        self.assertEqual(
            result,
            [
                {"path": "app.py", "line": 1, "text": "def login_app():"},
                {"path": "src/auth.py", "line": 1, "text": "def login():"},
            ],
        )

    def test_search_code_respects_limit(self):
        call = ToolCall(
            id="call-11",
            name="search_code",
            arguments={"query": "login", "limit": 1},
        )
        result = self.dispatcher.execute(call)
        self.assertEqual(
            result,
            [{"path": "app.py", "line": 1, "text": "def login_app():"}],
        )

    def test_search_code_requires_query(self):
        call = ToolCall(id="call-12", name="search_code", arguments={})
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_search_code_rejects_unknown_argument(self):
        call = ToolCall(
            id="call-13",
            name="search_code",
            arguments={"query": "login", "shell": "whoami"},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_search_code_rejects_non_string_query(self):
        call = ToolCall(
            id="call-14",
            name="search_code",
            arguments={"query": 42},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_search_code_rejects_string_limit(self):
        call = ToolCall(
            id="call-15",
            name="search_code",
            arguments={"query": "login", "limit": "1"},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_search_code_rejects_boolean_limit(self):
        call = ToolCall(
            id="call-16",
            name="search_code",
            arguments={"query": "login", "limit": True},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_execute_disallowed_tool(self):
        call = ToolCall(
            id="call-17",
            name="delete_file",
            arguments={},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

    def test_execute_result_success(self):
        call = ToolCall(
            id="call-18",
            name="list_files",
            arguments={},
        )
        result = self.dispatcher.execute_result(call)
        self.assertEqual (result.tool_call_id, "call-18")
        self.assertTrue (result.ok)
        self.assertEqual (result.output, ["app.py", "src/auth.py"])
        self.assertIsNone(result.error)

    def test_execute_result_fail(self):
        call = ToolCall(
            id="call-19",
            name="delete_file",
            arguments={},
        )
        result = self.dispatcher.execute_result(call)
        self.assertEqual (result.tool_call_id, "call-19")
        self.assertFalse (result.ok)
        self.assertIsNone (result.output)
        self.assertIn("not allowed", result.error)

    def test_execute_result_tool_fail(self):
        call = ToolCall(
            id="call-20",
            name="read_file",
            arguments={"relative_path": "missing.py"},
        )
        result = self.dispatcher.execute_result(call)
        self.assertEqual (result.tool_call_id, "call-20")
        self.assertFalse (result.ok)
        self.assertIsNone (result.output)
        self.assertIn("not a file", result.error)