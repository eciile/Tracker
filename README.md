# Tracker

Tracker is a learning-first agentic AI portfolio project. Its goal is to
investigate bug reports by inspecting a source repository, gathering evidence,
and producing a structured diagnosis.

The project starts with a deliberately small, provider-independent core. We
will build the tools and agent loop ourselves before adding a local language
model or an agent framework.

## Learning roadmap

- [x] Lesson 1: Build safe, read-only repository tools.
- [ ] Lesson 2: Define structured tool calls and validate model output.
- [ ] Lesson 3: Connect a local model and implement the agent loop.
- [ ] Lesson 4: Produce evidence-backed investigation reports.
- [ ] Lesson 5: Build an evaluation dataset and measure reliability.
- [ ] Lesson 6: Add approval-gated patches and test execution.
- [ ] Lesson 7: Expose the agent through an API and document results.

## Lesson 1

Run the tests:

```powershell
py -m unittest discover -s tests -v
```

Try the repository tools against this project:

```powershell
py -m tracker.cli list-files .
py -m tracker.cli search . "RepositoryTools"
py -m tracker.cli read . README.md --start 1 --end 12
```

The tools are intentionally read-only. Paths must remain inside the selected
repository, hidden files are excluded, binary files are rejected, and reads
have size and line limits.

## Why this is an agent project

An agent is more than a chat prompt. The model chooses actions, the application
validates and executes those actions, and the results are returned to the model
until it can complete the task. Lesson 1 builds the controlled action layer.
