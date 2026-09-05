# Workflow Orchestrator

Turn a plain-English description into a working, verified codebase — using AI
tools you already have open, not ones you pay for on someone else's API key.

## What this is

Workflow Orchestrator has no model of its own. It is deterministic Python that
classifies your request, scaffolds a project, and dispatches the actual coding
work to whichever real AI tools are already installed and logged in on your
machine: Claude Desktop, ChatGPT Desktop, GitHub Copilot, Cursor, Antigravity,
OpenCode, Gemini/Claude/ChatGPT via a real logged-in browser session, Ollama
locally, or an API key as a last-resort fallback.

It does not trust any of them. Every task is checked against a completion
marker **and** a real on-disk file diff before it counts as done, and the
final status (`completed` / `partial` / `failed`) is computed from what
actually happened, not from whether an agent said "done."

## Requirements

- Python 3.12+
- At least one supported AI tool installed and reachable: a CLI-based one
  (OpenCode, Codex CLI, Claude Code CLI, Ollama), a desktop app you're logged
  into, or a browser session already logged into Gemini/ChatGPT/Claude.

## Install

```bash
pip install -e .
```

On Windows, if you also want desktop-GUI automation (Tier 1-3 capture against
plain, non-Electron apps — see Known limitations below):

```bash
pip install -e ".[automation]"
playwright install   # one-time browser binaries for the browser transport
```

## Quickstart

```bash
workflow doctor                          # see what's actually usable right now
workflow build "a sudoku game with a web ui"
```

`workflow doctor` reports which tools were detected, which optional automation
packages are missing, and what's realistically available before you try to
build anything. `workflow build` runs the full pipeline unattended and prints
a real status at the end — if it's `partial` or `failed`, the failing task
names are listed, not just a generic error.

Prefer a menu instead of a one-shot command? `workflow gui` launches the
original interactive console (create/continue/list projects, providers,
agents, diagnostics, and more).

## How it works

1. **Classify & scaffold** — rule-based first; a real installed chat tool is
   only consulted if the request is genuinely ambiguous (never a coding agent,
   since those hang waiting for a real task instead of a quick answer).
2. **Dispatch** — tasks go to whichever real tool is idle, over one of three
   transports: CLI (most reliable), desktop GUI (3-tier capture: accessibility
   tree, clipboard, OCR), or browser (real Playwright against your logged-in
   session).
3. **Verify** — up to 8 turns per task, feeding an agent's own output back as
   the next prompt, only accepting success on a completion-marker match *and*
   real file changes on disk.
4. **Report** — a real `completed`/`partial`/`failed` status with exactly
   which tasks succeeded or failed.

## Command reference

| Command | What it does |
|---|---|
| `workflow build "<idea>"` | Build a project end-to-end from one prompt |
| `workflow doctor` | Full diagnostics: tools found, missing packages |
| `workflow providers` | List AI providers with health/status |
| `workflow agents` | List discovered desktop workers |
| `workflow login <provider>` | Configure a provider |
| `workflow environment` | Print detected environment |
| `workflow gui` | Launch the original interactive menu |

`workflow run` / `list` / `schedule` / `scan` / `plugins` / `reports` belong
to a **separate, secondary subsystem**: a generic YAML-workflow-and-plugin
automation engine (open an app, run a terminal command, git actions, browser
macros) for scripted desktop automation. It does not talk to the AI-dispatch
pipeline above — treat it as a distinct tool that happens to share this CLI.

## Known limitations

- **Electron-shell GUI capture doesn't work.** Claude Desktop, ChatGPT
  Desktop, and VS Code/Copilot all fail GUI-tier capture because Chromium
  disables its accessibility tree by default. This is confirmed, not an open
  bug. CLI-based tools and browser automation are the reliable paths.
- Desktop-GUI automation (`pywinauto`) is Windows-only; on macOS/Linux, use
  CLI-based workers or the browser transport.
- Real multi-worker parallelism depends on how many installed tools share
  overlapping skill tags — most single-machine setups run effectively
  single-worker even at larger project scales.

## Development

```bash
pip install -e ".[dev]"
pytest workflow_orchestrator/tests -x -q   # run from the repo root
```

## License

MIT
