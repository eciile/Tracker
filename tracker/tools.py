"""Safe, read-only tools for inspecting a source repository."""

from dataclasses import dataclass
from pathlib import Path
from typing import List


class ToolError(ValueError):
    """Raised when a repository tool receives an unsafe or invalid request."""


@dataclass(frozen=True)
class SearchMatch:
    path: str
    line: int
    text: str


class RepositoryTools:
    """Read-only operations constrained to one repository root."""

    def __init__(self, root: Path, max_file_bytes: int = 200_000) -> None:
        resolved_root = root.resolve()
        if not resolved_root.is_dir():
            raise ToolError("Repository root must be an existing directory")
        self.root = resolved_root
        self.max_file_bytes = max_file_bytes

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ToolError("Path must remain inside the repository") from exc
        return candidate

    @staticmethod
    def _is_hidden(relative: Path) -> bool:
        return any(part.startswith(".") for part in relative.parts)

    def list_files(self, relative_path: str = ".", limit: int = 200) -> List[str]:
        if not 1 <= limit <= 500:
            raise ToolError("limit must be between 1 and 500")
        directory = self._resolve(relative_path)
        if not directory.is_dir():
            raise ToolError("Requested path is not a directory")

        files: List[str] = []
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(self.root)
            if path.is_file() and not self._is_hidden(relative):
                files.append(relative.as_posix())
                if len(files) >= limit:
                    break
        return files

    def read_file(self, relative_path: str, start: int = 1, end: int = 200) -> str:
        if start < 1 or end < start or end - start >= 500:
            raise ToolError("Use a valid range containing at most 500 lines")
        path = self._resolve(relative_path)
        if not path.is_file():
            raise ToolError("Requested path is not a file")
        relative = path.relative_to(self.root)
        if self._is_hidden(relative):
            raise ToolError("Hidden files cannot be read")
        if path.stat().st_size > self.max_file_bytes:
            raise ToolError("File exceeds the configured size limit")

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise ToolError("Binary or non-UTF-8 files cannot be read") from exc

        selected = lines[start - 1 : end]
        return "\n".join(
            f"{number}: {text}"
            for number, text in enumerate(selected, start=start)
        )

    def search_code(self, query: str, limit: int = 50) -> List[SearchMatch]:
        if not query.strip():
            raise ToolError("Search query cannot be empty")
        if not 1 <= limit <= 200:
            raise ToolError("limit must be between 1 and 200")

        definition_matches: List[SearchMatch] = []
        other_matches: List[SearchMatch] = []
        for relative_path in self.list_files(limit=500):
            path = self._resolve(relative_path)
            if path.stat().st_size > self.max_file_bytes:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, text in enumerate(lines, start=1):
                if query.casefold() in text.casefold():
                    match = SearchMatch(
                        relative_path,
                        line_number,
                        text.strip(),
                    )

                    normalized_text = text.strip().casefold()
                    normalized_query = query.strip().casefold()

                    definition_prefixes = (
                        f"class {normalized_query}",
                        f"def {normalized_query}",
                        f"async def {normalized_query}",
                    )

                    if normalized_text.startswith(definition_prefixes):
                        definition_matches.append(match)
                    else:
                        other_matches.append(match)
        ranked_matches = definition_matches + other_matches
        return ranked_matches[:limit]

