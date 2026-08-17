import unittest


class FakeModelClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.received_messages = []

    def complete(self, messages):
        self.received_messages.append(messages)
        return self.responses.pop(0)


class FakeModelClientTests(unittest.TestCase):
    def test_returns_scripted_responses_and_records_messages(self):
        client = FakeModelClient(["first", "second"])
        first_messages = [{"role": "user", "content": "First request"}]
        second_messages = [{"role": "user", "content": "Second request"}]

        self.assertEqual(client.complete(first_messages), "first")
        self.assertEqual(client.complete(second_messages), "second")
        self.assertEqual(
            client.received_messages,
            [first_messages, second_messages],
        )


if __name__ == "__main__":
    unittest.main()
