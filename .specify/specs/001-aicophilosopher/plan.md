# Implementation Plan: AiCoPhilosopher v2.0

**Branch**: `feat/specify/init` | **Date**: 2026-05-13 | **Spec**: `.specify/specs/001-aicophilosopher/spec.md`

**Input**: Feature specification from `.specify/specs/001-aicophilosopher/spec.md`

## Summary

AiCoPhilosopher v2.0 is a stateful, hierarchical multi-agent workbench for philosophical research, designed as a philosophical analog to Google DeepMind's AI Co-Mathematician. The system provides an interactive, asynchronous workspace where a Project Coordinator Agent delegates complex tasks across parallel workstreams, enabling users to direct and interact with an evolving philosophical research process.

**Primary technical approach**:
- Python 3.11+ with LangGraph as the core orchestration framework
- Pydantic v2 for all state schemas and message validation
- Local-first architecture: SQLite (metadata) + filesystem (documents) + ChromaDB (vector RAG)
- Rich + Click for the terminal-based progressive-disclosure interface
- Modular agent hierarchy with standardized JSON message protocol over shared filesystem

**Key technical differentiators**:
1. **Philosophical Reasoning Engine**: Dedicated logic engine for validity checking, contradiction detection, and tradition-specific norm enforcement
2. **Uncertainty Lifecycle Management**: First-class uncertainty tracking with confidence scores, counter-argument strength, tradition validity maps, and explicit review status
3. **Dialectical History Preservation**: All refuted hypotheses, abandoned arguments, and failed explorations retained as permanent project artifacts
4. **Cross-Traditional Comparison Engine**: Prevents category colonization by evaluating arguments within native methodological frameworks before bridging

## Technical Context

**Language/Version**: Python 3.11+ (requires `typing.Self`, improved `TypedDict`, and async features)

**Primary Dependencies**:
- **LangGraph** (`langgraph>=0.2.0`): Stateful multi-agent graph orchestration, checkpointing, and human-in-the-loop breakpoints
- **Pydantic v2** (`pydantic>=2.7`): All state schemas, message validation, configuration management
- **ChromaDB** (`chromadb>=0.5.0`): Local vector database for RAG over uploaded papers with metadata filtering by tradition
- **Rich** (`rich>=13.0`): Terminal UI with progress tracking, collapsible panels, syntax highlighting for Markdown
- **Click** (`click>=8.0`): CLI command parsing and steering command interface
- **PyMuPDF** (`PyMuPDF>=1.24`): PDF text extraction and metadata extraction for local RAG
- **Z3-Solver** (`z3-solver>=4.13`): Formal satisfiability checking for argument validity (MVP); Prolog bridge skeleton for post-MVP
- **Anthropic/Gemini/Ollama SDKs**: LLM backend adapters (Claude 3.5 Sonnet, Gemini 1.5 Pro, local Ollama)

**Storage**:
- **SQLite** (`aiosqlite>=0.20`): Project metadata, workstream state, message queue, uncertainty registry
- **Local Filesystem**: Living document (Markdown), workstream reports, dialectical history (JSONL), artifacts
- **ChromaDB**: Vector embeddings for RAG with collection-per-project isolation

**Testing**:
- **pytest** + **pytest-asyncio**: Core test framework for async agent orchestration
- **pytest-mock**: External service mocking (LLM APIs, search APIs)
- **hypothesis**: Property-based testing for state transition invariants
- **coverage.py**: Coverage measurement with 80% minimum threshold for core logic

**Target Platform**: Linux/macOS/Windows (CLI application); future web UI via Gradio/Streamlit

**Project Type**: CLI application with reusable library core (importable `aicophilosopher` package)

**Performance Goals**:
- Workstream status reflection latency: <30 seconds (AC-007)
- Hypothesis history retrieval: <5 seconds (AC-008)
- Clarification dialogue to approved goal: ≤5 turns, ≤10 minutes (AC-001)
- Single workstream review round: <5 minutes (2 reviewer agents × 2.5 min each)
- PDF ingestion for RAG: <30 seconds per 50-page document

**Constraints**:
- **Offline-capable core**: All core features operational without internet after initial setup (AC-009)
- **Memory**: <500MB peak memory for CLI with 5 concurrent workstreams
- **Privacy**: Zero automatic external data transmission; explicit per-request consent required
- **Local-first**: All user data stored in `~/.aicophilosopher/` or user-specified directory

**Scale/Scope**:
- Single-user philosophical research workbench
- Up to 10 concurrent workstreams per project
- Up to 5 active projects
- Document size: living documents up to 100k words; RAG corpus up to 10k papers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status | Justification (if needed) |
|-----------|-------|--------|---------------------------|
| **I. Core Independence & Local-First Privacy** | No hard dependency on external orchestration layers; all data local by default; explicit consent for external APIs | ✅ PASS | LangGraph runs entirely locally. External layers (Hermes, OpenCode Go) connected via optional ExternalAgentBridge. Search APIs require explicit user consent per spec §4.2. |
| **II. Philosophical Accuracy & Intellectual Honesty** | Confidence scores mandatory; user final approval gate; complete hypothesis history preserved; uncertainty explicitly tracked | ✅ PASS | UncertaintyRegistry schema enforces confidence/counter-argument/review-status fields. Synthesis Agent requires user approval before permanent document updates. DialecticalHistory preserves all refutations. |
| **III. Code Quality & Maintainability** | PEP8 compliance; type annotations; docstrings; modular components | ✅ PASS | Pydantic v2 enforces type safety. Project structure separates concerns (agents/, reasoning/, artifacts/, tools/, interfaces/). pytest + mypy in CI pipeline. |
| **IV. Testing Standards & Determinism** | Automated test coverage; deterministic tests; mocks for external services; regression tests for bug fixes | ✅ PASS | pytest with asyncio support. All LLM calls mocked in core test suite. Hypothesis library for state invariant testing. 80% coverage gate. |
| **V. MVP-First Delivery & Continuous Improvement** | MVP scope clearly bounded; non-essential features deferred; documented usage instructions | ✅ PASS | MVP explicitly excludes Phenomenological Description Agent (full), Ethical Analysis Agent (full), LaTeX export, formal prover integration, web UI. Focus on Coordinator + Literature Search + Concept Analysis + Argumentation + Critical Review + Synthesis + Cross-Traditional Comparison. |

**Re-check after Phase 1**: All gates still pass. No complexity violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
.specify/specs/001-aicophilosopher/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── cli-commands.md
│   ├── message-protocol.md
│   └── external-bridge.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

**Structure Decision**: Single project (Option 1) — CLI application with library core. The `aicophilosopher` package is designed to be importable for future web UI or programmatic usage.

```text
src/
├── aicophilosopher/
│   ├── __init__.py
│   ├── __main__.py              # Entry point: python -m aicophilosopher
│   ├── version.py               # Semantic versioning
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py            # Pydantic state schemas (ProjectState, WorkstreamState, etc.)
│   │   ├── workspace.py         # WorkspaceManager: thread-safe/async-safe file/DB operations
│   │   ├── config.py            # Pydantic-settings based configuration
│   │   └── exceptions.py        # Domain-specific exceptions
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py              # BaseAgent: shared LLM client, logging, tool access
│   │   ├── coordinator.py       # ProjectCoordinatorAgent: user-facing, dialogue, steering
│   │   ├── workstream_coordinator.py  # WorkstreamCoordinatorAgent: manages sub-agent sequences
│   │   ├── literature_search.py # LiteratureSearchAgent: multi-database querying, tradition bridging
│   │   ├── concept_analysis.py  # ConceptAnalysisAgent: distinction mapping, genealogy, thought experiments
│   │   ├── cross_traditional.py # CrossTraditionalComparisonAgent: bridge concepts, incommensurability
│   │   ├── argumentation.py     # ArgumentationAgent: standard form, competing positions, implicit premises
│   │   ├── critical_review.py   # CriticalReviewAgent: fallacy detection, adversarial review
│   │   ├── phenomenological.py  # PhenomenologicalDescriptionAgent: POST-MVP skeleton
│   │   ├── ethical_analysis.py  # EthicalAnalysisAgent: POST-MVP skeleton
│   │   └── synthesis.py         # SynthesisAgent: living document generation, margin annotations
│   ├── reasoning/
│   │   ├── __init__.py
│   │   ├── logic_engine.py      # Formal validity, contradiction detection, Z3 integration
│   │   ├── tradition_manager.py # Tradition profiles, norm enforcement, incommensurability detection
│   │   └── uncertainty.py       # Uncertainty lifecycle: track, manage, communicate
│   ├── artifacts/
│   │   ├── __init__.py
│   │   ├── living_document.py   # Markdown generation, YAML frontmatter, annotation embedding
│   │   ├── review_process.py    # Multi-agent review orchestration, round management, escalation
│   │   └── document_parser.py   # Markdown/YAML parsing, annotation extraction
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py          # ToolRegistry: plugin-style tool registration
│   │   ├── search.py            # PhilPapers, SEP, IEP, arXiv, Semantic Scholar adapters
│   │   ├── pdf_rag.py           # PDF ingestion, chunking, ChromaDB indexing (local only)
│   │   └── code_execution.py    # Python sandbox (RestrictedPython), Prolog skeleton
│   ├── interfaces/
│   │   ├── __init__.py
│   │   ├── cli.py               # Rich-based terminal UI, progressive disclosure, command loop
│   │   ├── commands.py          # Click command definitions for steering
│   │   └── external_bridge.py   # ExternalAgentBridge: Hermes/OpenCode Go adapter with fallback
│   ├── messaging/
│   │   ├── __init__.py
│   │   ├── protocol.py          # JSON message schema, validation, routing
│   │   └── queue.py             # SQLite-backed message queue for async agent communication
│   └── persistence/
│       ├── __init__.py
│       ├── sqlite_store.py      # SQLite operations: projects, workstreams, messages, uncertainty
│       └── vector_store.py      # ChromaDB wrapper with tradition-aware metadata filtering
├── tests/
│   ├── conftest.py              # Shared fixtures: mock LLM client, temp workspace, test project
│   ├── unit/
│   │   ├── test_models.py       # State schema validation, serialization
│   │   ├── test_workspace.py    # WorkspaceManager operations
│   │   ├── test_logic_engine.py # Validity, contradiction detection
│   │   ├── test_tradition_manager.py  # Tradition norm enforcement
│   │   ├── test_uncertainty.py  # Uncertainty lifecycle transitions
│   │   ├── test_living_document.py    # Markdown generation, annotation parsing
│   │   ├── test_review_process.py     # Review round orchestration
│   │   └── test_messaging.py    # Message protocol, queue operations
│   ├── integration/
│   │   ├── test_coordinator.py  # End-to-end clarification dialogue → workstream creation
│   │   ├── test_literature_search.py  # Mocked search → structured bibliography
│   │   ├── test_workstream_lifecycle.py  # Create → run → pause → resume → complete
│   │   └── test_synthesis.py    # Multi-workstream → living document with annotations
│   └── fixtures/
│       ├── sample_papers/       # Mock PDFs for RAG testing
│       ├── mock_llm_responses/  # Pre-recorded LLM outputs for deterministic tests
│       └── test_projects/       # Pre-configured project states for integration tests
├── prompts/
│   ├── coordinator/             # Project Coordinator system prompts
│   ├── workstream/              # Workstream Coordinator prompts
│   ├── agent/                   # Per-agent role prompts (literature, concept, argument, etc.)
│   └── review/                  # Reviewer agent prompts with methodological frameworks
├── docs/
│   └── usage.md                 # User-facing documentation (post-MVP)
├── pyproject.toml               # Modern Python packaging, dependencies, tool configs
├── README.md
└── Makefile                     # Common dev tasks: test, lint, format, typecheck
```

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. All architectural decisions are justified by the specification and constitution principles.

## Phases

### Phase 0: Outline & Research

**Output**: `.specify/specs/001-aicophilosopher/research.md`

All technical unknowns resolved. See `research.md` for detailed decisions, rationales, and alternatives considered.

**Summary of Phase 0 decisions**:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration Framework | **LangGraph** | Native stateful graph execution, checkpointing, human-in-the-loop breakpoints, Pydantic v2 integration. AutoGen is too conversational; custom framework violates MVP-first principle. |
| Vector Database | **ChromaDB** (MVP), LanceDB (future) | File-based persistence, simple Python API, metadata filtering (critical for tradition tags). LanceDB offers better performance at scale but adds complexity. |
| LLM Abstraction | **Custom adapter** (not LiteLLM) | Only 3 backends needed (Claude, Gemini, Ollama). LiteLLM adds dependency overhead and potential privacy concerns. Custom adapter follows Adapter Pattern and keeps core independent. |
| PDF Processing | **PyMuPDF** | Fastest extraction, robust metadata handling, permissive license. pdfplumber is slower for large documents. |
| CLI Framework | **Rich + Click** | Rich provides progressive disclosure UI (collapsible panels, syntax highlighting). Click provides robust CLI parsing. Textual is overkill for MVP. |
| Formal Logic Engine | **Z3** (MVP), Prolog skeleton | Z3 has excellent Python bindings for basic SAT/SMT checking needed for argument validity. Lean4 is too heavy for MVP; Prolog adds symbolic reasoning for post-MVP. |
| Message Transport | **Shared filesystem + SQLite queue** | Mirrors Co-Mathematician design. Zero network overhead, fully debuggable, naturally local-first. gRPC/MQTT would introduce unnecessary complexity and network dependencies. |
| State Persistence | **LangGraph checkpointing + SQLite** | LangGraph's built-in checkpointing handles graph state. SQLite stores messages, metadata, and uncertainty registry. File system stores documents and artifacts. |
| Review Algorithm | **Iterative multi-reviewer with round limits** | 2 reviewer agents minimum, max 5 rounds, automatic escalation to Project Coordinator on non-termination. Prevents "death spiral" while ensuring rigor. |
| Tradition Representation | **JSON profile files + runtime registry** | Tradition assumptions, methodological norms, and evaluative criteria stored as structured JSON. Enables user-extensible tradition modules without code changes. |

### Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete

**Output**: `data-model.md`, `/contracts/`, `quickstart.md`

#### 1.1 Data Model (`data-model.md`)

See `.specify/specs/001-aicophilosopher/data-model.md` for complete entity definitions, field specifications, relationships, validation rules, and state transition diagrams.

**Key entities**:
- `ProjectState` (root aggregate)
- `WorkstreamState` (child aggregate, lifecycle: pending → running → paused → completed/failed/stalled)
- `HypothesisRecord` (immutable history, status transitions)
- `UncertaintyRecord` (confidence, counter-argument strength, tradition validity, review status)
- `DialecticalMove` (argument, refutation, revision, abandonment)
- `ConceptNode` (conceptual genealogy tree)
- `ReviewRound` (reviewer assignments, verdicts, escalation flags)
- `Message` (JSON protocol envelope)

#### 1.2 Interface Contracts (`/contracts/`)

See `.specify/specs/001-aicophilosopher/contracts/` for interface specifications.

**Contracts defined**:
- `cli-commands.md`: All steering commands, arguments, and return formats
- `message-protocol.md`: JSON schema for inter-agent communication
- `external-bridge.md`: Adapter interface for Hermes Agent / OpenCode Go integration

#### 1.3 Quickstart (`quickstart.md`)

See `.specify/specs/001-aicophilosopher/quickstart.md` for development environment setup, dependency installation, and MVP execution instructions.

#### 1.4 Agent Context Update

Updated `.github/copilot-instructions.md` between `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers to reference the implementation plan.

### Phase 2: Task Breakdown (Future `/speckit.tasks`)

Not created by `/speckit.plan`. The plan ends here. The next step is `/speckit.tasks` to generate `tasks.md` with actionable implementation tasks organized by user story and dependency order.

---

**Plan Version**: 1.0.0 | **Last Updated**: 2026-05-13 | **Status**: Phase 0 & Phase 1 Complete
