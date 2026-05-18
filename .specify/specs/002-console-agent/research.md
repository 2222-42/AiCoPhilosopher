# Research: Console Agent — Technical Decisions

**Date**: 2026-05-18
**Feature**: 002-console-agent
**Source**: Specification `.specify/specs/002-console-agent/spec.md`, Constitution `.specify/memory/constitution.md` v0.2.0

---

## 1. REPL Input Framework

### Decision: prompt_toolkit

**Rationale**:
The specification requires readline-style command history (up/down arrows, Ctrl+R reverse search) per FR-027, plus input handling for both natural language and slash commands. prompt_toolkit provides:

1. **Native readline emulation**: Full GNU readline keybindings including `Ctrl+R` history search, `Ctrl+W` word delete, `Ctrl+A/E` line navigation. Cross-platform (Linux/macOS/Windows). This directly satisfies FR-027.
2. **Input validation**: Can intercept keystrokes before they reach the buffer — enables slash-command detection at first `/` character for immediate routing.
3. **Syntax highlighting**: Can colorize slash commands, system messages, and coordinator responses differently within the prompt area.
4. **Tab completion**: Framework supports it natively (deferred per open question #4 but architecture supports it).

**Alternatives considered**:
- **Rich's `Prompt` class**: Simpler API, already in dependencies, but lacks `Ctrl+R` history search and advanced keybinding customization. FR-027 explicitly requires reverse search, ruling this out.
- **Pure `readline` module**: Standard library but Windows support requires `pyreadline3` shim. No Rich integration. No syntax highlighting.
- **Custom input loop**: Would need to reimplement readline from scratch. Violates MVP-first principle.

**Trade-offs**:
- prompt_toolkit adds ~500KB to the dependency footprint. Acceptable for a desktop CLI tool.
- prompt_toolkit's async event loop (if using `asyncio` session) requires care when mixing with synchronous Coordinator calls. Mitigation: run the REPL in a synchronous `prompt_toolkit.shortcuts.PromptSession` with the Coordinator wrapped in an async-to-sync bridge (or use `asyncio.run()` for each turn).

---

## 2. NLU Intent Classification

### Decision: LLM-based classification (cheap tier) with rule-based fallback

**Rationale**:
The specification requires classifying 16 intent types from natural language input (FR-003) with a confidence threshold of 0.85 (FR-004). An LLM-based approach:

1. **Zero training data**: MVP can ship immediately using a system prompt with intent definitions and few-shot examples. No labeled dataset required.
2. **Handles linguistic variety**: Philosophical inquiry uses varied language ("Let's explore...", "What about...", "Could we consider...", "I wonder if...", "調べてみたい" in Japanese). Rule-based regex would be brittle.
3. **Constitution §3.5 cost-aware routing**: Classification is an "exploration/collection" task → cheap tier (Gemini Flash, DeepSeek). Adds ~$0.0001 per turn at Flash pricing.
4. **Japanese support**: LLM-based classification handles Japanese natively (spec requires Japanese + English per assumptions).

**Fallback**: When LLM is unavailable (offline mode, network failure):
- Pattern-match common phrases to intent types (e.g., "search for" → `start_inquiry`, "stop" → `pause_session`)
- For ambiguous input, ask clarifying questions (FR-004 already mandates this below 0.85 confidence)
- This satisfies Constitution Principle I (core independence — system degrades gracefully)

**Classification prompt structure**:
```
System: You are an intent classifier for a philosophical research REPL.
Given the user's input and conversation context, classify the intent as one of:
[start_inquiry, clarify_question, propose_workstream, steer_workstream, ...]
Return JSON: {"intent_type": "...", "confidence": 0.95, "extracted_entities": {...}, "needs_clarification": false}

User input: "Let's look into Frankfurt cases from the 1980s"
Context: Active project, no running workstreams
```

**Alternatives considered**:
- **Fine-tuned classifier** (DistilBERT, SetFit): Faster (<100ms), zero per-call cost, but requires 500+ labeled examples per intent type (16 × 500 = 8,000 samples). Training data collection is a multi-week effort. Post-MVP path: fine-tune on collected dialogue data from real usage.
- **Rule-based regex**: Fast and offline but cannot handle the linguistic variety of natural philosophical inquiry. Would fail on Japanese input entirely. Rejected.
- **Local embedding + cosine similarity**: Encode input with `all-MiniLM-L6-v2` (already in 001 stack), compare against embedded intent archetypes. Moderate accuracy but requires careful threshold tuning and struggles with multi-intent input.

**Trade-offs**:
- LLM latency: 0.5-2s per classification. SC-001 allows 10s for first response (NLU + coordinator), so this fits comfortably.
- Cost: At Gemini Flash pricing, 1,000 turns costs ~$0.10. Acceptable for MVP.
- Cold-start: First call may have higher latency while the LLM backend initializes. Mitigation: warm up LLM connection on REPL startup.

---

## 3. Async Workstream Status Surfacing

### Decision: Background polling thread + Rich Live display

**Rationale**:
The REPL is fundamentally synchronous — it blocks on user input via `prompt_toolkit`. But workstreams run asynchronously via LangGraph and can complete, fail, or request human judgment at any time (FR-024). The system must surface these updates without interrupting the user mid-typing.

**Architecture**:

```
┌─────────────────────────────────────────┐
│ REPL Main Thread (prompt_toolkit)        │
│                                           │
│  User types...                            │
│  ┌──────────────────────────┐            │
│  │ > Let's explore free will │            │
│  └──────────────────────────┘            │
│                                           │
│  [Enter pressed]                          │
│       ↓                                   │
│  1. Flush queued updates                 │
│  2. Process input (NLU → Coordinator)    │
│  3. Render response (progressive disc.)  │
│  4. Show next prompt                     │
│                                           │
│  [Rich Live status bar]                  │
│  WS-001: 60% | WS-002: complete         │
│  ↑ Updated by background thread         │
└─────────────────────────────────────────┘
         ↕ queue
┌─────────────────────────────────────────┐
│ Background Polling Thread (every 2s)      │
│                                           │
│  poll_workstreams(session)               │
│       ↓                                   │
│  Compare with last known states          │
│       ↓                                   │
│  If changes detected:                    │
│    - Update Rich Live display             │
│    - Queue non-urgent updates             │
│    - Queue approval requests              │
│    - Surface completions immediately      │
└─────────────────────────────────────────┘
```

**Update queuing rules**:
- **Status changes** (running → completed, running → failed): Queue and surface after current user input completes
- **Progress updates** (30% → 60%): Update Rich Live bar only (non-intrusive)
- **Approval requests** (human judgment required): Flash notification, surface immediately after current turn
- **Stalled workstreams**: Surface with warning icon at top of next prompt

**Alternatives considered**:
- **Signal-based interrupts** (SIGALRM): Would literally interrupt the user's typing. Terrible UX. Rejected.
- **Async REPL with asyncio**: prompt_toolkit supports `asyncio` sessions. Would allow true concurrent I/O but adds complexity (the Coordinator's LangGraph-based operations are already async). Post-MVP optimization.
- **Poll only on user input** (no background thread): Simplest but worst UX — user doesn't know workstream completed until they press Enter, which could be minutes later.

**Trade-offs**:
- Background thread adds minor complexity. Python's GIL means no true parallelism but I/O-bound polling (SQLite reads) benefits from threading.
- Poll interval of 2s means up to 2s delay on status updates. Acceptable per SC-006 (5s slash command execution).

---

## 4. Session Persistence Strategy

### Decision: Per-turn incremental SQLite writes + atomic graceful shutdown

**Rationale**:
FR-009 requires: "Every DialogueTurn MUST be persisted to SQLite before the coordinator's next response is rendered to the user." This is an incremental per-turn write model. Additionally, on graceful exit, the session must be finalized in a single transaction.

**Write flow**:

```
User input → NLU classification → Coordinator response
                                          ↓
                              BEFORE rendering response:
                              1. INSERT dialogue_turn (user)
                              2. INSERT dialogue_turn (coordinator)
                              3. UPDATE sessions (last_active_at, focus_json)
                              4. UPSERT context_blocks (if context changed)
                              5. INSERT approval_requests (if coordinator raised any)
                                          ↓
                              Render response
```

**Exit flow** (triggered by `/exit`, `/quit`, Ctrl+D, SIGTERM, SIGHUP, SIGINT):

```
BEGIN TRANSACTION
  UPDATE sessions SET status='paused', exit_reason='user_exit', last_active_at=CURRENT_TIMESTAMP
  COMMIT
```

**Crash recovery** (SIGKILL, power loss):
- On next startup, scan `sessions WHERE status='active'`
- For each: check if PID alive + heartbeat ≤ 5 min (FR-013)
- If stale: `UPDATE sessions SET status='paused', exit_reason='stale_reclaimed'`
- At most 1 in-flight turn lost (the one being processed when crash occurred)

**Concurrent session prevention**:
- `CREATE UNIQUE INDEX idx_sessions_one_active ON sessions(project_id) WHERE status = 'active'`
- Attempting to start a second session for a project with a live active session (PID alive, heartbeat current) triggers FR-013 warning
- Stale active sessions auto-reclaimed

**Alternatives considered**:
- **File-based JSON session dump**: Simpler but no ACID guarantees. Crash during write could corrupt entire session. Rejected.
- **LangGraph checkpointing for sessions**: LangGraph's `SqliteSaver` could theoretically store session state, but it's designed for graph execution state, not dialogue history with relational queries. Mismatched abstraction.
- **In-memory only + periodic flush**: Violates FR-009 (persist before render). Data loss risk on crash. Rejected.

---

## 5. Progressive Disclosure Rendering

### Decision: Rich Panel with toggle state per section

**Rationale**:
FR-007 mandates progressive disclosure: Summary + Epistemic Status + Active Workstreams always visible; Details and Suggestions collapsed by default, togglable via `/details` and `/suggestions`.

**Rendering format** (example from contracts/repl-commands.md §5):

```
**Summary**
Project: "Ontology of Software Abstraction" — Active
2 workstreams running, 1 completed

**Epistemic Status**
Active: 4 | Refuted: 1 | Under Review: 2 | Stalled: 0

**Active Workstreams**
WS-001: Literature Search — completed (23 papers)
WS-002: Concept Analysis — running (60%)

[Details]    ← collapsed by default
[List of hypotheses, recent claims, review round statuses]

[Suggestions] ← collapsed by default
"WS-001 is complete. Start Argumentation?"
```

**Implementation**:
- `rendering.py` holds a `DisclosureState` with booleans: `show_details`, `show_suggestions`
- These are toggled by `/details`, `/hide-details`, `/suggestions`, `/hide-suggestions`
- State persisted in `FocusContext.toggle_state` for session resumption
- On render, Rich `Panel` with `expand=show_*` controls visibility

**Alternatives considered**:
- **Rich Live with dynamic sections**: More interactive (expand/collapse with keyboard), but complex to implement and interferes with prompt_toolkit's keybinding handling. Post-MVP.
- **Two-pass render**: First render compact version, user types `/details` to re-render with full content. Simple but destroys the "progressive" feel — user must explicitly request every time.
- **Textual TUI**: Full widget-based UI would enable native expand/collapse but is a separate framework with its own event loop. Conflicts with prompt_toolkit. Deferred to post-MVP Web UI.

---

## 6. Clean Architecture Integration

### Decision: REPL as presentation layer; session entities in domain/

**Rationale**:
The Console Agent is a presentation-layer concern per Clean Architecture. It MUST NOT contain domain logic, business rules, or direct infrastructure access.

**Layer boundaries**:

| Layer | What lives here | What it depends on |
|-------|----------------|-------------------|
| **presentation/** | `repl.py`, `nlu.py`, `slash_commands.py`, `rendering.py`, `session_manager.py` | `application/`, `ports/`, `domain/entities/session.py` |
| **application/** | `coordinator.py` (existing, unwrapped) — REPL calls it via use-case interface | `domain/`, `ports/` |
| **domain/entities/** | `session.py` — SessionState, DialogueTurn, etc. (pure Pydantic models) | stdlib + pydantic only |
| **ports/** | `storage_port.py` — extended with session methods (`save_session`, `load_session`, etc.) | `domain/` |
| **infrastructure/adapters/** | `sqlite_adapter.py` — implements session CRUD behind StoragePort | `ports/` |

**Key rules**:
- `presentation/repl.py` calls `coordinator.process_input(intent)` — never directly manipulates domain state
- `presentation/session_manager.py` uses `StoragePort` for persistence — never touches SQLite directly
- `domain/entities/session.py` imports ONLY stdlib + pydantic — verifiable via `scripts/check_domain_purity.py`
- NLU classifier uses `LLMPort` for LLM calls — follows existing adapter pattern

---

## 7. Slash Command Routing

### Decision: Prefix-based routing with arg validation before dispatch

**Rationale**:
FR-005 and FR-006 define slash command behavior: input starting with `/` (after trimming leading whitespace) is routed to the slash command handler, bypassing NLU entirely. This provides unambiguous, fast execution for power users.

**Routing algorithm** (from contracts/repl-commands.md §3):

```
Input handler
  ├── Input.strip().startswith("/")?
  │   ├── YES → Slash Command Parser
  │   │   ├── Split: /<command> [args...]
  │   │   ├── Validate command exists in registry
  │   │   ├── Validate args against command spec (required, optional, type)
  │   │   ├── On validation failure: friendly error + usage hint
  │   │   └── Dispatch to handler (session/inquiry/steering/view/export)
  │   └── NO → NLU Intent Classifier → Coordinator
```

**Command registry** (28 commands defined in contracts/repl-commands.md):
- Session (7): `/help`, `/exit`, `/quit`, `/new`, `/open`, `/projects`, `/archive`
- Inquiry (6): `/search`, `/analyze`, `/argue`, `/review`, `/compare`, `/synthesize`
- Steering (5): `/pause`, `/resume`, `/steer`, `/deepen`, `/abandon`
- View (8): `/status`, `/hypotheses`, `/dead-ends`, `/document`, `/details`, `/hide-details`, `/suggestions`, `/hide-suggestions`
- Export/Data (3): `/export`, `/add-note`, `/upload`
- Help/Config (2): `/help-request`, `/config`

**Validation rules** (from contract §4):
- Unknown command → `"Unknown command: '/xyz'. Type /help for available commands."`
- Missing required args → usage hint
- Invalid IDs → list valid options
- Ambiguous omission → ask which one

**Alternatives considered**:
- **Dispatch through Coordinator**: Route slash commands through NLU → Coordinator like natural language. Simpler code but defeats purpose of slash commands (speed, precision, bypass NLU confidence issues). Rejected.
- **Subcommand-style CLI**: `/workstream pause ws-001` instead of `/pause ws-001`. More consistent with git/docker style but longer to type. Current flat style chosen for speed.

---

## 8. Command History Persistence

### Decision: prompt_toolkit FileHistory + session-scoped isolation

**Rationale**:
FR-027 requires command history to be persisted as part of session state. prompt_toolkit's `FileHistory` stores history as a plain text file (one command per line). Per-session isolation ensures history from different projects doesn't cross-contaminate.

**Storage**: `~/.aicophilosopher/sessions/<session_id>/history.txt`

**Features**:
- Up/down arrows: navigate previous commands within the session
- Ctrl+R: reverse incremental search through history
- History persists across REPL restarts (loaded with session resume)
- Max history size: configurable, default 10,000 entries

---

## 9. Summary of Technology Stack (002 additions)

| Layer | Technology | Version | Justification |
|-------|-----------|---------|---------------|
| REPL Input | prompt_toolkit | 3.0+ | Readline emulation, history, completion |
| NLU Classification | LLM (cheap tier via existing LLMPort) | — | Flexible, multilingual, zero training data |
| Terminal Rendering | Rich | 13+ | Already in 001; extended for progressive disclosure |
| Persistence | SQLite (via existing StoragePort) | — | Already in 001; new session tables added |
| Testing | pytest + pytest-asyncio + pytest-mock | — | Same as 001; mock LLM for deterministic NLU tests |

**Total new production dependencies**: 1 (prompt_toolkit). All other dependencies already in 001 stack.

---

## 10. Open Questions for Post-MVP

1. **Fine-tuned NLU classifier**: Is the latency reduction (2000ms → 100ms) worth the training data effort after collecting real usage data?
2. **Tab completion**: prompt_toolkit supports it natively. What should be completed? Slash commands, project IDs, workstream IDs, philosophical concept names?
3. **Async REPL event loop**: Would switching to prompt_toolkit's `asyncio` session eliminate the need for a background polling thread? Trade-off: complexity vs. cleaner architecture.
4. **Syntax highlighting in user input**: Could the REPL highlight slash commands, quoted text, and tradition names in different colors as the user types?
5. **Multi-line input**: Should the REPL support multi-line input for long philosophical questions (e.g., via `\` continuation or Shift+Enter)?

---

**Research Version**: 1.0.0 | **Last Updated**: 2026-05-18
