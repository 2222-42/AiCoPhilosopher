# Tasks: Console Agent — Continuous Dialogue REPL

**Input**: Design documents from `.specify/specs/002-console-agent/`

**Prerequisites**: `spec.md` (4 user stories, 26 FRs, 9 SCs), `plan.md` (Phase 0 & Phase 1 Complete ✅), `research.md` (9 technical decisions), `data-model.md` (7 entities + SQLite schema), `contracts/` (repl-commands.md, nlu-intent-schema.md, repl-rendering.md)

**Tests**: Tests are mandatory per Constitution Principle IV. Every implementation task is paired with its test task (TDD: RED before GREEN). Mock LLM responses used for deterministic NLU tests.

**Organization**: Tasks are grouped by user story per the template. Console/REPL experience (Issue #35) is prioritized: natural language REPL (US1) → session persistence (US2) → slash commands (US3) → full inquiry cycle (US4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, Foundation)
- Include exact file paths in descriptions
- **AC**: Acceptance Criteria — verifiable conditions that prove task completion
- **Depends on**: Task IDs this task cannot start before

---

## Phase 1: Setup (Dependencies & Prompts)

**Purpose**: Add the single new production dependency (prompt_toolkit) and create the NLU system prompt. No code changes yet.

- [x] T-001 [P] [Foundation] Add `prompt_toolkit>=3.0` to `pyproject.toml` dependencies and reinstall editable package
  - **Files**: `pyproject.toml` (modify: add `"prompt_toolkit>=3.0"` to `[project] dependencies`)
  - **AC**: `pip install -e ".[dev]"` succeeds; `python -c "from prompt_toolkit import PromptSession; print('OK')"` outputs `OK`; `python -c "from prompt_toolkit.history import FileHistory; print('OK')"` outputs `OK`; existing test suite (`pytest tests/ -q`) passes with no regressions
  - **Depends on**: (none — can start immediately)

- [x] T-002 [P] [Foundation] Create NLU intent classification system prompt at `prompts/nlu/intent_classifier.md`
  - **Files**: `prompts/nlu/intent_classifier.md` (create)
  - **AC**: File exists with: 16 intent types listed with descriptions + 3 examples each; JSON output format spec shown; confidence threshold rule (<0.85 → needs_clarification) documented; Japanese examples included alongside English; context template with `{project_title}`, `{workstream_list}`, `{active_topic}`, `{pending_count}` placeholders; matches `contracts/nlu-intent-schema.md` §5 structure exactly
  - **Depends on**: (none — can start in parallel with T-001)

---

## Phase 2: Foundational (Domain Entities + Schema)

**Purpose**: Core domain entities and SQLite schema that ALL user stories depend on. Must be complete before any user story implementation begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### 2.1 Domain Entities

- [x] T-003 [Foundation] Implement all 7 Console Agent domain entities as Pydantic v2 models in `src/aicophilosopher/domain/entities/session.py`
  - **Files**: `src/aicophilosopher/domain/entities/session.py` (create)
  - **Entities**: `SessionState`, `DialogueTurn`, `UserIntent`, `ContextBlock`, `FocusContext`, `ApprovalRequest`, `ActionTaken` + all nested enums/models: `SessionStatus`, `SpeakerType`, `IntentType`, `AlternativeIntent`, `EpistemicSnapshot`, `PendingDecision`, `ToggleState`, `ApprovalRequestType`, `ApprovalOption`, `Urgency`, `ActionType`
  - **AC**: All entities importable: `from aicophilosopher.domain.entities.session import SessionState`; all entities validate correctly with sample data per `data-model.md` §2; `confidence` field bounds (0.0–1.0) enforced by Pydantic validator; `SessionStatus` enum values match (`active`, `paused`, `closed`); `IntentType` has all 16 values; `ApprovalRequestType` has all 7 values; `SpeakerType` has 3 values; `domain/entities/session.py` imports ONLY stdlib + pydantic (verified by `python scripts/check_domain_purity.py`); `ruff check` and `mypy` pass on the file
  - **Depends on**: T-001 (prompt_toolkit in deps — not used by session.py directly, but project must be installable)

- [x] T-004 [P] [Foundation] Write unit tests for all session domain entities
  - **Files**: `tests/unit/domain/test_session.py` (create)
  - **AC**: ≥30 tests covering: validation rules for each entity (required fields, bounds, enum membership); `SessionState` status transitions (active→paused→closed rejections); `DialogueTurn` speaker-type consistency (user turns must have intent, coordinator turns must have actions); `confidence` bound enforcement (reject <0.0, >1.0); `ApprovalRequest` resolution rules (resolved_at requires user_choice); `ContextBlock` computed `turns` property raises `NotImplementedError` (derived, not persisted); `FocusContext` default factory creates valid instance; immutability: copying entities via `.model_copy()` works correctly; all test fixtures use deterministic UUIDs (no `uuid4()` in test assertions); `pytest tests/unit/domain/test_session.py -v` passes; domain purity check still passes after adding test file
  - **Depends on**: T-003 (needs the entity classes to test)

### 2.2 SQLite Schema Extensions

- [x] T-005 [Foundation] Extend SQLite adapter with session persistence schema in `src/aicophilosopher/infrastructure/adapters/sqlite_adapter.py`
  - **Files**: `src/aicophilosopher/infrastructure/adapters/sqlite_adapter.py` (modify: add `_ensure_session_tables()` method + 4 CREATE TABLE statements + 7 INDEX statements from `data-model.md` §3)
  - **Tables**: `sessions`, `approval_requests`, `dialogue_turns`, `context_blocks`
  - **AC**: All 4 tables created on adapter init; `sessions` table has `project_id` FK → `projects(project_id) ON DELETE CASCADE`; `UNIQUE INDEX idx_sessions_one_active ON sessions(project_id) WHERE status = 'active'` enforces one-active-per-project rule; `dialogue_turns` has `session_id` FK → `sessions(session_id) ON DELETE CASCADE`; `dialogue_turns` has composite index on `(session_id, timestamp)`; `approval_requests` has filtered index for pending requests (`WHERE resolved_at IS NULL`); `context_blocks` has `session_id` FK; all tables survive re-initialization (`CREATE TABLE IF NOT EXISTS`); existing 001 tables not affected (no ALTER, no DROP); `pytest tests/ --ignore=tests/unit/presentation --ignore=tests/integration -q` (existing tests) passes
  - **Depends on**: T-003 (needs entity field names to match SQL columns)

- [x] T-006 [P] [Foundation] Write unit tests for SQLite session schema creation and constraints
  - **Files**: `tests/unit/infrastructure/test_session_schema.py` (create)
  - **AC**: ≥15 tests: verify all 4 tables exist after adapter init; test one-active-session constraint (insert two active sessions for same project → UNIQUE constraint violation); test FK cascade (delete project → session + turns deleted); test filtered index (query `WHERE resolved_at IS NULL` uses index via `EXPLAIN QUERY PLAN`); test `dialogue_turns` timestamp ordering (inserted turns returned in chronological order); test schema is idempotent (calling `_ensure_session_tables()` twice doesn't error); test `approval_requests.options_json` stores/retrieves list of dicts correctly; each test uses temporary in-memory SQLite database; `pytest tests/unit/infrastructure/test_session_schema.py -v` passes
  - **Depends on**: T-005 (needs the schema to test)

### 2.3 StoragePort Extension

- [ ] T-007 [Foundation] Add session persistence method signatures to StoragePort protocol
  - **Files**: `src/aicophilosopher/ports/storage_port.py` (modify: add async method signatures following existing Protocol pattern)
  - **Methods to add** (all `async def`, returning `...` body per existing Protocol conventions): `save_session(session: dict[str, object]) -> None`, `load_session(project_id: str) -> dict[str, object] | None`, `list_projects_with_sessions() -> list[dict[str, object]]`, `reclaim_stale_sessions() -> int`, `save_dialogue_turn(turn: dict[str, object], session_id: str) -> None`, `save_approval_request(request: dict[str, object], session_id: str) -> None`, `load_pending_approvals(session_id: str) -> list[dict[str, object]]`, `update_session_heartbeat(session_id: str) -> None`, `finalize_session(session_id: str, reason: str) -> None`
  - **AC**: All 9 signatures follow existing `typing.Protocol` pattern (`async def ...` with `...` body); each has docstring describing behavior per `data-model.md` invariants; `mypy --strict src/aicophilosopher/ports/storage_port.py` passes and catches any adapter that misses a method; IDs use `str` type consistent with existing port signatures (`project_id`, `workstream_id` are `str` in the codebase, not `UUID`); existing adapter tests still pass (StoragePort is a Protocol, not ABC — missing methods are caught by mypy, not runtime TypeError); no implementation — signatures only
  - **Depends on**: T-003 (needs entity types for dict shape documentation in docstrings)

---

**Checkpoint**: Foundation ready — domain entities, SQLite schema, and StoragePort signatures in place. User story implementation can now begin.

---

## Phase 3: User Story 1 — Casual Philosophical Inquiry in Natural Language (Priority: P1) 🎯 Issue #35 Core

**Goal**: Launch `aicophilosopher`, type a philosophical question in natural language (no prefix, no subcommand), receive Socratic response. The fundamental REPL experience.

**Independent Test**: Launch `aicophilosopher`, type "I want to explore free will", receive natural language Socratic response with progressive disclosure rendering. No command prefixes used. Full dialogue turn persisted.

**Spec coverage**: FR-001 through FR-007, FR-014 through FR-017, FR-027, SC-001, SC-002, SC-007

### 3.1 NLU Intent Classifier

- [ ] T-008 [US1] Write unit tests for NLU intent classifier
  - **Files**: `tests/unit/presentation/test_nlu.py` (create), `tests/fixtures/mock_nlu_responses/` (create directory with `sample_classifications.json`)
  - **AC**: ≥25 tests: test all 16 intent types classified correctly with sample inputs (both English and Japanese); test confidence threshold behavior (<0.85 → `needs_clarification=True`); test entity extraction for each intent type (`start_inquiry` → `topic`, `tradition`; `steer_workstream` → `workstream_id`, `instruction`); test alternative intents populated (top 3 by confidence); test JSON parsing of LLM response (valid JSON, malformed JSON, missing fields); test rule-based fallback when LLM unavailable (offline mode patterns trigger correct intents); test empty input returns `needs_clarification=True`; test `/` prefixed input is NOT passed to NLU (handled by slash command router — test raises or otherwise confirms NLU is bypassed); test Japanese input ("自由意志について調べたい" → `start_inquiry` with topic "自由意志"); all tests use mock LLMPort (no network); `pytest tests/unit/presentation/test_nlu.py -v` passes
  - **Depends on**: T-003 (needs UserIntent, IntentType entities), T-002 (needs prompt template)

- [ ] T-009 [US1] Implement NLU intent classifier in `src/aicophilosopher/presentation/nlu.py`
  - **Files**: `src/aicophilosopher/presentation/nlu.py` (create)
  - **AC**: `classify_intent(user_input: str, context: FocusContext, llm_port: LLMPort) -> UserIntent` function works; calls LLMPort with system prompt from `prompts/nlu/intent_classifier.md` + user input + context; parses JSON response into `UserIntent` model (Pydantic validation catches malformed responses); enforces confidence threshold from config (`nlu.confidence_threshold`, default 0.85); returns `needs_clarification=True` when below threshold; includes `raw_input` in returned `UserIntent`; rule-based fallback function `fallback_classify(user_input: str) -> UserIntent` uses regex patterns from `contracts/nlu-intent-schema.md` §6; fallback returns `confidence=0.80` (always below threshold → will trigger clarification); all tests from T-008 pass; `ruff check` passes; `mypy` passes; file imports ONLY from `domain/`, `ports/`, and stdlib (no direct infrastructure imports)
  - **Depends on**: T-008 (TDD: tests before implementation)

### 3.2 REPL Main Loop

- [ ] T-010 [US1] Write unit tests for REPL main loop
  - **Files**: `tests/unit/presentation/test_repl.py` (create)
  - **AC**: ≥20 tests: test REPL session starts and shows welcome message; test natural language input routed to NLU (mock NLU returns `start_inquiry`); test `/` prefixed input routed to inline essential command handler (`/exit`, `/help`, `/details`, `/hide-details`, `/suggestions`, `/hide-suggestions` — these 6 commands are handled inline for US1); test unknown `/` commands (not yet implemented) produce "unknown command" message; test empty input ignored (no NLU call, no error); test Ctrl+D (EOF) triggers graceful exit; test `KeyboardInterrupt` (Ctrl+C) triggers graceful exit with session save; test REPL loop exits cleanly on `/exit` input; test input history tracks previous commands (prompt_toolkit FileHistory); test progressive disclosure rendering called after each coordinator response; test workstream status update queue flushed between turns; test session heartbeat updated on each turn; all tests mock LLMPort (no network) and use mock coordinator; `pytest tests/unit/presentation/test_repl.py -v` passes
  - **Depends on**: T-003 (SessionState, DialogueTurn), T-009 (NLU classifier interface must be known)

- [ ] T-011 [US1] Implement REPL main loop in `src/aicophilosopher/presentation/repl.py`
  - **Files**: `src/aicophilosopher/presentation/repl.py` (create)
  - **AC**: `run_repl(project_id: str | None = None, test_mode: bool = False) -> None` function with: prompt_toolkit `PromptSession` with `FileHistory`; input routing: `/` prefix → inline essential command handler (handles `/exit`, `/help`, `/details`, `/hide-details`, `/suggestions`, `/hide-suggestions` — 6 commands sufficient for US1; unknown `/` commands produce friendly "not yet implemented" message noting full registry comes in US3); non-`/` input → `nlu.classify_intent()` → `await coordinator.run(user_input=..., command=...)` via the existing `ProjectCoordinatorAgent` async API; Ctrl+D handler → graceful exit; Ctrl+C handler → graceful exit; progressive disclosure rendering via `rendering.render_response()`; command history (up/down arrows, Ctrl+R search) works; session heartbeat sent before every prompt display; workstream status queue flushed after each response render; test_mode flag: when True, uses mock coordinator and skips LLM calls; exit flow: `await session_manager.finalize_session()`, save command history, print goodbye; `ruff check` passes; `mypy` passes; imports only from `presentation/`, `application/`, `domain/`, `ports/` (no direct infrastructure imports)
  - **Depends on**: T-010 (TDD), T-009 (NLU classifier)
  - **Note**: The inline essential command handler in US1 is replaced by full `slash_commands.py` (T-020) in Phase 5. When T-020 completes, the REPL loop upgrades from inline dispatch to `slash_commands.dispatch()`. The 6 essential commands (`/exit`, `/help`, `/details`, `/hide-details`, `/suggestions`, `/hide-suggestions`) are sufficient for US1 + US2 operation.

### 3.3 Progressive Disclosure Rendering

- [ ] T-012 [P] [US1] Write unit tests for progressive disclosure renderer
  - **Files**: `tests/unit/presentation/test_rendering.py` (create)
  - **AC**: ≥20 tests: test Summary section always rendered (≤5 lines); test Epistemic Status always rendered (confidence, tradition, review status); test Active Workstreams rendered when workstreams exist (omitted when none); test [Details] collapsed by default (label shown, content hidden); test [Suggestions] collapsed by default; test toggle: `/details` command → `show_details=True` → content visible; test toggle: `/hide-details` → `show_details=False`; test toggle state persisted in FocusContext; test approval requests surfaced in Summary with ⚠️ icon; test system messages rendered in distinct style; test empty sections show placeholder text; test terminal width <80 columns → panels stack vertically; test Rich Panel borders rendered correctly; test confidence color coding (green ≥0.8, yellow ≥0.5, red <0.5); test markdown in [Details] section rendered correctly; all tests verify output string contains expected Rich markup or plain text anchors; `pytest tests/unit/presentation/test_rendering.py -v` passes
  - **Depends on**: T-003 (FocusContext, ToggleState)

- [ ] T-013 [US1] Implement progressive disclosure renderer in `src/aicophilosopher/presentation/rendering.py`
  - **Files**: `src/aicophilosopher/presentation/rendering.py` (create)
  - **AC**: `render_response(response: CoordinatorResponse, focus: FocusContext, console: Console) -> None` renders 5-section progressive disclosure per `contracts/repl-rendering.md`; `CoordinatorResponse` is a new Pydantic model (or dataclass) with fields: `summary`, `epistemic_status`, `active_workstreams`, `details`, `suggestions`, `is_approval_request`, `approval_options`; Rich `Panel` used for each section; confidence color coding: `Style(color="green")` for ≥0.8, yellow for ≥0.5, red for <0.5; toggle state read from `FocusContext.toggle_state`; `/details` and `/suggestions` commands toggled via `FocusContext.toggle_state` mutations; Summary truncated at 5 lines with `[...]` indicator when longer; system messages use `[System] HH:MM — message` format; all tests from T-012 pass; `ruff check` passes; `mypy` passes
  - **Depends on**: T-012 (TDD), T-003 (FocusContext)

### 3.4 US1 Integration

- [ ] T-014 [US1] Write integration test for US1: natural language inquiry end-to-end
  - **Files**: `tests/integration/test_repl_us1_inquiry.py` (create)
  - **AC**: ≥5 tests: test full flow — launch REPL → type "I want to explore free will" → NLU classifies as `start_inquiry` → mock coordinator returns Socratic response → progressive disclosure rendered; test clarification dialogue — user answers coordinator's question → NLU classifies as `clarify_question` → coordinator refines; test empty input → no crash, prompt re-shown; test 5-turn conversation → all turns persisted in dialogue history; test `/exit` → session finalized, status=paused; all tests use test_mode=True (no real LLM), mock coordinator answers; `pytest tests/integration/test_repl_us1_inquiry.py -v` passes; existing test suite passes (no regressions)
  - **Depends on**: T-011 (REPL loop), T-013 (rendering)

---

**Checkpoint**: US1 complete — user can launch REPL, converse in natural language, see progressive disclosure. Issue #35 core experience delivered.

---

## Phase 4: User Story 2 — Session Persistence and Seamless Resumption (Priority: P1) 🎯 Issue #35 Session Resume

**Goal**: Type `/exit`, come back later, resume exactly where you left off. Dialogue history, context blocks, pending approvals, and workstream states all restored.

**Independent Test**: Create project, chat 5 turns, `/exit`. Restart `aicophilosopher`, select project, verify dialogue history and context restored, continue conversation seamlessly.

**Spec coverage**: FR-008 through FR-013, FR-017, SC-004, SC-005, SC-009

### 4.1 Session Manager

- [ ] T-015 [US2] Write unit tests for session manager persistence
  - **Files**: `tests/unit/presentation/test_session_manager.py` (create)
  - **AC**: ≥25 tests: test `create_session(project_id)` creates active session with correct PID; test `persist_turn(turn, session_id)` writes DialogueTurn to DB; test persisting user turn (speaker=user, intent present) and coordinator turn (speaker=coordinator, actions present); test `finalize_session(session_id, reason)` → status=paused, exit_reason set, single transaction; test `load_session(project_id)` returns full SessionState with dialogue_history, context_blocks, focus_context; test resume: load session, status transitions paused→active, heartbeat updated; test `list_projects()` returns projects with last_active timestamps and session status (only active/paused, not closed); test `list_projects()` ordering: most recently active first; test `reclaim_stale_sessions()`: PID not running → mark paused with `exit_reason='stale_reclaimed'`; test `reclaim_stale_sessions()`: PID still running + heartbeat current → NOT reclaimed; test concurrent session prevention: `is_active_session_live(project_id)` returns True when PID alive + heartbeat ≤300s; test concurrent session warning triggers when starting new session on project with live session; test `update_heartbeat(session_id)` updates `heartbeat_at` timestamp; test crash recovery: simulate SIGKILL (no finalize) → next startup reclaims stale session, at most 1 turn lost; test `load_pending_approvals(session_id)` returns unresolved approval requests; test `save_approval_request(request, session_id)` upserts correctly; test context block persistence: `save_context_block(block, session_id)` and `load_context_blocks(session_id)` round-trips; all tests use in-memory SQLite; `pytest tests/unit/presentation/test_session_manager.py -v` passes
  - **Depends on**: T-005 (SQLite schema), T-003 (SessionState, etc.)

- [ ] T-016 [US2] Implement session manager in `src/aicophilosopher/presentation/session_manager.py`
  - **Files**: `src/aicophilosopher/presentation/session_manager.py` (create)
  - **AC**: `SessionManager` class with methods: `create_session()`, `persist_turn()`, `finalize_session()`, `load_session()`, `list_projects()`, `reclaim_stale_sessions()`, `update_heartbeat()`, `save_approval_request()`, `load_pending_approvals()`, `save_context_block()`, `load_context_blocks()`; `create_session()` inserts row in `sessions` table with `status='active'`, current PID, `heartbeat_at=now()`; `persist_turn()` inserts into `dialogue_turns` table BEFORE render (FR-009); `finalize_session()` wraps status update and exit_reason in single SQL transaction; `load_session()` reconstructs full `SessionState` from 4 tables + loads associated turns, context blocks, approvals; `list_projects()` joins `projects` and `sessions` tables, returns [dict] with keys: project_id, title, last_active_at, session_status, workstream_count; `reclaim_stale_sessions()` queries `sessions WHERE status='active'`, checks `os.kill(pid, 0)` or heartbeat timeout, `UPDATE` stale ones to paused; uses `StoragePort` for all DB access (no direct `aiosqlite` calls); all tests from T-015 pass; `ruff check` passes; `mypy` passes
  - **Depends on**: T-015 (TDD), T-007 (StoragePort signatures), T-005 (SQLite adapter)
  - **Note**: This is the largest single task (~400-500 lines). Implement in sub-modules if needed.

### 4.2 Session Resume Flow

- [ ] T-017 [US2] Implement project selection and session resume UI in REPL startup
  - **Files**: `src/aicophilosopher/presentation/repl.py` (modify: add `_startup_flow()` function), `src/aicophilosopher/presentation/cli.py` (modify: wire `--project`, `--new`, `--test-mode` flags)
  - **AC**: On `aicophilosopher` (no args): list projects with numbers (1-N), prompt user to select; numeric input selects project; UUID input treated as project ID; new question input → create new project + session; `--project <id>` flag: skip list, open directly; `--new "<question>"` flag: create project + begin clarification; `--test-mode` flag: skip LLM, use mock coordinator; stale session reclaim runs on startup (before project list); concurrent session detection: if selected project has live session → warn + offer terminate/read-only/cancel; session resume: load SessionState → coordinator presents structured summary (last topic, completed since exit, running workstreams, pending approvals); session resume: coordinator's LLM context populated with last N turns + context block summaries + pending approvals per FR-012; `pytest tests/integration/test_repl_us1_inquiry.py -v` still passes (no regressions to US1)
  - **Depends on**: T-016 (session manager), T-011 (REPL loop)

- [ ] T-018 [US2] Write integration test for session persistence and resume
  - **Files**: `tests/integration/test_session_persistence.py` (create)
  - **AC**: ≥8 tests: test full persist-resume cycle — create project, 5 turns of dialogue, `/exit`, load session, verify all 10 dialogue turns present; test workstream survival — launch workstream, `/exit`, resume, workstream still `running`; test pending approval survival — coordinator raises approval request, `/exit`, resume, approval re-presented; test context blocks survive restart — 3 context blocks created, `/exit`, resume, all 3 loaded with correct turn associations; test stale reclaim on crash — insert stale active session row (old PID), run reclaim, verify marked `stale_reclaimed`; test concurrent session detection — insert live active session, attempt resume, verify warning; test resume summary presentation — after resume, coordinator output includes last topic and workstream counts; test heartbeat updated on each turn; all tests use in-memory SQLite, test_mode=True; `pytest tests/integration/test_session_persistence.py -v` passes; existing tests pass (no regressions)
  - **Depends on**: T-017 (resume UI), T-016 (session manager)

---

**Checkpoint**: US1 + US2 complete — full P1 slice: natural language REPL with session persistence. Issue #35's "session resumption" requirement satisfied.

---

## Phase 5: User Story 3 — Slash Commands as Power-User Shortcuts (Priority: P2)

**Goal**: Type `/status`, `/pause ws-001`, `/export markdown` — fast, unambiguous command execution bypassing NLU. All 28 commands working.

**Independent Test**: Type each slash command, verify immediate correct action without NLU ambiguity. Verify every natural-language-capable action also has a `/` shortcut.

**Spec coverage**: FR-005, FR-006, FR-018 (partial), SC-006

### 5.1 Slash Command Parser

- [ ] T-019 [P] [US3] Write unit tests for slash command parser and router
  - **Files**: `tests/unit/presentation/test_slash_commands.py` (create)
  - **AC**: ≥30 tests: test all 28 commands parse correctly; test `/help` returns command list grouped by category; test `/exit` → session finalize called; test `/new "question"` → project creation initiated; test `/open proj-id` → session load initiated; test `/projects --status active` → filtered list returned; test `/archive` → confirmation prompt shown before archival; test `/search "query"` → literature search workstream launch; test `/analyze "concept"` → concept analysis launch; test `/argue "topic"` → argumentation launch; test `/review ws-002` → review triggered on specified workstream; test `/compare "topic" --traditions a,b` → cross-traditional comparison with traditions parsed; test `/synthesize` → synthesis triggered; test `/pause ws-001` → workstream paused; test `/resume ws-001` → workstream resumed; test `/steer ws-001 "instruction"` → steering command dispatched; test `/deepen "concept"` → deep analysis triggered; test `/abandon hyp-id` → hypothesis abandoned with reason prompt; test `/status` → overview displayed; test `/hypotheses --status refuted` → filtered hypothesis list; test `/dead-ends` → failed explorations displayed; test `/document --section Args --annotations` → document section shown; test `/details` → toggle ON; test `/hide-details` → toggle OFF; test `/export markdown` → export triggered; test `/add-note "text" --attach-to hyp-id` → note added; test `/upload /path/to/file.pdf` → PDF ingestion triggered; test `/help-request` → human assistance request; test `/config llm.backend claude` → config updated; test unknown command → friendly error with `/help` suggestion; test missing required args → usage hint; test invalid workstream ID → list of valid IDs; test ambiguous omission (e.g., `/pause` with multiple workstreams) → clarification; test input not starting with `/` is NOT routed to slash handler; test `/` appearing mid-sentence (e.g., "What does /search do?") NOT treated as command; test leading whitespace before `/` is trimmed (FR-006); `pytest tests/unit/presentation/test_slash_commands.py -v` passes
  - **Depends on**: T-003 (entity types for command handler signatures)

- [ ] T-020 [US3] Implement slash command parser and router in `src/aicophilosopher/presentation/slash_commands.py`
  - **Files**: `src/aicophilosopher/presentation/slash_commands.py` (create)
  - **AC**: `dispatch(command: str, session: SessionState) -> CommandResult` function; parser splits `/command args...` with quoted-string support; command registry: dict mapping 28 command names → handler functions with arg specs; validation before dispatch: unknown command → error, missing args → error, invalid IDs → error; ambiguous omission (e.g., `/pause` with >1 workstream) → clarification prompt; 6 category groupings per `contracts/repl-commands.md`: Session, Inquiry, Steering, View, Export/Data, Help/Config; command handlers delegate to appropriate managers: session commands → SessionManager, inquiry/steering → Coordinator, view → Coordinator, export/data → Coordinator/StoragePort; progressive disclosure used for command responses (same format as natural language); all tests from T-019 pass; `ruff check` passes; `mypy` passes
  - **Depends on**: T-019 (TDD), T-011 (REPL loop routing — slash dispatch is called from REPL), T-016 (SessionManager for session commands)

### 5.2 Command Response Rendering

- [ ] T-021 [US3] Write unit tests for slash command response rendering
  - **Files**: `tests/unit/presentation/test_rendering.py` (modify: add slash command response tests)
  - **AC**: ≥10 additional tests: test `/status` response renders with Summary + Epistemic Status + Active Workstreams; test `/help` response lists all 28 commands grouped by 6 categories; test `/hypotheses` table output with status/tradition columns; test `/document` shows markdown with optional annotations; test error responses formatted distinctly (red color, usage hint); test toggle commands (`/details`, `/hide-details`) don't produce visible output, just update state; test export confirmation shows file path; test `/archive` confirmation prompt renders with options; `pytest tests/unit/presentation/test_rendering.py -v` passes (old + new tests)
  - **Depends on**: T-020 (slash command output format must be known)

- [ ] T-022 [US3] Implement slash command response renderers in `src/aicophilosopher/presentation/rendering.py`
  - **Files**: `src/aicophilosopher/presentation/rendering.py` (modify: add `render_command_result()` function)
  - **AC**: `render_command_result(result: CommandResult, focus: FocusContext, console: Console)` renders command output in progressive disclosure format; command-specific formatters: status overview table, hypothesis list table, document sections with annotations, config display; error responses use `Style(color="red")` for error text + dim for usage hint; confirmation prompts (archive) use highlighted panel; all tests from T-021 pass; no regressions in US1 rendering tests
  - **Depends on**: T-021 (TDD), T-013 (existing rendering infrastructure)

- [ ] T-023 [US3] Write integration test for slash commands
  - **Files**: `tests/integration/test_repl_slash_commands.py` (create)
  - **AC**: ≥10 tests: test `/help` → output contains all 6 category headers; test `/status` → output includes project name, workstream counts, epistemic counts; test `/pause ws-001` → workstream paused, confirmation shown; test `/steer ws-001 "focus on post-1980"` → steering dispatched; test `/export markdown` → file created at reported path; test `/add-note "text"` → note persisted and retrievable; test `/hypotheses --status active` → only active hypotheses listed; test `/dead-ends` → failed explorations listed; test unknown command `/xyz` → error with `/help` suggestion; test `/` embedded in natural language not treated as command; all tests use test_mode=True; `pytest tests/integration/test_repl_slash_commands.py -v` passes; existing tests pass
  - **Depends on**: T-020 (parser), T-022 (rendering), T-017 (session resume — some commands need loaded session)

---

**Checkpoint**: US1 + US2 + US3 complete — REPL with natural language, session persistence, and 28 slash commands. Power users have full command set.

---

## Phase 6: User Story 4 — Full Inquiry Cycle as Single Conversation (Priority: P2)

**Goal**: Complete the full philosophical workflow — question → refine → search → discuss → tentative answer — entirely within the REPL, no mode-switching. Issue #35 flow requirement: "問い→Refine→サーチ→議論→仮の答え".

**Independent Test**: Start from vague question, pass through all phases to tentative answer. Verify living document updated with annotations, dialectical history, and uncertainty tracking.

**Spec coverage**: FR-018 through FR-026, SC-003, SC-008

### 6.1 Coordinator Integration

- [ ] T-024 [US4] Write unit tests for REPL-to-Coordinator integration
  - **Files**: `tests/unit/presentation/test_coordinator_integration.py` (create)
  - **AC**: ≥15 tests: test `start_inquiry` intent → `await coordinator.run(user_input=..., command="start")` called; test `clarify_question` intent → `await coordinator.run(user_input=..., command="refine_goal")` called; test `propose_workstream` intent → `await coordinator.run(command="propose_workstream", workstream_type=...)` called; test `approve_action` with workstream proposal → `await coordinator.run(command="approve_goal")` called; test `steer_workstream` intent → `await coordinator.run(command="steer", workstream_id=..., instruction=...)` called; test `request_status` intent → `await coordinator.run(command="status")` called; test `request_export` intent → export handled via StoragePort; test `inject_information` (PDF upload) → PDF ingestion via existing pipeline; test `compare_traditions` intent → workstream launched via `command="propose_workstream"` with appropriate type; test `dialogue_state` field in coordinator response dict used for routing (e.g., `"awaiting_question"`, `"clarifying"`, `"goal_proposed"`); test coordinator response `dict[str, Any]` transforms to `CoordinatorResponse` for rendering; test workstream status updates queued when received mid-input; test bidirectional help: coordinator raises approval request → surfaced as ⚠️ in Summary; test user's approval response routes back to coordinator; test existing message protocol used (no new message types introduced); all tests mock coordinator (return pre-scripted `dict[str, Any]` responses); `pytest tests/unit/presentation/test_coordinator_integration.py -v` passes
  - **Depends on**: T-009 (NLU — intents must be defined), T-011 (REPL loop — integration point)

- [ ] T-025 [US4] Implement REPL-Coordinator adapter in `src/aicophilosopher/presentation/repl.py`
  - **Files**: `src/aicophilosopher/presentation/repl.py` (modify: add `_route_to_coordinator()` function)
  - **AC**: `_route_to_coordinator(intent: UserIntent, coordinator: ProjectCoordinatorAgent) -> CoordinatorResponse` function; maps all 16 intent types to `await coordinator.run(...)` calls using the existing command API (`command="start"`, `"refine_goal"`, `"approve_goal"`, `"propose_workstream"`, `"steer"`, `"status"`); reads `dialogue_state` from coordinator's `dict[str, Any]` response for routing decisions; converts coordinator output to `CoordinatorResponse` for rendering; `approval_request` extraction: when `dialogue_state == "goal_proposed"` or similar, wrap in `CoordinatorResponse(is_approval_request=True, approval_options=[...])`; workstream status changes from async updates queued and surfaced per FR-024; uses existing JSON message protocol from 001 contracts (FR-023); no new message types introduced; all tests from T-024 pass; no regressions in US1-US3 tests
  - **Depends on**: T-024 (TDD)

### 6.2 Async Workstream Surfacing

- [ ] T-026 [P] [US4] Write unit tests for workstream status surfacing
  - **Files**: `tests/unit/presentation/test_workstream_surfacing.py` (create)
  - **AC**: ≥12 tests: test background thread polls workstream status every 2s; test status change (running→completed) queued and surfaced after current turn; test progress update (30%→60%) updates Rich Live bar only; test approval request surfaced immediately with ⚠️; test stalled workstream surfaced with warning icon; test updates queued during user input (not interrupting mid-typing); test multiple concurrent status changes all queued in order; test thread cleanly stopped on session exit; test polling uses StoragePort (not direct DB access); test error in polling thread doesn't crash REPL (error logged, polling continues); test workstream completion during session absence detected on resume; test LangGraph checkpointing integrated (workstreams continue independent of REPL process); `pytest tests/unit/presentation/test_workstream_surfacing.py -v` passes
  - **Depends on**: T-003 (SessionState.active_workstreams), T-011 (REPL loop — polling thread lifecycle)

- [ ] T-027 [US4] Implement workstream status surfacing in `src/aicophilosopher/presentation/repl.py`
  - **Files**: `src/aicophilosopher/presentation/repl.py` (modify: add `WorkstreamPoller` class)
  - **AC**: `WorkstreamPoller` class: `start(session_id, storage_port, update_queue)`, `stop()`, `_poll()`; runs in `threading.Thread` with 2s interval; queries workstream status via `StoragePort`; compares with last known states; detects transitions: running→completed, running→failed, running→stalled; queues `StatusChange` named tuples to update queue; `Rich Live` display updated with current workstream bar; approval requests detected and surfaced immediately; thread daemon=True (dies with main process); `stop()` sets event flag and joins; integration with REPL loop: `_flush_updates()` called before each prompt display; all tests from T-026 pass
  - **Depends on**: T-026 (TDD), T-025 (coordinator integration)

### 6.3 Full Cycle Integration Test

- [ ] T-028 [US4] Write integration test for full inquiry cycle
  - **Files**: `tests/integration/test_full_inquiry_cycle.py` (create)
  - **AC**: ≥8 tests: test full cycle — start inquiry "explore free will" → 3-turn Socratic clarification → goals approved → workstreams proposed → literature search launched → concept analysis launched → argumentation launched → critical review triggered → synthesis triggered → tentative answer presented; test pivot mid-cycle — "Actually, examine from phenomenological angle" → context shift, new workstream; test deepen — "Drill into Frankfurt 1969" → focused workstream; test info injection — upload mock PDF → RAG ingestion triggered; test dialectical history — "Show me how we arrived at this claim" → lineage presented; test 100-turn stress test — session handles 100 turns without degradation (response time ≤30s for 100th turn, comparable to 10th); test living document updated after synthesis with margin annotations; test all epistemic statuses tracked through cycle; all tests use test_mode=True, mock coordinator with pre-scripted responses; `pytest tests/integration/test_full_inquiry_cycle.py -v` passes; all existing tests pass (no regressions)
  - **Depends on**: T-025 (coordinator integration), T-027 (workstream surfacing), T-020 (slash commands — `/search`, `/argue`, etc.)

---

**Checkpoint**: All 4 user stories complete. Full REPL with natural language + persistence + slash commands + inquiry cycle.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: CLI entry point integration, quickstart validation, edge case hardening, and final quality gates.

- [ ] T-029 [Polish] Wire `aicophilosopher` CLI entry point to launch REPL mode
  - **Files**: `src/aicophilosopher/presentation/cli.py` (modify: add `repl` entry point)
  - **AC**: Running `aicophilosopher` (no subcommand) launches REPL mode; `aicophilosopher --project <id>` opens specific project; `aicophilosopher --new "<question>"` creates project and enters REPL; `aicophilosopher --test-mode` launches with mock coordinator; `aicophilosopher --help` shows REPL options alongside existing subcommand help; existing CLI subcommands (`new-project`, `start-workstream`, `refine-goal`, etc.) still work unchanged; `aicophilosopher --version` shows version; `pip install -e ".[dev]"` makes the console script available in PATH (existing project pattern, no Poetry); `ruff check` passes; `mypy` passes
  - **Depends on**: T-011 (REPL loop), T-017 (startup flow)

- [ ] T-030 [P] [Polish] Validate quickstart.md instructions end-to-end
  - **Files**: `.specify/specs/002-console-agent/quickstart.md` (reference only — validate, don't modify unless corrections needed)
  - **AC**: All `pip install` commands succeed; `python -c "from prompt_toolkit import PromptSession"` works; `python -m pytest tests/ -q` passes full test suite; `ruff check src/aicophilosopher/presentation/ tests/unit/presentation/` passes; `mypy src/aicophilosopher/presentation/ src/aicophilosopher/domain/entities/session.py` passes; `python scripts/check_domain_purity.py` passes (session.py only imports stdlib + pydantic); `make check` or equivalent runs all gates; manual REPL launch in test mode works: `aicophilosopher --test-mode` starts and accepts input; sqlite3 inspection queries from quickstart §5.4 work correctly; any discrepancies between quickstart and reality are fixed in quickstart.md
  - **Depends on**: T-029 (CLI entry point), all prior tasks

- [ ] T-031 [Polish] Edge case hardening and NLU accuracy validation
  - **Files**: `src/aicophilosopher/presentation/nlu.py` (modify: edge case handling), `tests/unit/presentation/test_nlu.py` (modify: add edge case tests)
  - **AC**: Edge cases from spec §Edge Cases all covered by tests: NLU misclassification below confidence → clarifying question (not wrong action); empty input → treated as inquiry start ("What would you like to explore?"); `/` in natural language ("What does /search do?") → NOT routed to slash handler; SIGKILL crash recovery → at most 1 turn lost, stale session reclaimed; concurrent session conflict → warning + choice interface; 1000-turn session → no performance degradation (latency ≤30s for 1000th turn); non-philosophical input ("What's the weather?") → polite redirection to philosophical topics; workstream completion during session absence → surfaced on resume; steering completed workstream → explained, new workstream offered; SC-002 NLU accuracy test: ≥90% on 100-utterance test set (test fixture created as `tests/fixtures/nlu_accuracy_test_set.json`); `pytest tests/unit/presentation/test_nlu.py -v` passes (old + new edge case tests); all integration tests pass
  - **Depends on**: T-028 (full cycle), T-018 (session persistence), T-023 (slash commands)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ─────────────────────────────────────────────────┐
    │                                                              │
Phase 2 (Foundational: entities + schema) ─── BLOCKS all stories ─┤
    │                                                              │
    ├── Phase 3 (US1: Natural Language REPL)                       │
    │       │                                                      │
    │       ├── Phase 4 (US2: Session Persistence)                 │
    │       │       │                                              │
    │       │       ├── Phase 5 (US3: Slash Commands)              │
    │       │       │       │                                      │
    │       │       │       ├── Phase 6 (US4: Full Inquiry Cycle)  │
    │       │       │       │       │                              │
    │       │       │       │       └── Phase 7 (Polish)           │
```

### Within Each User Story

Per Constitution Principle IV (TDD):
1. Test tasks FIRST (write tests, verify they FAIL)
2. Implementation tasks SECOND (make tests PASS)
3. Integration test LAST (verify story independence)

### Parallel Opportunities

| Phase | Parallel Tasks |
|-------|---------------|
| Phase 1 | T-001 ∥ T-002 |
| Phase 2 | T-004 ∥ T-006 (after T-003 and T-005 respectively) |
| Phase 3 | T-012 ∥ (T-008, T-010) — rendering tests run parallel to NLU and REPL tests |
| Phase 4 | (after T-015 + T-016 done, T-017 and T-018 can partially overlap) |
| Phase 5 | T-019 ∥ (can start after T-003, before T-020) |
| Phase 6 | T-026 ∥ (can start after T-003 + T-011, before T-025) |
| Phase 7 | T-030 ∥ T-031 |

### MVP Strategy (P1 Only)

1. Phase 1 + Phase 2 → Foundation
2. Phase 3 (US1) → Natural language REPL ← **MVP! Issue #35 core**
3. Phase 4 (US2) → Session persistence ← **MVP! Issue #35 resume**
4. **STOP**: Demoable: launch REPL, converse, exit, resume
5. Phase 5 (US3) → Slash commands (P2)
6. Phase 6 (US4) → Full inquiry cycle (P2)
7. Phase 7 (Polish) → Final quality

---

## Summary

| Phase | Tasks | Story | Priority | Lines (est.) |
|-------|-------|-------|----------|-------------|
| Phase 1: Setup | T-001–T-002 | Foundation | — | ~30 |
| Phase 2: Foundational | T-003–T-007 | Foundation | — | ~700 |
| Phase 3: US1 | T-008–T-014 | Natural Language REPL | P1 🎯 | ~1200 |
| Phase 4: US2 | T-015–T-018 | Session Persistence | P1 🎯 | ~800 |
| Phase 5: US3 | T-019–T-023 | Slash Commands | P2 | ~1000 |
| Phase 6: US4 | T-024–T-028 | Full Inquiry Cycle | P2 | ~900 |
| Phase 7: Polish | T-029–T-031 | Cross-cutting | — | ~400 |
| **Total** | **31 tasks** | — | — | **~5,030 lines** |

---

**Tasks Version**: 1.0.0 | **Last Updated**: 2026-05-18 | **Based on**: spec.md v1.0, plan.md v1.0 (Phase 0 & 1 Complete ✅), constitution.md v0.2.0
