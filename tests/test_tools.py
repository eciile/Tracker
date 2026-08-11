import tempfile
import unittest
from pathlib import Path

from tracker.tools import RepositoryTools, ToolError


class RepositoryToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "auth.py").write_text(
            "def login(email):\n    return email.lower()\n", encoding="utf-8"
        )
        (self.root / ".env").write_text("SECRET=example", encoding="utf-8")
        self.tools = RepositoryTools(self.root)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_lists_non_hidden_files(self) -> None:
        self.assertEqual(self.tools.list_files(), ["src/auth.py"])

    def test_reads_numbered_lines(self) -> None:
        self.assertEqual(
            self.tools.read_file("src/auth.py", 1, 1), "1: def login(email):"
        )

    def test_searches_case_insensitively(self) -> None:
        matches = self.tools.search_code("LOGIN")
        self.assertEqual(matches[0].path, "src/auth.py")
        self.assertEqual(matches[0].line, 1)

    def test_rejects_path_traversal(self) -> None:
        with self.assertRaises(ToolError):
            self.tools.read_file("../outside.txt")

    def test_rejects_hidden_files(self) -> None:
        with self.assertRaises(ToolError):
            self.tools.read_file(".env")


if __name__ == "__main__":
    unittest.main()
