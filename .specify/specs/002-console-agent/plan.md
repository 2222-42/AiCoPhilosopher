# Implementation Plan: Console Agent — Continuous Dialogue REPL

**Branch**: `002-console-agent` | **Date**: 2026-05-18 | **Spec**: `.specify/specs/002-console-agent/spec.md`
**Constitution**: `.specify/memory/constitution.md` v0.2.0

**Input**: Feature specification from `.specify/specs/002-console-agent/spec.md`

## Summary

The Console Agent transforms AiCoPhilosopher from a CLI-command-driven tool into a continuous dialogue REPL — an AI agent you converse with in natural language, not a tool you invoke with subcommands. The REPL wraps the existing Project Coordinator from 001-aicophilosopher with an interactive terminal interface supporting natural language intent classification, slash-command shortcuts, persistent session state, and async workstream awareness.

**Primary technical approach**:
- Python 3.11+ presentation layer added to existing Clean Architecture
- `prompt_toolkit` for interactive REPL input (history, completion, readline emulation)
- LLM-based NLU intent classification (cheap-tier model per cost-aware routing)
- Rich library for progressive disclosure rendering (collapsible panels, live status)
- SQLite session persistence (new tables per data-model.md, integrated with existing schema)
- Async workstream status surfacing via background thread + Rich Live display
- All domain entities defined as Pydantic v2 models (SessionState, DialogueTurn, etc.)

**Key design decisions** (detailed in research.md):
1. **REPL framework**: `prompt_toolkit` — provides readline history (FR-027), tab completion, and input handling
2. **NLU classification**: LLM-based (cheap tier) for MVP — flexible, no training data required
3. **Async updates**: Background thread polling + Rich Live status bar; updates queued during active input
4. **Session persistence**: Per-turn incremental writes to SQLite; graceful shutdown in single transaction
5. **Progressive disclosure**: Rich Panels with toggle state tracked in FocusContext

## Technical Context

**Language/Version**: Python 3.11+ (same as 001; async, typing.Self, match/case for intent routing)

**Primary Dependencies** (additions to 001 stack):
- **prompt_toolkit** (`prompt_toolkit>=3.0`): Interactive REPL with history, completion, syntax highlighting
- **Rich** (`rich>=13.0`): Already in 001 deps; extended for collapsible progressive disclosure panels and live status
- **aiosqlite** (`aiosqlite>=0.20`): Already in 001 deps for SQLite storage
- **Pydantic v2** (`pydantic>=2.7`): Already in 001 deps; all session entities defined as BaseModel

**Existing 001 dependencies leveraged**:
- LangGraph: Workstream execution continues via LangGraph checkpointing (REPL does NOT manage workstream lifecycle)
- LLM adapters (Claude/Gemini/Ollama): NLU classification routes through existing LLMPort
- StoragePort: Extended with session persistence methods (save_session, load_session, etc.)
- ChromaDB: PDF upload via `/upload` uses existing RAG pipeline
- PyMuPDF: PDF ingestion unchanged

**Storage**:
- **SQLite**: New tables — `sessions`, `dialogue_turns`, `context_blocks`, `approval_requests` (see data-model.md §3). Integrated into existing 001 SQLite schema with foreign keys to `projects`.
- **No new storage systems introduced**.

**Testing**:
- **pytest** + **pytest-asyncio**: Async REPL loop testing
- **pytest-mock**: Mock LLM responses for deterministic NLU tests
- **prompt_toolkit test utilities**: Simulate user input sequences
- **Coverage target**: 80% on new presentation-layer and domain-entity code

**Target Platform**: Linux/macOS/Windows terminal (same as 001; Rich + prompt_toolkit support all three)

**Project Type**: Feature addition to existing CLI application (presentation layer extension)

**Performance Goals**:
- First response latency (NLU + coordinator): ≤10 seconds (SC-001)
- Slash command execution: ≤5 seconds from Enter to acknowledgement (SC-006)
- 1000th turn latency: ≤30 seconds (SC-008)
- Session resume summary: ≤30 seconds from project selection (SC-005)
- NLU accuracy: ≥90% on 100-utterance test set (SC-002)

**Constraints**:
- **Offline-capable**: NLU can fall back to rule-based intent matching when LLM is unavailable
- **Memory**: <200MB additional peak memory (prompt_toolkit + session state)
- **Privacy**: Session dialogue history stored locally only; no telemetry (Constitution Principle I)
- **Concurrent sessions**: Exactly one active REPL session per project (FR-013)

**Scale/Scope**:
- Up to 5 active projects, 1 active REPL session each
- Session history: up to 10,000 dialogue turns per session (graceful degradation after 1,000 per SC-008)
- Context blocks: up to 100 per session
- Approval requests: up to 50 pending per session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status | Justification |
|-----------|-------|--------|---------------|
| **I. Core Independence & Local-First Privacy** | REPL wraps existing Project Coordinator; no new orchestration layers. All data local. | ✅ PASS | prompt_toolkit + Rich are local TUI libs. FR-026 mandates no external data transmission without consent. `external_search_consent` ApprovalRequest type gates all external calls. |
| **II. Intellectual Honesty** | Confidence scores mandatory; epistemic status always visible. | ✅ PASS | FR-007 mandates Epistemic Status in every response. EpistemicSnapshot in data model. `/dead-ends` preserves failed explorations. |
| **III. Code Quality** | PEP8, type annotations, Clean Architecture. | ✅ PASS | REPL is presentation-layer adapter wrapping application/domain. Pydantic v2 for all entities. Clean Architecture assumption added to spec. |
| **IV. Testing** | Automated tests; deterministic; mocks for LLM. | ✅ PASS | NLU accuracy test (SC-002). Session persistence testable (US2 scenarios). Concurrent session detection test (SC-009). Mock LLM for deterministic NLU tests. |
| **V. MVP-First** | P1 features only in MVP scope. | ✅ PASS | P1 = natural language + session persistence. P2 = slash commands + full inquiry cycle. Tab-completion deferred. Web UI deferred to 001 Phase 4. |

**Re-check after Phase 1**: Pending design completion.

## Project Structure

### Documentation (this feature)

```text
.specify/specs/002-console-agent/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command output)
├── data-model.md        # Phase 1 output (already created)
├── quickstart.md        # Phase 1 output (/speckit.plan command output)
├── contracts/           # Phase 1 output (/speckit.plan command output)
│   ├── repl-commands.md # Slash command reference (already created)
│   ├── nlu-intent-schema.md  # NLU intent types and entity schemas
│   └── repl-rendering.md     # Progressive disclosure output format contract
└── tasks.md             # Phase 2 output (/speckit.tasks command — NOT created by /speckit.plan)
```

### Source Code (repository root)

**Structure Decision**: Feature addition to existing single-project CLI application. The Console Agent REPL is a **presentation-layer extension** that wraps the existing Project Coordinator (`application/orchestration/coordinator.py`). All new domain entities (SessionState, DialogueTurn, ContextBlock, FocusContext, ApprovalRequest) live in `domain/entities/` alongside existing 001 entities. No new layers or infrastructure adapters required — the REPL uses existing `LLMPort` and `StoragePort`.

```text
src/aicophilosopher/
├── domain/
│   └── entities/
│       └── session.py              # NEW: SessionState, DialogueTurn, ContextBlock,
│                                   #      FocusContext, ApprovalRequest, UserIntent,
│                                   #      ActionTaken + all nested enums/models
├── application/
│   └── orchestration/
│       └── coordinator.py          # EXISTING: Project Coordinator (wrapped by REPL)
├── ports/
│   ├── llm_port.py                 # EXISTING: Used by NLU classifier
│   └── storage_port.py             # EXISTING: Extended with session persistence methods
├── presentation/
│   ├── __init__.py
│   ├── cli.py                      # EXISTING: CLI entry point (modified to launch REPL)
│   ├── commands.py                 # EXISTING: Click commands (retained for non-REPL use)
│   ├── repl.py                     # NEW: Main REPL loop (prompt_toolkit session)
│   ├── nlu.py                      # NEW: NLU intent classifier (LLM-based)
│   ├── slash_commands.py           # NEW: Slash command parser and router
│   ├── rendering.py                # NEW: Progressive disclosure Rich renderer
│   └── session_manager.py          # NEW: Session persistence (load/save/resume/reclaim)
├── infrastructure/
│   └── adapters/
│       └── sqlite_adapter.py       # EXISTING: Extended with session table CRUD

tests/
├── unit/
│   ├── domain/
│   │   └── test_session.py         # NEW: Session entity validation, state transitions
│   └── presentation/
│       ├── test_nlu.py             # NEW: NLU intent classification accuracy
│       ├── test_slash_commands.py  # NEW: Command parsing, routing, validation
│       ├── test_rendering.py       # NEW: Progressive disclosure output format
│       └── test_session_manager.py # NEW: Session CRUD, stale reclaim, concurrent detection
├── integration/
│   ├── test_repl_loop.py           # NEW: End-to-end REPL: input → NLU → coordinator → render
│   ├── test_session_persistence.py # NEW: Save/load/resume cycle with full state
│   └── test_workstream_surfacing.py # NEW: Async status updates in REPL
└── fixtures/
    ├── mock_nlu_responses/         # NEW: Pre-recorded LLM intent classifications
    └── test_sessions/              # NEW: Pre-built session states for resume testing

prompts/
└── nlu/
    └── intent_classifier.md        # NEW: System prompt for NLU intent classification
```

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. All architectural decisions are justified by the specification and constitution principles.

**Design notes**:
- NLU classification uses cheap-tier LLM (Constitution §3.5 cost-aware routing). No new model tier introduced.
- Session entities are pure Pydantic models in `domain/` with zero external dependencies.
- REPL delegates all workstream operations to existing 001 Project Coordinator — no duplication of orchestration logic.
- prompt_toolkit is the single new significant dependency; it is pure Python, well-maintained, and widely used.

## Phases

### Phase 0: Outline & Research

**Output**: `.specify/specs/002-console-agent/research.md`

All technical unknowns resolved. See `research.md` for detailed decisions, rationales, and alternatives considered.

**Summary of Phase 0 decisions**:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| REPL Input Framework | **prompt_toolkit** | Native readline emulation (FR-027: up/down/Ctrl+R), tab completion, cross-platform. Rich Prompt lacks full history search. |
| NLU Classification | **LLM-based (cheap tier)** | Flexible, no training data. Post-MVP: fine-tune on collected dialogue. Falls back to rule-based when offline. |
| Async Status Updates | **Background thread + Rich Live** | Polls workstream status every 2s. Updates queued during active input. Non-blocking. |
| Session Persistence | **Per-turn incremental SQLite** | FR-009: persist before rendering next response. Graceful exit in single transaction. Crash recovery from last persisted turn. |
| Command History | **prompt_toolkit history** | File-backed, per-session. Persisted as part of session state (FR-027). |
| Progressive Disclosure | **Rich Panel + toggle state** | [Summary] + [Epistemic Status] + [Active Workstreams] always visible. [Details]/[Suggestions] toggled via `/details` `/suggestions`. |
| Tab Completion | **Deferred to post-MVP** | prompt_toolkit supports it natively. Deferred per open question #4 in checklist. |
| NLU Confidence Threshold | **0.85** (configurable) | FR-004 default. Below threshold → clarifying question. |

### Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete

**Output**: `data-model.md`, `/contracts/`, `quickstart.md`

#### 1.1 Data Model (`data-model.md`)

See `.specify/specs/002-console-agent/data-model.md` for complete entity definitions, field specifications, relationships, validation rules, SQLite schema extensions, and key invariants.

**Key entities** (7 new domain entities):
- `SessionState` (root aggregate for REPL session)
- `DialogueTurn` (user/coordinator/system turn with intent/actions)
- `ContextBlock` (thematic grouping of turns with epistemic snapshot)
- `FocusContext` (coordinator's current attention window)
- `ApprovalRequest` (pending decision requiring user input)
- `UserIntent` (parsed NLU classification result)
- `ActionTaken` (coordinator action record)

#### 1.2 Interface Contracts (`/contracts/`)

See `.specify/specs/002-console-agent/contracts/` for interface specifications.

**Contracts defined**:
- `repl-commands.md`: All 28 slash commands grouped by category (Session, Inquiry, Steering, View, Export, Help/Config)
- `nlu-intent-schema.md`: 16 intent types with entity schemas, confidence thresholds, and clarification logic
- `repl-rendering.md`: Progressive disclosure output format with Section anchors and toggle behavior

#### 1.3 Quickstart (`quickstart.md`)

See `.specify/specs/002-console-agent/quickstart.md` for development environment setup, REPL launch instructions, and testing procedures.

#### 1.4 Agent Context Update

Update `.github/copilot-instructions.md` between `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers to reference the Console Agent implementation plan.

### Phase 2: Task Breakdown (Future `/speckit.tasks`)

Not created by `/speckit.plan`. The plan ends here. The next step is `/speckit.tasks` to generate `tasks.md` with actionable implementation tasks organized by user story and dependency order.

---

**Plan Version**: 1.0.0 | **Last Updated**: 2026-05-18 | **Status**: Phase 0 & Phase 1 In Progress
