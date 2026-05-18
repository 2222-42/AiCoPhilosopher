# Quickstart: Console Agent REPL Development

**Date**: 2026-05-18
**Feature**: 002-console-agent
**Audience**: Developers contributing to the Console Agent feature

---

## 1. Prerequisites

- Python 3.11 or higher
- Existing 001-aicophilosopher development environment set up (see `../001-aicophilosopher/quickstart.md`)
- Git
- (Optional) Anthropic API key for NLU classification (falls back to rule-based otherwise)
- (Optional) Google API key for Gemini Flash NLU (cheaper tier)

## 2. Environment Setup

### 2.1 Install Console Agent Dependencies

```bash
# From project root
cd aicophilosopher

# Activate existing virtual environment
source .venv/bin/activate  # Linux/macOS

# Install new dependency
pip install "prompt_toolkit>=3.0"
```

### 2.2 Verify Installation

```bash
# Check prompt_toolkit is available
python -c "from prompt_toolkit import PromptSession; print('OK')"

# Run existing test suite to ensure no regressions
python -m pytest tests/ -q
```

## 3. Project Structure for Console Agent Development

```text
src/aicophilosopher/
├── domain/
│   └── entities/
│       └── session.py              # NEW: All 6 session entities + enums
├── presentation/
│   ├── cli.py                      # MODIFIED: Launch REPL mode via `aicophilosopher`
│   ├── repl.py                     # NEW: Main REPL loop
│   ├── nlu.py                      # NEW: NLU intent classifier
│   ├── slash_commands.py           # NEW: Slash command parser/router
│   ├── rendering.py                # NEW: Progressive disclosure renderer
│   └── session_manager.py          # NEW: Session persistence manager

tests/
├── unit/
│   ├── domain/
│   │   └── test_session.py         # NEW: Session entity validation
│   └── presentation/
│       ├── test_nlu.py             # NEW: NLU intent classification
│       ├── test_slash_commands.py  # NEW: Command parsing/routing
│       ├── test_rendering.py       # NEW: Progressive disclosure output
│       └── test_session_manager.py # NEW: Session CRUD, stale reclaim

prompts/
└── nlu/
    └── intent_classifier.md        # NEW: NLU system prompt

.specify/specs/002-console-agent/
├── spec.md                         # Feature specification
├── plan.md                         # Implementation plan
├── research.md                     # Technical decisions
├── data-model.md                   # Entity definitions + SQLite schema
├── quickstart.md                   # This file
└── contracts/
    ├── repl-commands.md            # Slash command reference
    ├── nlu-intent-schema.md        # NLU intent types and schemas
    └── repl-rendering.md           # Rendering format contract
```

## 4. Running the REPL

### 4.1 Launch (Post-Implementation)

```bash
# Start interactive REPL session
aicophilosopher

# Or with a specific project
aicophilosopher --project proj-a1b2c3d4

# Or start a new project directly
aicophilosopher --new "What is the nature of truth?"
```

### 4.2 Basic REPL Workflow

```text
$ aicophilosopher

Welcome to AiCoPhilosopher — your philosophical research collaborator.

Projects:
  1. "Ontology of Software Abstraction" — last active 2026-05-17
  2. "Free Will and Determinism" — last active 2026-05-15
  3. "Ethics of AI" — last active 2026-05-10

Select a project (1-3), enter a project ID, or type a question to start fresh:

> I want to explore whether abstraction in software engineering has philosophical grounding beyond just engineering practice.

Coordinator:
┌─ Summary ─────────────────────────────────────────────────────────────┐
│ That's a rich question that touches on ontology (what is abstraction?),│
│ philosophy of technology (how do artifacts embody abstract concepts?), │
│ and philosophy of mathematics (what makes an abstraction valid?).      │
│ Before I launch workstreams, let me clarify your angle...              │
└────────────────────────────────────────────────────────────────────────┘
┌─ Epistemic Status ────────────────────────────────────────────────────┐
│ Confidence: 0.9 | Tradition: Philosophy of Technology                 │
└────────────────────────────────────────────────────────────────────────┘

> I'm specifically interested in whether software abstractions have ontological status — are they real in the same way mathematical objects are?

...conversation continues...

> /status
┌─ Summary ─────────────────────────────────────────────────────────────┐
│ Project: "Ontology of Software Abstraction" — Active                  │
│ 2 workstreams running, 1 completed, 4 hypotheses active              │
└────────────────────────────────────────────────────────────────────────┘

> /exit
Session saved. Goodbye!
```

### 4.3 Slash Commands Quick Reference

| Category | Commands |
|----------|----------|
| Session | `/help`, `/exit`, `/new`, `/open`, `/projects`, `/archive` |
| Inquiry | `/search`, `/analyze`, `/argue`, `/review`, `/compare`, `/synthesize` |
| Steering | `/pause`, `/resume`, `/steer`, `/deepen`, `/abandon` |
| View | `/status`, `/hypotheses`, `/dead-ends`, `/document`, `/details`, `/suggestions` |
| Export | `/export`, `/add-note`, `/upload` |
| Config | `/help-request`, `/config` |

Full reference: `.specify/specs/002-console-agent/contracts/repl-commands.md`

## 5. Development Commands

### 5.1 Testing

```bash
# Run all tests (including new Console Agent tests)
python -m pytest tests/ -q

# Run Console Agent-specific tests
python -m pytest tests/unit/presentation/ -v
python -m pytest tests/unit/domain/test_session.py -v

# Run NLU accuracy tests (requires mock LLM responses)
python -m pytest tests/unit/presentation/test_nlu.py -v

# Run integration tests (REPL loop with mock coordinator)
python -m pytest tests/integration/test_repl_loop.py -v

# Run with coverage
python -m pytest tests/ --cov=src/aicophilosopher/presentation --cov=src/aicophilosopher/domain/entities/session.py --cov-report=html
```

### 5.2 Code Quality

```bash
# Format
ruff format src/aicophilosopher/presentation/ tests/unit/presentation/

# Lint
ruff check src/aicophilosopher/presentation/ tests/unit/presentation/

# Type check (including new session entities)
mypy src/aicophilosopher/presentation/ src/aicophilosopher/domain/entities/session.py

# Domain purity check (ensure session.py only imports stdlib + pydantic)
python scripts/check_domain_purity.py

# All quality gates
make check  # or: ruff check && mypy && pytest tests/ -q && python scripts/check_domain_purity.py
```

### 5.3 Manual REPL Testing

```bash
# Launch REPL in test mode (mock coordinator, no LLM required)
python -m aicophilosopher --test-mode

# Test specific scenarios
# 1. Natural language inquiry
> I want to explore free will

# 2. Slash command routing
> /help

# 3. Session persistence
> /exit
python -m aicophilosopher  # Resume session

# 4. Concurrent session detection
# (Open two terminals, try to open same project)
```

### 5.4 Database Inspection

```bash
# Inspect session data
sqlite3 ~/.aicophilosopher/metadata.db

# List sessions
SELECT session_id, project_id, status, exit_reason, last_active_at FROM sessions;

# View dialogue history for a session
SELECT speaker, substr(content, 1, 100), timestamp
FROM dialogue_turns
WHERE session_id = '<session_id>'
ORDER BY timestamp;

# Check pending approval requests
SELECT request_type, description, urgency, resolved_at
FROM approval_requests
WHERE session_id = '<session_id>' AND resolved_at IS NULL;

# View context blocks
SELECT label, summary, created_at FROM context_blocks WHERE session_id = '<session_id>';
```

## 6. Key Architecture Points

### 6.1 Layer Boundaries (Critical)

```
presentation/repl.py
    ↓ calls
application/orchestration/coordinator.py  (existing)
    ↓ uses
ports/llm_port.py                          (existing, used by NLU)
ports/storage_port.py                      (existing, extended for sessions)
    ↓ implemented by
infrastructure/adapters/sqlite_adapter.py  (existing, extended)

domain/entities/session.py                 (NEW — pure Pydantic, no deps)
```

**Rule**: `presentation/` NEVER imports from `infrastructure/`. All I/O goes through `ports/`.

### 6.2 NLU Classification Flow

```
User input → repl.py
    ├── Starts with "/"? → slash_commands.py → dispatch to handler
    └── Otherwise → nlu.py → LLMPort.generate(classifier_prompt + input)
            ├── confidence ≥ 0.85 → return UserIntent
            └── confidence < 0.85 → return UserIntent(needs_clarification=True)
    → coordinator.process_input(intent)
    → rendering.py → Rich output
    → session_manager.py → persist turn
```

### 6.3 Session Persistence Lifecycle

```
REPL START
    ├── No --project? → session_manager.list_projects() → user selects
    ├── --project <id>? → session_manager.load_or_create(project_id)
    └── --new? → create project + session

REPL LOOP (each turn)
    ├── session_manager.persist_turn(user_turn)
    ├── coordinator.process(intent)
    ├── rendering.render(response)
    └── session_manager.persist_turn(coordinator_turn)

REPL EXIT (/exit, Ctrl+D, SIGTERM)
    └── session_manager.finalize(reason)  [single transaction]
```

## 7. Common Issues

| Issue | Solution |
|-------|----------|
| prompt_toolkit not found | `pip install "prompt_toolkit>=3.0"` |
| NLU classification slow on first call | Normal: LLM backend cold start. Warm up on REPL launch. |
| Session appears "active" after crash | Run `aicophilosopher --reclaim-stale` or auto-reclaim on next startup |
| Rich panels overlapping weirdly | Check terminal width ≥ 80 columns. Rich auto-wraps at smaller widths. |
| Concurrent session conflict | Kill stale process or use `aicophilosopher --force-open <project>` |
| History not persisting | Check write permissions on `~/.aicophilosopher/sessions/` |

## 8. Contributing

1. Create feature branch from `feature/002-console-agent-plan`
2. Implement one task from `tasks.md` (TDD: test → impl → green)
3. Run quality gates: `ruff check && mypy && pytest tests/ -q && python scripts/check_domain_purity.py`
4. Commit with conventional commit: `feat(repl): description`
5. Push and create chained draft PR

See `.specify/memory/constitution.md` for all quality requirements.

---

**Quickstart Version**: 1.0.0 | **Last Updated**: 2026-05-18
