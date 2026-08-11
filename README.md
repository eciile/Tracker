# Tracker

Tracker is an evidence-driven agent for investigating software bugs. Given a
bug report and a source repository, it explores the codebase, identifies
relevant files, gathers line-level evidence, and produces a structured root
cause analysis.

The project is designed around a provider-independent agent loop, allowing it
to work with local or hosted language models without coupling its core tools to
a single AI platform.

## Project status

Tracker is under active development. The current version provides a secure,
read-only toolkit for repository inspection through Python and the command
line. Model-driven investigation and structured reports are planned next.

## Current capabilities

- Recursively list files within a selected repository.
- Search source files using case-insensitive text matching.
- Read bounded, line-numbered sections of text files.
- Reject paths that escape the repository root.
- Exclude hidden files such as `.env` from inspection.
- Reject binary, non-UTF-8, and oversized files.
- Limit file listings, search results, and line ranges.

## Planned capabilities

- Structured and validated model tool calls.
- Support for locally hosted language models.
- Multi-step repository investigation.
- Evidence-backed bug diagnosis reports.
- Evaluation datasets and reliability metrics.
- Approval-gated patch generation and test execution.
- HTTP API and investigation history.

## Architecture

```text
Bug report
    |
    v
Agent reasoning loop
    |
    v
Validated tool dispatcher
    |
    +-- list_files
    +-- search_code
    +-- read_file
    |
    v
Evidence-backed investigation report
```

Only the repository tools are implemented in the current version. The agent
loop and model integration shown above describe the intended architecture.

## Requirements

- Python 3.9 or newer
- Git

The current version has no third-party runtime dependencies.

## Installation

Clone the repository and enter the project directory:

```powershell
git clone https://github.com/eciile/Tracker.git
cd Tracker
```

You can run Tracker directly from the repository. To install its CLI in an
isolated environment:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -e .
```

## Usage

List the files in a repository:

```powershell
py -m tracker.cli list-files C:\path\to\repository
```

Search for a symbol or phrase:

```powershell
py -m tracker.cli search C:\path\to\repository "login"
```

Read a specific range of lines:

```powershell
py -m tracker.cli read C:\path\to\repository src/auth.py --start 1 --end 80
```

When installed with `pip install -e .`, replace `py -m tracker.cli` with
`tracker` in these commands.

## Testing

Run the test suite from the project directory:

```powershell
py -m unittest discover -s tests -v
```

The tests cover normal repository operations as well as security boundaries
such as hidden-file access and path traversal.

## Security model

Repository content should be treated as untrusted input. Tracker therefore
starts with read-only, least-privilege tools and validates paths before any
file operation. Future capabilities that can execute tests or modify files
will require explicit user approval and additional isolation.

## License

This project is licensed under the MIT License.
