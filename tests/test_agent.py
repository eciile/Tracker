import tempfile
import unittest
from pathlib import Path

from tracker.agent import AgentError, TrackerAgent
from tracker.dispatcher import ToolDispatcher
from tracker.tools import RepositoryTools


class FakeModelClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.received_messages = []

    def complete(self, messages):
        self.received_messages.append(list(messages))
        return self.responses.pop(0)


class TrackerAgentTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "auth.py").write_text(
            "def login():\n    return True\n",
            encoding="utf-8",
        )
        self.dispatcher = ToolDispatcher(RepositoryTools(self.root))

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_runs_tool_call_then_returns_final_answer(self):
        client = FakeModelClient(
            [
                '{"type":"tool_call","id":"call-1","name":"search_code",'
                '"arguments":{"query":"login"}}',
                '{"type":"tool_call","id":"call-2","name":"read_file",'
                '"arguments":{"relative_path":"src/auth.py",'
                '"start":1,"end":2}}',
                '{"type":"final","answer":'
                '"Login is implemented in src/auth.py on line 1."}',
            ]
        )
        agent = TrackerAgent(client, self.dispatcher)

        answer = agent.run("Where is login implemented?")

        self.assertEqual(
            answer,
            "Login is implemented in src/auth.py on line 1.",
        )
        self.assertEqual(len(client.received_messages), 3)
        second_request = client.received_messages[1]
        self.assertEqual(second_request[-1]["role"], "tool")
        self.assertIn("src/auth.py", second_request[-1]["content"])

    def test_stops_after_maximum_steps(self):
        repeated_call = (
            '{"type":"tool_call","id":"call-1",'
            '"name":"list_files","arguments":{}}'
        )
        client = FakeModelClient([repeated_call, repeated_call])
        agent = TrackerAgent(client, self.dispatcher, max_steps=2)

        with self.assertRaisesRegex(AgentError, "maximum of 2 steps"):
            agent.run("Keep investigating forever")

    def test_rejects_malformed_model_response(self):
        client = FakeModelClient(
            ['{"type":"tool_call","id":"call-1"}\nExtra explanation']
        )
        agent = TrackerAgent(client, self.dispatcher)

        with self.assertRaisesRegex(AgentError, "invalid response"):
            agent.run("Investigate this issue")

    def test_rejects_final_answer_before_using_tool(self):
        client = FakeModelClient([
            (
                '{"type":"final",'
                '"answer":"Login is in an invented file."}'
            ),
            (
                '{"type":"tool_call","id":"call-1",'
                '"name":"search_code",'
                '"arguments":{"query":"login"}}'
            ),
            (
                '{"type":"tool_call","id":"call-2",'
                '"name":"read_file",'
                '"arguments":{"relative_path":"src/auth.py",'
                '"start":1,"end":2}}'
            ),
            (
                '{"type":"final",'
                '"answer":"Login is defined in src/auth.py."}'
            ),
        ])
        agent = TrackerAgent(
            client=client,
            dispatcher=self.dispatcher,
            max_steps=4,
        )

        answer = agent.run("Where is login defined?")

        self.assertEqual(
            answer,
            "Login is defined in src/auth.py.",
        )
        self.assertEqual(len(client.received_messages), 4)

        second_request = client.received_messages[1]
        self.assertIn(
            "investigation is incomplete",
            second_request[-1]["content"],
        )
        self.assertIn("search_code", second_request[-1]["content"])
        self.assertIn("read_file", second_request[-1]["content"])


if __name__ == "__main__":
    unittest.main()
