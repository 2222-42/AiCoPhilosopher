# Data Model: Console Agent Session Entities

**Date**: 2026-05-18
**Feature**: 002-console-agent
**Source**: Specification `.specify/specs/002-console-agent/spec.md`

---

## 1. Entity Relationship Diagram

```
SessionState (1 per active REPL session)
├── DialogueTurn (0..n) ── grouped into ──→ ContextBlock (0..n)
├── FocusContext (1)
│   └── PendingDecision (0..n)
├── ApprovalRequest (0..n)
└── references ──→ WorkstreamHandle (0..n) [from 001 data model]
```

---

## 2. Core Entities

### 2.1 SessionState

Root entity for the REPL session. Persisted to SQLite on `/exit`; loaded on resume.

```python
class SessionState(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    status: SessionStatus = Field(default=SessionStatus.active)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dialogue_history: list[DialogueTurn] = Field(default_factory=list)
    context_blocks: list[ContextBlock] = Field(default_factory=list)
    current_focus: FocusContext = Field(default_factory=FocusContext)
    pending_approvals: list[ApprovalRequest] = Field(default_factory=list)
    active_workstreams: list[str] = Field(default_factory=list)  # Workstream IDs
    exit_reason: Optional[str] = None  # "user_exit", "sigterm", "crash"
    config_snapshot: dict[str, Any] = Field(default_factory=dict)

class SessionStatus(str, Enum):
    active = "active"       # REPL is currently running
    paused = "paused"       # Exited gracefully; can be resumed
    closed = "closed"       # Terminal session; cannot be resumed (archived project)
```

**Validation rules**:
- `project_id` MUST reference an existing project in the `projects` table
- `status` transitions: `active → paused` (on exit), `paused → active` (on resume), `* → closed` (on project archive)
- A project MUST NOT have more than one session with `status == active`
- `dialogue_history` ordering: MUST be in chronological order (ascending timestamp)
- `active_workstreams`: All entries MUST be valid workstream IDs within the project

### 2.2 DialogueTurn

```python
class DialogueTurn(BaseModel):
    turn_id: UUID = Field(default_factory=uuid4)
    speaker: SpeakerType
    content: str = Field(..., min_length=1)
    intent: Optional[UserIntent] = None       # Only for user turns
    actions_taken: list[ActionTaken] = Field(default_factory=list)  # Only for coordinator turns
    context_id: Optional[UUID] = None          # Which ContextBlock this belongs to
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_by_user: Optional[bool] = None    # For approval-response turns

class SpeakerType(str, Enum):
    user = "user"
    coordinator = "coordinator"
    system = "system"  # e.g., "Workstream WS-001 completed", "Connection lost"
```

**Validation rules**:
- `intent` MUST be present for `speaker == "user"` turns
- `actions_taken` MUST be present for `speaker == "coordinator"` turns
- `context_id`: If present, MUST reference a valid ContextBlock ID
- `approved_by_user`: MUST be present when the turn is a response to an ApprovalRequest

### 2.3 UserIntent

```python
class UserIntent(BaseModel):
    intent_type: IntentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    extracted_entities: dict[str, Any] = Field(default_factory=dict)
    raw_input: str                                         # Original user input
    alternative_intents: list[AlternativeIntent] = Field(default_factory=list)
    needs_clarification: bool = Field(default=False)

class IntentType(str, Enum):
    start_inquiry = "start_inquiry"
    clarify_question = "clarify_question"
    propose_workstream = "propose_workstream"
    steer_workstream = "steer_workstream"
    request_status = "request_status"
    request_detail = "request_detail"
    request_export = "request_export"
    approve_action = "approve_action"
    reject_action = "reject_action"
    ask_question = "ask_question"
    inject_information = "inject_information"
    request_help = "request_help"
    pause_session = "pause_session"
    resume_session = "resume_session"
    archive_project = "archive_project"
    compare_traditions = "compare_traditions"

class AlternativeIntent(BaseModel):
    intent_type: IntentType
    confidence: float
    rationale: str
```

**Validation rules**:
- `confidence`: 0.0–1.0. Below 0.85 (default threshold), `needs_clarification` MUST be True.
- `extracted_entities`: Common keys include `workstream_id`, `concept_name`, `topic`, `tradition`, `file_path`, `format`, `section_name`
- `alternative_intents`: MUST contain at most 3 entries; ordered by confidence descending

### 2.4 ContextBlock

```python
class ContextBlock(BaseModel):
    context_id: UUID = Field(default_factory=uuid4)
    label: str = Field(..., min_length=1, max_length=200)
    turns: list[UUID] = Field(default_factory=list)      # DialogueTurn IDs
    summary: str = Field(default="")                      # Auto-generated by LLM
    parent_context: Optional[UUID] = None                 # For branching discussions
    epistemic_state: EpistemicSnapshot = Field(default_factory=EpistemicSnapshot)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None                  # When context is no longer active

class EpistemicSnapshot(BaseModel):
    active_claims: list[str] = Field(default_factory=list)   # Claim IDs
    hypotheses_discussed: list[str] = Field(default_factory=list)  # Hypothesis IDs
    workstreams_active: list[str] = Field(default_factory=list)    # Workstream IDs
    key_conclusions: list[str] = Field(default_factory=list)       # Brief text summaries
```

**Validation rules**:
- `label`: Human-readable, unique within a session (e.g., "Compatibilism literature survey", "Frankfurt case analysis")
- `turns`: All IDs MUST be valid DialogueTurn IDs within the same session
- `parent_context`: If present, MUST be a valid ContextBlock ID within the same session
- `summary`: Auto-generated by LLM summarization when context is closed; empty string while active

### 2.5 FocusContext

```python
class FocusContext(BaseModel):
    active_topic: str = Field(default="")
    last_workstream_id: Optional[str] = None
    last_hypothesis_id: Optional[str] = None
    pending_decisions: list[PendingDecision] = Field(default_factory=list)
    recent_claim_ids: list[str] = Field(default_factory=list)  # Last N claim IDs (N=10)
    last_context_id: Optional[UUID] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PendingDecision(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    decision_type: DecisionType
    description: str
    presented_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None  # If decision is time-sensitive

class DecisionType(str, Enum):
    workstream_approval = "workstream_approval"
    normative_judgment = "normative_judgment"
    incommensurability_resolution = "incommensurability_resolution"
    review_escalation = "review_escalation"
    goal_refinement = "goal_refinement"
```

**Validation rules**:
- `active_topic`: Updated on every coordinator response to reflect the current discussion thread
- `last_workstream_id`: Set when a workstream is explicitly mentioned by user or coordinator
- `pending_decisions`: MUST be pruned when the user responds to them
- `recent_claim_ids`: FIFO buffer of last N claims (N configurable, default 10)

### 2.6 ApprovalRequest

```python
class ApprovalRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    request_type: ApprovalRequestType
    description: str = Field(..., min_length=10)
    options: list[ApprovalOption] = Field(default_factory=list)
    urgency: Urgency = Field(default=Urgency.non_blocking)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    user_choice: Optional[int] = None            # Index into options list
    user_comment: Optional[str] = None

class ApprovalRequestType(str, Enum):
    workstream_proposal = "workstream_proposal"
    normative_judgment = "normative_judgment"
    incommensurability_resolution = "incommensurability_resolution"
    review_escalation = "review_escalation"
    external_search_consent = "external_search_consent"
    synthesis_conflict = "synthesis_conflict"

class ApprovalOption(BaseModel):
    index: int
    label: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    consequences: str = Field(default="")  # What happens if chosen

class Urgency(str, Enum):
    blocking = "blocking"       # Workstream cannot proceed until resolved
    non_blocking = "non_blocking"  # Workstream continues; can be resolved later
```

**Validation rules**:
- `options`: MUST contain at least 1 option; at most 5
- A request is considered "pending" if `resolved_at is None`
- On session resume, all pending requests (`resolved_at is None`) MUST be re-presented to the user
- `urgency == "blocking"` requests are surfaced immediately; `non_blocking` may be batched or deferred

### 2.7 ActionTaken

```python
class ActionTaken(BaseModel):
    action_type: ActionType
    target_id: Optional[str] = None       # Workstream ID, hypothesis ID, etc.
    description: str
    result: Optional[str] = None          # Brief result description
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ActionType(str, Enum):
    created_project = "created_project"
    refined_goal = "refined_goal"
    launched_workstream = "launched_workstream"
    paused_workstream = "paused_workstream"
    resumed_workstream = "resumed_workstream"
    steered_workstream = "steered_workstream"
    ingested_pdf = "ingested_pdf"
    synthesized_document = "synthesized_document"
    exported_document = "exported_document"
    added_note = "added_note"
    escalated_to_user = "escalated_to_user"
    archived_project = "archived_project"
```

---

## 3. SQLite Schema Additions

These tables are added to the existing 001-aicophilosopher SQLite schema.

```sql
-- Sessions
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'closed')),
    focus_json TEXT DEFAULT '{}',
    pending_approvals_json TEXT DEFAULT '[]',
    active_workstreams_json TEXT DEFAULT '[]',
    exit_reason TEXT,
    config_snapshot_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dialogue Turns
CREATE TABLE dialogue_turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    speaker TEXT NOT NULL CHECK (speaker IN ('user', 'coordinator', 'system')),
    content TEXT NOT NULL,
    intent_json TEXT,                     -- UserIntent (null for coordinator/system)
    actions_json TEXT,                    -- [ActionTaken] (null for user/system)
    context_id TEXT,                      -- ContextBlock ID (nullable)
    approved_by_user BOOLEAN,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Context Blocks
CREATE TABLE context_blocks (
    context_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    turns_json TEXT DEFAULT '[]',         -- [turn_id, ...]
    summary TEXT DEFAULT '',
    parent_context TEXT,
    epistemic_snapshot_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_sessions_project ON sessions(project_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_dialogue_turns_session ON dialogue_turns(session_id);
CREATE INDEX idx_dialogue_turns_timestamp ON dialogue_turns(timestamp);
CREATE INDEX idx_dialogue_turns_context ON dialogue_turns(context_id);
CREATE INDEX idx_context_blocks_session ON context_blocks(session_id);
```

---

## 4. Key Invariants

1. **One active session per project**: At most one `sessions` row per `project_id` can have `status == 'active'` at any time.

2. **Dialogue history completeness**: Every `DialogueTurn` within a session MUST be persisted to SQLite before the coordinator's next response is rendered to the user.

3. **Context block consistency**: A `DialogueTurn.context_id` MUST reference a `ContextBlock` within the same session, or be NULL.

4. **Focus freshness**: `FocusContext.updated_at` MUST be updated on every coordinator response, reflecting the state AFTER the response's actions are taken.

5. **Approval resolution**: Every `ApprovalRequest` with `resolved_at IS NOT NULL` MUST have `user_choice` set to a valid option index.

6. **Session atomicity**: On `/exit`, the full `SessionState` (session row + all pending dialogue_turns + all context_blocks) MUST be written atomically. Partial writes are rolled back.

7. **Crash recovery**: The latest committed `SessionState` snapshot is authoritative. On crash, the system recovers from the most recent snapshot. The most recent unpersisted dialogue turn (if any) is lost.

---

**Data Model Version**: 1.0.0 | **Last Updated**: 2026-05-18
