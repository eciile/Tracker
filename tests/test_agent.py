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
                '"Login is implemented in src/auth.py on line 1.",'
                '"evidence":[{"path":"src/auth.py",'
                '"start_line":1,"end_line":1}]}'
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

    def test_recovers_from_malformed_model_response(self):
        client = FakeModelClient(
            [
                '{"type":"tool_call","id":"bad"}\nExtra explanation',
                '{"type":"tool_call","id":"call-1","name":"search_code",'
                '"arguments":{"query":"login"}}',
                '{"type":"tool_call","id":"call-2","name":"read_file",'
                '"arguments":{"relative_path":"src/auth.py","start":1,"end":2}}',
                '{"type":"final","answer":"Login is in src/auth.py.",'
                '"evidence":[{"path":"src/auth.py",'
                '"start_line":1,"end_line":1}]}',
            ]
        )
        agent = TrackerAgent(client, self.dispatcher, max_steps=4)

        answer = agent.run("Where is login defined?")

        self.assertEqual(answer, "Login is in src/auth.py.")
        self.assertEqual(len(client.received_messages), 4)

        correction_request = client.received_messages[1]
        self.assertEqual(correction_request[-1]["role"], "user")
        self.assertIn(
            "invalid response",
            correction_request[-1]["content"].lower(),
        )

    def test_rejects_final_answer_before_using_tool(self):
        client = FakeModelClient([
            (
                '{"type":"final",'
                '"answer":"Login is in an invented file.",'
                '"evidence":[]}'
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
                '"answer":"Login is defined in src/auth.py.",'
                '"evidence":[{"path":"src/auth.py",'
                '"start_line":1,"end_line":1}]}'
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

    def test_rejects_final_answer_with_unread_evidence(self):
        client = FakeModelClient(
            [
                '{"type":"tool_call","id":"call-1","name":"search_code",'
                '"arguments":{"query":"login"}}',
                '{"type":"tool_call","id":"call-2","name":"read_file",'
                '"arguments":{"relative_path":"src/auth.py","start":1,"end":2}}',
                '{"type":"final","answer":"Login is elsewhere.",'
                '"evidence":[{"path":"src/other.py",'
                '"start_line":1,"end_line":2}]}',
                '{"type":"final","answer":"Login is in src/auth.py.",'
                '"evidence":[{"path":"src/auth.py",'
                '"start_line":1,"end_line":1}]}',
            ]
        )
        agent = TrackerAgent(client, self.dispatcher, max_steps=4)

        answer = agent.run("Where is login defined?")

        self.assertEqual(answer, "Login is in src/auth.py.")
        self.assertEqual(len(client.received_messages), 4)
        self.assertIn(
            "evidence",
            client.received_messages[3][-1]["content"].lower(),
        )

    def test_rejects_read_that_stops_at_block_opener(self):
        client = FakeModelClient(
            [
                '{"type":"tool_call","id":"call-1","name":"search_code",'
                '"arguments":{"query":"login"}}',
                '{"type":"tool_call","id":"call-2","name":"read_file",'
                '"arguments":{"relative_path":"src/auth.py","start":1,"end":1}}',
                '{"type":"final","answer":"Login is defined here.",'
                '"evidence":[{"path":"src/auth.py",'
                '"start_line":1,"end_line":1}]}',
                '{"type":"tool_call","id":"call-3","name":"read_file",'
                '"arguments":{"relative_path":"src/auth.py","start":1,"end":2}}',
                '{"type":"final","answer":"Login returns True.",'
                '"evidence":[{"path":"src/auth.py",'
                '"start_line":1,"end_line":2}]}',
            ]
        )
        agent = TrackerAgent(client, self.dispatcher, max_steps=5)

        answer = agent.run("Explain what login does.")

        self.assertEqual(answer, "Login returns True.")
        self.assertEqual(len(client.received_messages), 5)

    def test_gives_correction_after_failed_tool_call(self):
        client = FakeModelClient(
            [
                '{"type":"tool_call","id":"call-1","name":"search_code",'
                '"arguments":{"query":"login"}}',
                '{"type":"tool_call","id":"call-2","name":"read_file",'
                '"arguments":{"relative_path":"src/auth.py",'
                '"start_line":1,"end_line":2}}',
                '{"type":"tool_call","id":"call-3","name":"read_file",'
                '"arguments":{"relative_path":"src/auth.py",'
                '"start":1,"end":2}}',
                '{"type":"final","answer":"Login returns True.",'
                '"evidence":[{"path":"src/auth.py",'
                '"start_line":1,"end_line":2}]}',
            ]
        )
        agent = TrackerAgent(client, self.dispatcher, max_steps=4)

        answer = agent.run("Explain what login does.")

        self.assertEqual(answer, "Login returns True.")

        correction_request = client.received_messages[2]
        self.assertEqual(correction_request[-1]["role"], "user")
        self.assertIn(
            "tool call failed",
            correction_request[-1]["content"].lower(),
        )
        self.assertIn(
            "start and end",
            correction_request[-1]["content"].lower(),
        )

if __name__ == "__main__":
    unittest.main()
