"""Command-line interface for exercising Tracker's repository tools."""

import argparse
from pathlib import Path
from typing import Optional, Sequence

from .tools import RepositoryTools, ToolError

from .agent import AgentError, TrackerAgent
from .dispatcher import ToolDispatcher
from .ollama_client import OllamaModelClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-files")
    list_parser.add_argument("root", type=Path)
    list_parser.add_argument("--path", default=".")

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("root", type=Path)
    search_parser.add_argument("query")

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("root", type=Path)
    read_parser.add_argument("path")
    read_parser.add_argument("--start", type=int, default=1)
    read_parser.add_argument("--end", type=int, default=200)

    investigate_parser = subparsers.add_parser(
        "investigate",
        help="Investigate a repository issue using a local model",
    )
    investigate_parser.add_argument("root", type=Path)
    investigate_parser.add_argument("issue")
    investigate_parser.add_argument(
        "--model",
        default="qwen2.5-coder:3b-instruct",
    )
    investigate_parser.add_argument(
        "--max-steps",
        type=int,
        default=5,
    )
    investigate_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show model responses and tool results",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tools = RepositoryTools(args.root)
        if args.command == "list-files":
            for path in tools.list_files(args.path):
                print(path)
        elif args.command == "search":
            for match in tools.search_code(args.query):
                print(f"{match.path}:{match.line}: {match.text}")
        elif args.command == "read":
            print(tools.read_file(args.path, args.start, args.end))
        elif args.command == "investigate":

            client = OllamaModelClient(model=args.model)
            dispatcher = ToolDispatcher(tools)
            agent = TrackerAgent(
                client=client,
                dispatcher=dispatcher,
                max_steps=args.max_steps,
                trace=print if args.verbose else None,
            )
            print(agent.run(args.issue))
        return 0
    
    except (ToolError, AgentError) as exc:
        print(f"error: {exc}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
