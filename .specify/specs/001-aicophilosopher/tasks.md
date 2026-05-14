# Tasks: AiCoPhilosopher v2.0

**Input**: Design documents from `.specify/specs/001-aicophilosopher/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`

**Tests**: Tests are included per the specification's explicit acceptance criteria (AC-001 through AC-010).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T-001 [DONE] [P] [Setup] Create project directory structure per plan.md at `src/aicophilosopher/` with Clean Architecture layers (`domain/`, `application/`, `ports/`, `infrastructure/adapters/`, `presentation/`)
  - **AC**: `tree src/aicophilosopher/` shows all 5 layers; `__init__.py` files present in each; `scripts/check_domain_purity.py` passes

- [x] T-002 [DONE] [P] [Setup] Initialize `pyproject.toml` with Python 3.11+ requirement, core dependencies (langgraph>=0.2.0, pydantic>=2.7, chromadb>=0.5.0, rich>=13.0, click>=8.0, PyMuPDF>=1.24, z3-solver>=4.13, anthropic, google-generativeai, ollama, aiosqlite>=0.20), and dev dependencies (pytest, pytest-asyncio, pytest-mock, hypothesis, coverage, ruff, mypy)
  - **AC**: `pip install -e ".[dev]"` succeeds in clean venv; `python -c "import aicophilosopher"` works

- [x] T-003 [DONE] [P] [Setup] Configure linting/formatting/type checking: `ruff` for lint+format, `mypy` for type checking, `pytest` with asyncio plugin in `pyproject.toml` tool sections
  - **AC**: `ruff check src/` passes on empty structure; `mypy src/aicophilosopher` passes; `pytest --collect-only` works

- [x] T-004 [DONE] [Setup] Create `Makefile` with targets: `test`, `test-cov`, `lint`, `format`, `typecheck`, `check` (runs all)
  - **AC**: `make check` runs without error on empty project

- [x] T-005 [DONE] [P] [Setup] Update `.gitignore` for Python project (venv, `__pycache__`, `.env`, `*.egg-info`, `.coverage`, ChromaDB data dirs, workspace dirs)
  - **AC**: `git status` shows no untracked build artifacts after `pip install -e ".[dev]"`

---

## Phase 1.5: Architecture Skeleton (Clean Architecture / Ports & Adapters)

**Purpose**: Establish the layered directory structure and dependency-injection wiring before any domain logic is written. Enforces the "inward-only" dependency rule from day one.

**⚠️ CRITICAL**: No domain logic or adapter implementation can begin until this skeleton passes lint and type checks.

- [x] T-006 [DONE] [P] [Setup] Create Clean Architecture directory skeleton at `src/aicophilosopher/`: `domain/` (entities/, value_objects/, services/), `application/` (orchestration/, use_cases/), `ports/` (llm_port.py, storage_port.py, reviewer_port.py, dialectical_history_port.py, search_port.py), `infrastructure/adapters/` (gemini_adapter.py, claude_adapter.py, ollama_adapter.py, sqlite_adapter.py, chroma_adapter.py, filesystem_adapter.py), `presentation/` (cli.py, commands.py)
  - **AC**: `tree src/aicophilosopher/` shows all 5 layers; every package has `__init__.py`; no Python files contain implementation code yet (only docstrings / pass / `raise NotImplementedError`)
  - **Depends on**: T-001, T-002

- [x] T-007 [DONE] [P] [Setup] Define all Port interfaces in `src/aicophilosopher/ports/` using `typing.Protocol` with full type annotations and docstrings: `LLMPort` (generate, embed), `StoragePort` (save_project, load_project, query_uncertainty), `ReviewerPort` (request_review, submit_verdict), `DialecticalHistoryPort` (append_move, query_history), `SearchPort` (query_philpapers, query_sep)
  - **AC**: Each protocol can be imported without errors; `mypy --strict src/aicophilosopher/ports/` passes; a mock implementation satisfies the protocol (verified by `mypy`)
  - **Depends on**: T-006

- [x] T-008 [DONE] [Setup] Implement DI container skeleton in `src/aicophilosopher/container.py`: lightweight `Container` class that reads backend config from `core/config.py`, instantiates the correct Adapter for each Port, and allows one-line adapter swap for testing (e.g., `container.register(StoragePort, FakeStorageAdapter)`)
  - **AC**: `python -c "from aicophilosopher.container import Container; c = Container(); c.resolve('LLMPort')"` raises `NotImplementedError` (no adapter bound yet); `c.register(LLMPort, FakeLLMAdapter); c.resolve(LLMPort)` returns `FakeLLMAdapter` instance; no circular imports
  - **Depends on**: T-007, T-012

- [x] T-009 [DONE] [P] [Setup] Configure `ruff` circular-import detection and add `scripts/check_domain_purity.py` that verifies every `.py` file under `domain/` imports only stdlib + `pydantic` (no LangGraph, no ChromaDB, no SDKs)
  - **AC**: `ruff check src/aicophilosopher` passes on the skeleton; `python scripts/check_domain_purity.py` passes; `mypy --strict src/aicophilosopher` passes; `pyright src/aicophilosopher` passes (if pyright is configured)
  - **Depends on**: T-003, T-006

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### 2.1 Core Models & Schemas

- [x] T-010 [DONE] [P] [Foundation] Implement Pydantic v2 domain entities in `src/aicophilosopher/domain/entities/`: `ProjectState`, `WorkstreamState`, `HypothesisRecord`, `UncertaintyRecord`, `DialecticalMove`, `ConceptNode`, `ReviewRound`, `Message`, `GoalStatement`, `Artifact`, `ProgressUpdate`, `FailedExploration`, `Note` with all enums (`WorkstreamType`, `WorkstreamStatus`, `HypothesisStrength`, `Origin`, `HypothesisStatus`, `ReviewStatus`, `DialecticalMoveType`, `MessageType`, `ArtifactType`, `ReviewerVerdictStatus`, `ReviewRoundStatus`, `ProjectStatus`)
  - **AC**: All entities validate correctly with sample data; enums restrict values; `confidence_score` bounds (0.0–1.0) enforced; `ProjectState` includes `status: ProjectStatus` field; `Note` entity supports `--attach-to` option from CLI contract
  - **Depends on**: T-002

- [x] T-011 [DONE] [Foundation] Implement `src/aicophilosopher/domain/exceptions.py` with domain-specific exceptions: `AICoPhilosopherError`, `WorkstreamError`, `ReviewDeadlockError`, `IncommensurabilityError`, `ExternalLayerError`, `ValidationError`, `ConfigurationError`
  - **AC**: Each exception can be raised/caught; `ReviewDeadlockError` carries `workstream_id` and `round_number`

- [x] T-012 [DONE] [Foundation] Implement `src/aicophilosopher/domain/services/config.py` using `pydantic-settings` for environment-based configuration: LLM backends, privacy settings, external layer toggles, workspace directory, log level
  - **AC**: `Config()` loads from `.env`; `Config(llm_backend="ollama")` overrides; validation rejects unknown backends
  - **Depends on**: T-010

### 2.2 Persistence Layer

- [x] T-013 [DONE] [Foundation] Implement SQLite StoragePort adapter in `src/aicophilosopher/infrastructure/adapters/sqlite_adapter.py`: `SQLiteAdapter` class implementing `StoragePort` with methods for CRUD on projects, workstreams, hypotheses, uncertainty registry, messages, review rounds, artifacts, notes
  - **AC**: All tables from `data-model.md` §3.1 created; `notes` table added; foreign keys enforced; indexes functional; async `aiosqlite` operations work; `StoragePort` interface satisfied
  - **Depends on**: T-010, T-011

- [x] T-014 [DONE] [P] [Foundation] Implement `src/aicophilosopher/infrastructure/adapters/chroma_adapter.py`: `ChromaAdapter` implementing SearchPort's vector retrieval methods with `create_collection`, `add_documents`, `query` with tradition-aware `where` filtering, collection-per-project isolation
  - **AC**: `ChromaAdapter.query("free will", where={"tradition": "analytic_philosophy"})` returns filtered results; collections isolated by project ID; `SearchPort` interface satisfied
  - **Depends on**: T-002

### 2.3 Workspace & File System

- [x] T-015 [DONE] [Foundation] Implement `src/aicophilosopher/infrastructure/adapters/filesystem_adapter.py`: `FileSystemAdapter` implementing `StoragePort` with async-safe methods for creating project directories, reading/writing living documents, workstream reports, hypotheses JSONL (derived export), dialectical history JSONL (derived export), margin notes, uncertainty registry JSON, and notes
  - **AC**: `FileSystemAdapter.create_project("Test")` creates full directory tree; concurrent writes to different project files do not corrupt; `living_document.md` round-trips with YAML frontmatter intact; `StoragePort` interface satisfied; SQLite is authoritative source; JSONL files are derived exports
  - **Depends on**: T-010, T-012

### 2.4 Messaging Protocol

- [x] T-016 [DONE] [Foundation] Implement `src/aicophilosopher/domain/entities/message.py`: Pydantic models for all 12 message types (`status_update`, `delegation_request`, `delegation_response`, `steering_command`, `steering_ack`, `help_request`, `help_response`, `review_request`, `review_response`, `result_delivery`, `error_notification`, `user_notification`) with payload schemas per `contracts/message-protocol.md`
  - **AC**: All message types validate with sample payloads; `MessageType` enum restricts values; `correlation_id` linking works
  - **Depends on**: T-010

- [x] T-017 [DONE] [Foundation] Implement `src/aicophilosopher/infrastructure/adapters/message_queue_adapter.py`: `MessageQueueAdapter` implementing `MessagePort` backed by SQLite with `enqueue`, `dequeue`, `poll_inbox(agent_id)`, `broadcast`, and message retention policies
  - **AC**: Messages enqueue/dequeue correctly; `poll_inbox("project_coordinator")` returns only messages for that agent; broadcast creates copies for all active agents; retention policy archives old messages; `MessagePort` interface satisfied
  - **Depends on**: T-013, T-016

### 2.5 LLM Backend & Tool Registry

- [x] T-018 [DONE] [Foundation] Define `LLMPort` in `src/aicophilosopher/ports/llm_port.py` (Protocol) and implement `ClaudeBackend`, `GeminiBackend`, `OllamaBackend` in `src/aicophilosopher/infrastructure/adapters/` (`claude_adapter.py`, `gemini_adapter.py`, `ollama_adapter.py`); factory function `create_backend(config)` in `domain/services/config.py`
  - **AC**: Each backend implements `LLMPort` Protocol and returns `GenerationResult` with text + usage; `OllamaBackend` works offline; switching backends via config works; all backends mocked in tests; DI container resolves `LLMPort` correctly
  - **Depends on**: T-012

- [x] T-019 [DONE] [P] [Foundation] Implement `src/aicophilosopher/application/services/tool_registry.py`: `ToolRegistry` with plugin-style registration (`register_tool`, `get_tool`, `list_tools`); `BaseTool` ABC with `name`, `description`, `execute()`
  - **AC**: Tools register/unregister dynamically; `ToolRegistry.get_tool("search")` returns correct instance; duplicate registration raises `ValidationError`

### 2.6 Reasoning Engine Skeleton

- [x] T-020 [DONE] [P] [Foundation] Implement `src/aicophilosopher/domain/services/tradition_manager.py`: `TraditionManager` that loads JSON tradition profiles from `data/traditions/` (5 default traditions: analytic, continental, philosophy_of_technology, philosophy_of_science, philosophy_of_mathematics, software_architecture, model_theory); validates arguments against tradition norms; detects incommensurability
  - **AC**: `load_traditions()` discovers all JSON files; `validate_argument(arg, "philosophy_of_technology")` returns norm violations; `check_incommensurability("software_abstraction", "mathematical_abstraction")` returns True with explanation
  - **Depends on**: T-019

- [x] T-021 [DONE] [P] [Foundation] Implement `src/aicophilosopher/domain/services/uncertainty.py`: `UncertaintyLifecycle` class with `track()`, `manage()`, `communicate()` methods; state machine for `ReviewStatus` transitions; uncertainty registry sync with inline Markdown annotations
  - **AC**: `track(claim)` creates `UncertaintyRecord`; `manage()` updates confidence; `communicate()` generates margin annotation string; rejected claims trigger document section removal + appendix append
  - **Depends on**: T-010

- [x] T-022 [DONE] [P] [Foundation] Implement `src/aicophilosopher/domain/services/logic_engine.py`: `LogicEngine` with Z3 integration for propositional/predicate validity checking; `check_validity(premises, conclusion)`; `detect_contradiction(formulas)`; returns `ValidityResult` with `is_valid`, `counter_model` (if invalid), `confidence`
  - **AC**: Syllogism "All M are P; All S are M; Therefore All S are P" returns valid; inconsistent premises return contradiction detected; invalid argument returns counter-model explanation
  - **Depends on**: T-002

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Clarification Dialogue & Workstream Management (Priority: P1) 🎯 MVP

**Goal**: User can start a project with a vague question, engage in Socratic clarification, approve a refined goal, and manage workstreams via CLI commands

**Independent Test**: Run `new project`, `refine goal`, `start workstream`, `pause`, `resume`, `status`, `show hypotheses`, `show dead ends` end-to-end with mock LLM responses

### Tests for User Story 1

- [x] T-030 [P] [US1] Unit tests for `ProjectCoordinatorAgent` dialogue state machine in `tests/unit/test_coordinator_dialogue.py`: test clarification turns, goal approval transition, workstream proposal (4 tests FAIL as required; install T-033 to make them PASS)
  - **AC**: Tests FAIL before implementation; PASS after; cover ≤5 turns constraint (AC-001)

- [x] T-032 [DONE] [US1] Implement `src/aicophilosopher/application/orchestration/base.py`: `BaseAgent` with shared LLM client, logging, tool access via `ToolRegistry`, message sending via `MessageQueue`; `run()` abstract method
  - **AC**: Subclassing `BaseAgent` and calling `run()` dispatches to LLM; messages logged; tools accessible via `self.tools.get_tool()`
  - **Depends on**: T-017, T-018, T-019

- [x] T-037 [DONE] [US1] Implement `src/aicophilosopher/application/services/living_document.py`: `LivingDocument` class with YAML frontmatter generation, Markdown section management, annotation embedding/extraction, version tracking
  - **AC**: `create(title, project_id)` generates frontmatter; `add_section("Arguments", content)` appends with annotation placeholders; `embed_annotations()` inserts HTML comment annotations; `parse_annotations()` extracts all annotations
  - **Depends on**: T-015

- [x] T-033 [DONE] [US1] Implement `src/aicophilosopher/application/orchestration/coordinator.py`: `ProjectCoordinatorAgent` with Socratic clarification dialogue, goal refinement, workstream proposal/approval, steering command handling, progressive disclosure rendering
  - **AC**: Dialogue continues until goal approved; `propose_workstream()` returns structured proposal; steering commands update workstream state
  - **Depends on**: T-032, T-013, T-015

- [x] T-034 [DONE] [P] [US1] Implement `src/aicophilosopher/application/orchestration/workstream_coordinator.py`: `WorkstreamCoordinatorAgent` base class that manages sub-agent sequences, tracks workstream status, generates incremental updates
  - **AC**: `create_workstream(type, goal)` initializes correct coordinator subclass; `pause()`/`resume()` transition status; `steer()` modifies active plan
  - **Depends on**: T-032, T-015

- [x] T-031 [DONE] [US1] Integration test for full clarification → workstream lifecycle in `tests/integration/test_clarification_workflow.py`: full lifecycle start→clarify→approve→start→pause→resume→status
  - **AC**: End-to-end test passes; workstream status reflects commands within 30s (AC-007)

- [x] T-035 [DONE] [US1] Implement `src/aicophilosopher/presentation/commands.py`: Click command definitions for all CLI commands
  - **AC**: Each command parses arguments correctly; invalid arguments show help; `status` displays epistemic overview; `show dead ends` lists failed/abandoned (AC-008)
  - **Depends on**: T-033, T-034

- [x] T-036 [DONE] [US1] Implement `src/aicophilosopher/presentation/cli.py`: Rich-based terminal UI with live display, collapsible panels, Markdown rendering
  - **AC**: `show document` renders Markdown; `status` shows live progress bars; collapsible [Details]/[Suggestions]; latency <30s (AC-007)
  - **Depends on**: T-035

**Checkpoint**: ✅ **User Story 1 COMPLETE** — User can create project, clarify goals, manage workstreams, and view document via CLI commands with Rich progressive disclosure. Ready for Phase 4 (User Story 2).

---

## Phase 4: User Story 2 - Literature Search & Concept Analysis (Priority: P1) 🎯 MVP

**Goal**: User can launch literature search and concept analysis workstreams that produce structured, tradition-aware outputs integrated into the living document

**Independent Test**: Start `literature_search` workstream → receive structured bibliography with tradition tags and bridge notes; start `concept_analysis` workstream → receive concept map and distinction matrix

### Tests for User Story 2

- [x] T-040 [DONE] [P] [US2] Unit tests for `LiteratureSearchAgent` in `tests/unit/test_literature_search.py`: test query construction, result filtering, tradition tagging, bridge note generation (5 tests FAIL as required; install T-044 to make them PASS)
  - **AC**: Tests FAIL before implementation; PASS after; mock search API returns 5 results; agent outputs ≥1 bridge note per cross-traditional query (AC-002)

- [x] T-041 [DONE] [P] [US2] Unit tests for `ConceptAnalysisAgent` in `tests/unit/test_concept_analysis.py`: test distinction mapping, thought experiment generation, conceptual genealogy (5 tests FAIL as required; install T-046 to make them PASS)
  - **AC**: Tests FAIL before implementation; PASS after; concept map contains ≥3 nodes; distinction matrix compares ≥2 traditions (AC-003)

- [x] T-042 [DONE] [P] [US2] Integration test for literature search → synthesis flow in `tests/integration/test_literature_synthesis.py`: workstream runs → report generated → Synthesis Agent integrates into living document (2 tests FAIL as required)
  - **AC**: End-to-end test passes; living document contains bibliography section with margin annotations (AC-006)

**Checkpoint**: User Stories 1 AND 2 should both work independently. User can search literature, analyze concepts, and see results in the living document.

### Implementation for User Story 2

- [x] T-043 [DONE] [US2] Implement `src/aicophilosopher/infrastructure/adapters/search_adapter.py`: `SearchTool` with adapters for PhilPapers API, SEP (scrape if no API), IEP, arXiv (cs.AI + humanities), Semantic Scholar; cross-traditional query expansion; tradition tag assignment; consent gate before external API calls
  - **AC**: `search("abstraction", traditions=["analytic", "philosophy_of_technology"])` returns results with tradition tags; consent dialog shown if `privacy.allow_external_search` unset; no project content transmitted (Constitution Principle I)
  - **Depends on**: T-019, T-012

- [x] T-044 [DONE] [US2] Implement `src/aicophilosopher/application/agents/literature_search.py`: `LiteratureSearchAgent` that uses `SearchTool`, performs cross-domain literature bridging (e.g., "abstraction" → software abstraction layers, mathematical abstraction, scientific model abstraction), generates structured bibliography with confidence scores and bridge notes
  - **AC**: Bibliography contains ≥1 bridge note per cross-traditional query; relevance score 0.0–1.0 for each paper; BibTeX entries valid; precision ≥70% on known queries (AC-002)
  - **Depends on**: T-043, T-032

- [x] T-045 [DONE] [P] [US2] Implement `src/aicophilosopher/infrastructure/adapters/pdf_rag_adapter.py`: `PDFRAGTool` with PyMuPDF extraction, text chunking, ChromaDB indexing, local retrieval only; metadata extraction (title, author, abstract)
  - **AC**: `ingest_pdf(path)` extracts text in <2s per 50 pages; `query("qualia")` returns relevant chunks; metadata accessible; no external transmission
  - **Depends on**: T-014, T-019

- [x] T-046 [DONE] [US2] Implement `src/aicophilosopher/application/agents/concept_analysis.py`: `ConceptAnalysisAgent` that performs necessary/sufficient condition analysis, distinction mapping (de re vs de dicto, formal specification vs implementation), thought experiment generation (trolley, brain-in-a-vat, Chinese room argument), conceptual genealogy, cross-traditional concept bridging with incommensurability flagging
  - **AC**: Concept map has ≥3 nodes with relationships; distinction matrix compares ≥2 traditions; thought experiments include epistemic status; confidence scores on all analyses; accuracy ≥80% on analytic concepts (AC-003)

- [x] T-047 [DONE] [US2] Implement `src/aicophilosopher/application/services/document_parser.py`: `DocumentParser` for parsing Markdown/YAML frontmatter, extracting margin annotations, validating annotation schema (Source, Confidence, Origin, Counter-argument strength, Tradition, Review status, Phenomenological grounding)
  - **AC**: `parse("living_document.md")` returns frontmatter dict + list of annotations; invalid annotations raise `ValidationError`; annotation round-trip preserves all fields
  - **Depends on**: T-037

### 2.7 Domain-Aware Query Strategy (spec §3.6)

- [ ] T-048 [US2] Implement `src/aicophilosopher/ports/query_port.py`: `PhilosophicalQueryStrategy` with semantic expansion, Core Domain detection, staged pipeline integration (Cheap→Expensive), and tradition-aware query generation
  - **AC**: `PhilosophicalQueryStrategy.expand("moving sofa problem")` returns philosophically scoped queries including "philosophy of mathematics"; LLM-based expansion (not keyword matching); Core Domains automatically detected
  - **Depends on**: T-012 (reads LLM config for cheap-model access)

- [ ] T-049 [P] [US2] Implement `src/aicophilosopher/domain/services/core_domains.py`: Core Philosophical Domains registry (Philosophy of Mathematics, Logic, Pragmatism, Philosophy of Science, Philosophy of Technology, Model Theory) with weighted priority, sub-traditions, and subtopic metadata; shared across all Agents
  - **AC**: `CoreDomains.get("philosophy_of_mathematics")` returns domain profile with sub_traditions and expansion_terms; `CoreDomains.detect("moving sofa problem")` returns matching domain priorities; all 6 domains registered
  - **Depends on**: T-020 (follows same domain/ pattern)
  - **Depends on**: T-032, T-020, T-021

- [x] T-047 [DONE] [US2] Implement `src/aicophilosopher/application/services/document_parser.py`: `DocumentParser` for parsing Markdown/YAML frontmatter, extracting margin annotations, validating annotation schema
  - **AC**: `parse("living_document.md")` returns frontmatter dict + list of annotations; invalid annotations raise `ValidationError`
  - **Depends on**: T-037

**Checkpoint**: All User Story 2 tasks complete (T-040–T-047). Ready for Phase 5.

---

## Phase 5: User Story 3 - Argumentation, Critical Review & Synthesis (Priority: P1) 🎯 MVP

**Goal**: User can reconstruct arguments, detect fallacies, generate counter-arguments, and synthesize everything into a coherent living document with full margin annotations

**Independent Test**: Start `argumentation` workstream → get standard-form arguments with competing positions; start `critical_review` workstream → get fallacy inventory and counter-arguments; `synthesis` merges all into annotated living document

### Tests for User Story 3

- [x] T-050 [DONE] [P] [US3] Unit tests for `ArgumentationAgent` in `tests/unit/test_argumentation.py`: test standard form reconstruction, competing position generation, implicit premise identification
  - **AC**: Tests FAIL before implementation; PASS after; ≥2 competing positions generated; each has premises + conclusion + inference rule (AC-004)

- [x] T-051 [DONE] [P] [US3] Unit tests for `CriticalReviewAgent` in `tests/unit/test_critical_review.py`: test fallacy detection, counter-argument generation, adversarial review
  - **AC**: Tests FAIL before implementation; PASS after; ≥1 counter-argument per argument; ≥70% validity rate on counter-arguments (AC-005)

- [ ] T-052 [P] [US3] Integration test for argumentation → review → synthesis flow in `tests/integration/test_argument_review_synthesis.py`
  - **AC**: End-to-end test passes; living document contains Arguments section with embedded margin annotations (AC-006)

### Implementation for User Story 3

- [ ] T-053 [US3] Implement `src/aicophilosopher/application/agents/argumentation.py`: `ArgumentationAgent` that reconstructs arguments in standard form (premises + conclusion + inference rule), generates multiple competing positions
  - **AC**: Each argument has explicit premises/conclusion/inference rule; ≥2 distinct traditions represented; implicit assumptions listed
  - **Depends on**: T-032, T-022, T-020

- [ ] T-054 [US3] Implement `src/aicophilosopher/application/agents/critical_review.py`: `CriticalReviewAgent` that detects logical fallacies with severity ratings, evaluates validity/soundness/plausibility, generates counter-arguments, performs adversarial review
  - **AC**: Fallacy inventory includes severity + correction; counter-argument tree has ≥1 node per argument; review confidence score present
  - **Depends on**: T-032, T-022, T-020

- [x] T-055 [DONE] [US3] Implement `src/aicophilosopher/application/services/review_process.py`: `ReviewProcess` class that orchestrates iterative multi-reviewer rounds (min 2, max 5 rounds), manages reviewer persistence, handles escalation
  - **AC**: Review round completes when all approve; escalation at round 5; `stalled` status on escalation
  - **Depends on**: T-034, T-021

- [ ] T-056 [US3] Implement `src/aicophilosopher/application/agents/synthesis.py`: `SynthesisAgent` that merges workstream outputs into coherent living document sections, preserves margin annotations, generates conflict flags
  - **AC**: Synthesized document has consistent voice; 100% of non-trivial claims annotated; conflicts flagged; synthesis confidence score included
  - **Depends on**: T-037, T-047, T-055, T-021

**Checkpoint**: User Stories 1, 2, AND 3 should all work independently. The MVP core is complete: clarification, literature search, concept analysis, argumentation, critical review, and synthesis all functional.

---

## Phase 6: User Story 4 - Cross-Traditional Comparison (Priority: P2)

**Goal**: User can compare philosophical positions across traditions, identify bridge concepts, and flag incommensurabilities

**Independent Test**: `compare traditions "mind"` returns tradition profiles, bridge concept map, and incommensurability register

### Tests for User Story 4

- [ ] T-060 [P] [US4] Unit tests for `CrossTraditionalComparisonAgent` in `tests/unit/test_cross_traditional.py`: test bridge identification, incommensurability detection, colonization prevention
  - **AC**: Tests FAIL before implementation; PASS after; bridge map has valid edges; incommensurability register flags contested mappings

- [ ] T-061 [P] [US4] Integration test for cross-traditional comparison → synthesis in `tests/integration/test_cross_traditional_synthesis.py`
  - **AC**: End-to-end test passes; living document contains Cross-Traditional Perspectives section

### Implementation for User Story 4

- [ ] T-062 [US4] Implement `src/aicophilosopher/application/agents/cross_traditional.py`: `CrossTraditionalComparisonAgent` that identifies functional analogues across traditions, flags incommensurabilities, evaluates within native frameworks, avoids category colonization
  - **AC**: Comparison report contains tradition profiles, bridge concept map, incommensurability register, synthesis proposals
  - **Depends on**: T-032, T-020, T-021

- [x] T-063 [DONE] [US4] Add 5 default tradition JSON profiles in `data/traditions/`: `analytic_philosophy.json`, `continental_philosophy.json`, `philosophy_of_technology.json`, `philosophy_of_science.json`, `philosophy_of_mathematics.json`, `software_architecture.json`, `model_theory.json`
  - **AC**: Each profile has assumptions, norms, criteria, key figures, bridge warnings; `TraditionManager` loads all on startup
  - **Depends on**: T-020

**Checkpoint**: All four user stories independently functional. Core MVP complete per spec §10.1.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories; ensure constitution compliance; prepare for deployment

### 7.1 Testing & Quality

- [ ] T-070 [P] [Polish] Achieve ≥80% test coverage for core logic (`src/aicophilosopher/domain/`, `src/aicophilosopher/application/`, `src/aicophilosopher/infrastructure/adapters/``)
  - **AC**: `pytest --cov` report shows ≥80% for all listed packages; `make test-cov` passes

- [ ] T-071 [P] [Polish] Add property-based tests for state transition invariants using `hypothesis`: project lifecycle, workstream status machine, uncertainty review status machine
  - **AC**: Hypothesis tests run for 100+ examples without failure; catch invalid transitions (e.g., `completed` → `running`)

- [ ] T-072 [Polish] Add regression test suite in `tests/regression/`: capture known bug scenarios from development and ensure they remain fixed
  - **AC**: Each regression test has issue reference, reproduction steps, and assertion; all pass

### 7.2 Constitution Compliance Verification

- [ ] T-073 [Polish] Verify Constitution Principle I (Core Independence): Run full MVP with `HERMES_ENABLED=false`, `OPENCODE_ENABLED=false`, `ALLOW_EXTERNAL_SEARCH=false`; all core features operational
  - **AC**: All ACs pass in offline mode except AC-002 (external search); local RAG and all other agents fully functional (AC-009)

- [ ] T-074 [Polish] Verify Constitution Principle II (Intellectual Honesty): Audit all agents for mandatory confidence scores; verify user approval gate before permanent document updates; check hypothesis history retention
  - **AC**: No agent omits confidence score; `SynthesisAgent` requires approval; `show dead ends` returns 100% of abandoned hypotheses (AC-008)

- [ ] T-075 [Polish] Verify Constitution Principle IV (Testing): Ensure all core logic has deterministic tests; verify mock usage for external services; check coverage report
  - **AC**: Core test suite passes without network; coverage ≥80%; no flaky tests

### 7.3 Performance & Robustness

- [ ] T-076 [Polish] Performance validation: workstream status reflection <30s (AC-007), hypothesis retrieval <5s (AC-008), clarification ≤5 turns ≤10min (AC-001)
  - **AC**: Benchmark script runs all ACs and reports pass/fail with timing

- [ ] T-077 [Polish] Add retry logic with exponential backoff for external API calls (LLM, search); max 3 retries; escalation to Project Coordinator on persistent failure
  - **AC**: Simulated 503 errors trigger retry; after 3 failures, error notification sent to coordinator; fallback to alternative backend if configured

- [ ] T-078 [Polish] Memory profiling: ensure peak memory <500MB with 5 concurrent workstreams
  - **AC**: `memory_profiler` or `tracemalloc` report shows peak <500MB during stress test

### 7.4 Documentation & DevEx

- [ ] T-079 [P] [Polish] Update `README.md` with installation instructions, quickstart, architecture overview, and contribution guidelines
  - **AC**: New developer can install and run `new project` following README alone

- [ ] T-080 [P] [Polish] Validate `quickstart.md` against actual codebase: verify all commands, file paths, and environment variables match implementation
  - **AC**: Every command in `quickstart.md` executes successfully in clean environment

- [ ] T-081 [Polish] Add user-facing `docs/usage.md` with tutorial: creating a project, running a literature review, analyzing concepts, building arguments, and exporting a position paper
  - **AC**: Tutorial is step-by-step with expected outputs; suitable for philosophy students with no technical background

### 7.5 External Bridge Skeleton (Optional for MVP)

- [ ] T-082 [P] [Polish] Implement `src/aicophilosopher/infrastructure/adapters/external_bridge_adapter.py`: `ExternalAgentBridge` ABC with `HermesAdapter` and `OpenCodeGoAdapter` skeletons; seamless fallback to internal LangGraph; consent flow; audit logging
  - **AC**: Bridge interface compiles; fallback triggers when external layer unavailable; consent dialog shown before data sharing; logs written to `external_bridge.jsonl`
  - **Note**: Full functionality deferred to Phase 6 (post-MVP) per spec §11

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
  - T-010/T-011/T-012 can start in parallel
  - T-013 depends on T-010/T-011
  - T-014 is independent of other foundation tasks
  - T-015 depends on T-010/T-012
  - T-016 depends on T-010
  - T-017 depends on T-013/T-016
  - T-018 depends on T-012
  - T-019 is independent
  - T-020 depends on T-019
  - T-021 depends on T-010
  - T-022 is independent (Z3 only needs package installed)
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3 → US4)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Integrates with US1 via CLI but independently testable
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - Depends on US1/US2 concepts but independently testable
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Builds on US2/US3 but independently testable

### Critical Path

```
T-001 → T-002 → T-010 → T-013 → T-017 → T-032 → T-033 → T-034 → T-035 → T-036 → T-037
                                              ↓
                                        [US1 Complete]
                                              ↓
                                        T-043 → T-044 → T-046 → [US2 Complete]
                                              ↓
                                        T-053 → T-054 → T-055 → T-056 → [US3 Complete]
                                              ↓
                                        T-062 → [US4 Complete]
                                              ↓
                                        T-070 → T-073 → T-076 → [MVP Ready]
```

### Parallel Opportunities

- **Setup**: T-001 through T-005 all parallel
- **Foundation**: T-010/T-011/T-012/T-014/T-018/T-019/T-022 all parallel; T-013/T-015/T-016/T-017/T-020/T-021 sequential within foundation
- **US1 Tests**: T-030 and T-031 parallel
- **US1 Implementation**: T-032, T-034 parallel (both depend on foundation); T-033 depends on both; T-035 depends on T-033/T-034; T-036 depends on T-035; T-037 parallel with T-032
- **US2 Tests**: T-040, T-041, T-042 parallel
- **US2 Implementation**: T-043 and T-045 parallel; T-044 depends on T-043; T-046 depends on foundation; T-047 parallel
- **US3 Tests**: T-050, T-051, T-052 parallel
- **US3 Implementation**: T-053, T-054, T-055 parallel; T-056 depends on all three + T-037/T-047/T-021
- **US4 Tests**: T-060, T-061 parallel
- **US4 Implementation**: T-062 parallel with US3; T-063 parallel
- **Polish**: T-070, T-071, T-072, T-079, T-080, T-081, T-082 all parallel; T-073/T-074/T-075/T-076/T-077/T-078 sequential or parallel depending on resources

---

## Implementation Strategy

### MVP First (US1 + US2 + US3 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Clarification & Workstream Management)
4. Complete Phase 4: User Story 2 (Literature Search & Concept Analysis)
5. Complete Phase 5: User Story 3 (Argumentation, Review & Synthesis)
6. **STOP and VALIDATE**: All AC-001 through AC-010 pass
7. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (basic project management)
3. Add User Story 2 → Test independently → Deploy/Demo (research assistance)
4. Add User Story 3 → Test independently → Deploy/Demo (MVP complete)
5. Add User Story 4 → Test independently → Deploy/Demo (cross-traditional support)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (coordinator + CLI)
   - Developer B: User Story 2 (literature + concept agents)
   - Developer C: User Story 3 (argumentation + review + synthesis)
3. Stories complete and integrate independently
4. Developer D: User Story 4 (cross-traditional) starts once T-020/T-063 are ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (test-first for all foundation and US1-3 tasks)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All tasks must respect constitution principles: local-first, privacy, intellectual honesty, testing, MVP-focus

---

**Tasks Version**: 1.0.0 | **Last Updated**: 2026-05-13 | **Status**: **Phase 0-3 COMPLETE, Phase 4 (User Story 2) COMPLETE, T-063 DONE** — Ready for Phase 5 (User Story 3).
