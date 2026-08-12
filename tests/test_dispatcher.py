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

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_execute_allowed_tool(self):
        call = ToolCall(
            id="call-1",
            name="list_files",
            arguments={},
        )
        result = self.dispatcher.execute(call)
        self.assertEqual(result, 'list_files')

    def test_execute_disallowed_tool(self):
        call = ToolCall(
            id="call-2",
            name="delete_file",
            arguments={},
        )
        with self.assertRaises(DispatchError):
            self.dispatcher.execute(call)

