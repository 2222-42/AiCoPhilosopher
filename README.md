# AI Co-Philosopher

A stateful, hierarchical multi-agent workbench for philosophical research, inspired by Google DeepMind's *AI Co-Mathematician* (arXiv:2605.06651v1, 2026).

The AI Co-Philosopher is **not** a chatbot. It is a collaborative research environment where multiple specialized AI agents work together to clarify philosophical questions, search literature, analyze concepts, reconstruct arguments, detect fallacies, synthesize findings, and compare ideas across analytic, continental, pragmatic, philosophy of technology/science/mathematics, software architecture, and model theory traditions.

## Quickstart

```bash
git clone https://github.com/2222-42/AiCoPhilosopher.git
cd AiCoPhilosopher
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
aicophilosopher new project "What is abstraction?"
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup and a guided tutorial.

## Core Design Principles

| Principle | Description |
|-----------|-------------|
| **Embrace philosophy beyond arguments** | Conceptual clarification, phenomenological description, thought experiments, cross-traditional dialogue |
| **Dialectical refinement of inquiry** | Socratic clarification until the inquiry is sufficiently refined |
| **Native philosophical artifacts** | Living working paper with margin annotations, conceptual genealogy, dialectical history |
| **Async investigation with steering** | Heavy workstreams run in parallel; user can steer, intervene, or redirect at any time |
| **Progressive disclosure** | Summaries first; detailed argument maps and source analyses on demand |
| **Uncertainty tracking** | Every claim carries confidence scores, counter-argument strength, tradition-specific validity |
| **Preserve dead ends** | Failed hypotheses and refuted arguments are first-class project history |

## Architecture

```
User
↓ (CLI + steering commands)
Project Coordinator Agent
↓ (delegates via message protocol)
Workstream Coordinators
├── Literature Search Agent
├── Concept Analysis Agent
├── Argumentation Agent
├── Critical Review Agent
├── Cross-Traditional Comparison Agent
└── Synthesis Agent
```

Implemented in **Python 3.11+** following Clean Architecture (Ports & Adapters):
- `domain/` — Pure business logic (zero external dependencies)
- `application/` — Agent orchestration and use cases
- `ports/` — Abstract interfaces (LLMPort, StoragePort, etc.)
- `infrastructure/adapters/` — Concrete implementations (SQLite, ChromaDB, LLM backends)
- `presentation/` — CLI with Rich-based terminal UI

## Features

- **Socratic Clarification**: Refine vague questions through dialectical dialogue
- **Literature Search**: Cross-domain search with tradition tagging and bridge notes
- **Concept Analysis**: Necessary/sufficient conditions, distinction mapping, thought experiments
- **Argument Reconstruction**: Standard-form arguments with competing positions
- **Critical Review**: Fallacy detection, validity/soundness evaluation, adversarial review
- **Synthesis**: Merge workstream outputs into a coherent living document
- **Cross-Traditional Comparison**: Bridge concepts and flag incommensurabilities
- **Local-first & Private**: All data stored locally; no external transmission without consent

## CLI Commands

```
new project <title>          Start a new research project
refine goal                   Enter Socratic clarification dialogue
start workstream <type>       Launch a workstream (literature_search, concept_analysis,
                              argumentation, critical_review, cross_traditional, synthesis)
pause/resume <id>             Control workstream execution
status                        View epistemic overview
show document                 Display the living document
show hypotheses               View hypothesis history with status
show dead ends                View failed explorations (Constitution II)
add note <text>               Attach notes to the workspace
compare traditions <topic>    Cross-traditional comparison
export [markdown|html|latex]  Export the living document
```

## Development

```bash
make check        # Run all checks (lint + typecheck + test)
make test         # Run tests
make test-cov     # Run tests with coverage
make lint         # Run ruff
make format       # Auto-format code
make typecheck    # Run mypy
```

## Constitution

The project is governed by a [constitution](.specify/memory/constitution.md) with five core principles:

1. **Core Independence & Local-First Privacy** — fully self-contained, no external orchestration dependencies
2. **Philosophical Accuracy & Intellectual Honesty** — confidence scores, dead-end preservation, user approval gates
3. **Code Quality & Maintainability** — PEP8, type annotations, docstrings, modular components
4. **Testing Standards & Determinism** — automated tests, no network requirement, regression tests
5. **MVP-First Delivery** — working product before perfection

## License

MIT
