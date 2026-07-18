# QUICKSTART

Get the AI Co-Philosopher running in under 5 minutes.

## Prerequisites

- Python 3.11 or later
- pip

## Installation

```bash
git clone https://github.com/2222-42/AiCoPhilosopher.git
cd AiCoPhilosopher
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows
pip install -e ".[dev]"
```

Verify installation:

```bash
aicophilosopher --help
python -c "import aicophilosopher; print(aicophilosopher.__version__)"
```

## First Project

### 1. Create a project

```bash
aicophilosopher new-project "What is the nature of abstraction?"
```

This creates a persistent workspace under `projects/<project_id>/`.

### 2. Refine your question

```bash
aicophilosopher refine-goal
```

The Project Coordinator Agent will engage in Socratic dialogue to clarify your question across philosophical traditions. Respond to its questions until the goal is approved.

### 3. Launch workstreams

```bash
aicophilosopher start-workstream literature_search -t "analytic,continental,philosophy_of_technology"
aicophilosopher start-workstream concept_analysis
aicophilosopher start-workstream argumentation
```

### 4. Monitor progress

```bash
aicophilosopher status
aicophilosopher show-document
```

### 5. Review and steer

```bash
aicophilosopher show-hypotheses
aicophilosopher show-dead-ends
aicophilosopher steer <workstream_id> "deepen analysis on abstraction layers"
```

### 6. Export

```bash
aicophilosopher export markdown
aicophilosopher export html
```

## Running Offline

The AI Co-Philosopher operates fully offline by default. External literature APIs are gated by `AICOPH_ALLOW_EXTERNAL_SEARCH` (default: `false`).

```bash
export AICOPH_ALLOW_EXTERNAL_SEARCH=false
aicophilosopher new-project "What is truth?"
```

All core features (argumentation, concept analysis, critical review, synthesis) work without network access.

**Literature sources today:**
- **Live** (when `AICOPH_ALLOW_EXTERNAL_SEARCH=true`): Semantic Scholar, arXiv
- **Stub** (not connected; no fabricated results/URLs): PhilPapers, SEP
- **Unimplemented**: IEP

## Configuration

Create a `.env` file in the project root (settings use the `AICOPH_` prefix):

```env
# LLM backend (optional; heuristic mode works without LLM)
AICOPH_LLM_BACKEND=ollama              # ollama | claude | gemini
AICOPH_LLM_MODEL=llama3                # model name

# Storage
AICOPH_WORKSPACE_DIR=./projects        # where project data lives

# Privacy / external search
# false (default): offline placeholders only
# true: enable live Semantic Scholar + arXiv (query terms only)
# PhilPapers / SEP remain stubs either way — they are not live APIs yet.
AICOPH_ALLOW_EXTERNAL_SEARCH=false
AICOPH_LOG_LEVEL=INFO                  # DEBUG | INFO | WARNING | ERROR
```

## Running Tests

```bash
make test           # run all tests
make test-cov       # with coverage report
make check          # lint + typecheck + test
```

## Next Steps

- Read the [full tutorial](docs/usage.md) for a guided walkthrough
- Explore the [architecture](.specify/specs/001-aicophilosopher/spec.md)
- Review the [constitution](.specify/memory/constitution.md) for design principles
