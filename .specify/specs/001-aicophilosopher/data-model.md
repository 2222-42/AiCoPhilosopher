# Data Model: AiCoPhilosopher v2.0

**Date**: 2026-05-13  
**Feature**: AiCoPhilosopher v2.0  
**Source**: Specification `.specify/specs/001-aicophilosopher/spec.md`

---

## 1. Entity Relationship Diagram

```
ProjectState (1)
├── WorkstreamState (0..n)
│   ├── ProgressUpdate (0..n)
│   ├── ReviewRound (0..n)
│   ├── UncertaintyFlag (0..n)
│   └── FailedExploration (0..n)
├── HypothesisRecord (0..n)
│   ├── Reference (0..n)
│   └── CounterArgument (0..n)
├── DialecticalMove (0..n)
├── ConceptNode (0..n) [genealogy tree]
├── UncertaintyRecord (0..n)
├── Artifact (0..n)
└── Message (0..n) [messaging queue]
```

---

## 2. Core Entities

### 2.1 ProjectState

Root aggregate. Represents a single philosophical research project.

```python
class ProjectState(BaseModel):
    project_id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=500)
    original_question: str = Field(..., min_length=1)
    status: ProjectStatus = Field(default=ProjectStatus.created)
    refined_goals: list[GoalStatement] = Field(default_factory=list)
    workstreams: dict[str, WorkstreamState] = Field(default_factory=dict)
    living_document: str = Field(default="")
    dialectical_history: list[DialecticalMove] = Field(default_factory=list)
    hypotheses: list[HypothesisRecord] = Field(default_factory=list)
    conceptual_genealogy: dict[str, ConceptNode] = Field(default_factory=dict)
    uncertainty_registry: list[UncertaintyRecord] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    metadata: ProjectMetadata = Field(default_factory=ProjectMetadata)
    external_layer_config: ExternalConfig | None = Field(default=None)
    notes: list[Note] = Field(default_factory=list)

    # Validation
    @field_validator("living_document")
    @classmethod
    def validate_yaml_frontmatter(cls, v: str) -> str:
        if v and not v.startswith("---"):
            raise ValueError("living_document must start with YAML frontmatter")
        return v
```

**ProjectStatus enum**:
```python
class ProjectStatus(str, Enum):
    created = "created"
    clarifying = "clarifying"
    goals_approved = "goals_approved"
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"
```

**Validation rules**:
- `title`: 1-500 characters, non-empty
- `original_question`: minimum 1 character (vague questions are expected; the clarification dialogue refines them)
- `status`: MUST follow the lifecycle state transitions (see §4.1)
- `living_document`: If non-empty, MUST start with YAML frontmatter (`---`)
- `refined_goals`: Must have at least 1 goal before workstreams can be created

**State transitions**:
```
created → clarifying → goals_approved → active → paused → completed | archived
```

**Supporting types**:
```python
class ProjectMetadata(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1, ge=1)
    tags: list[str] = Field(default_factory=list)

class ExternalConfig(BaseModel):
    hermes_enabled: bool = Field(default=False)
    hermes_endpoint: str | None = Field(default=None)
    opencode_enabled: bool = Field(default=False)
    opencode_endpoint: str | None = Field(default=None)
    consent_given_at: datetime | None = Field(default=None)  # When user consented to external calls
```

### 2.2 WorkstreamState

Child aggregate. Represents a single parallel investigation thread.

```python
class WorkstreamState(BaseModel):
    workstream_id: str = Field(default_factory=lambda: f"ws-{uuid4().hex[:8]}")
    type: WorkstreamType
    status: WorkstreamStatus = Field(default=WorkstreamStatus.pending)
    goal_statement: GoalStatement
    assigned_coordinator: str  # Agent identifier (e.g., "concept_analysis_coordinator")
    assigned_sub_agents: list[str] = Field(default_factory=list)
    results: str = Field(default="")  # Compiled report Markdown
    incremental_updates: list[ProgressUpdate] = Field(default_factory=list)
    review_rounds: list[ReviewRound] = Field(default_factory=list)
    uncertainty_flags: list[UncertaintyFlag] = Field(default_factory=list)
    failed_explorations: list[FailedExploration] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**WorkstreamType enum**:
```python
class WorkstreamType(str, Enum):
    literature_search = "literature_search"
    concept_analysis = "concept_analysis"
    cross_traditional_comparison = "cross_traditional_comparison"
    argumentation = "argumentation"
    critical_review = "critical_review"
    phenomenological_description = "phenomenological_description"  # Post-MVP
    ethical_analysis = "ethical_analysis"  # Post-MVP
    synthesis = "synthesis"
```

**WorkstreamStatus enum**:
```python
class WorkstreamStatus(str, Enum):
    pending = "pending"           # Created but not started
    running = "running"           # Active execution
    paused = "paused"             # User or system paused
    completed = "completed"       # Successfully finished with approved report
    failed = "failed"             # Terminated with unresolvable error
    stalled = "stalled"           # Non-terminating review or intractable disagreement; awaiting user
```

**State transition rules**:
```
pending → running (on user approval)
running → paused (on user command or system interrupt)
paused → running (on user resume)
running → completed (on successful review approval)
running → failed (on unresolvable error)
running → stalled (on max review rounds exceeded or intractable disagreement)
stalled → running (on user steering/override)
stalled → failed (on user abandonment)
paused → stalled (if pause reason is intractable disagreement)
```

**Invariant**: A workstream in `running` status MUST have at least one assigned coordinator and a non-empty `goal_statement`.

### 2.3 HypothesisRecord

Immutable history entry. All hypotheses including refuted and abandoned are retained permanently.

```python
class HypothesisRecord(BaseModel):
    hypothesis_id: str = Field(default_factory=lambda: f"hyp-{uuid4().hex[:8]}")
    statement: str = Field(..., min_length=10)
    strength: HypothesisStrength
    origin: Origin
    supporting_evidence: list[Reference] = Field(default_factory=list)
    counter_arguments: list[CounterArgument] = Field(default_factory=list)
    dialectical_children: list[str] = Field(default_factory=list)  # IDs of refined/replaced hypotheses
    status: HypothesisStatus
    epistemic_tradition: str | None = Field(default=None)  # e.g., "analytic", "phenomenological"
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    abandoned_at: datetime | None = Field(default=None)
    abandonment_reason: str | None = Field(default=None)
```

**HypothesisStrength enum**:
```python
class HypothesisStrength(str, Enum):
    strong = "strong"
    moderate = "moderate"
    weak = "weak"
    refuted = "refuted"
    underdetermined = "underdetermined"
```

**Origin enum**:
```python
class Origin(str, Enum):
    user = "user"
    ai = "ai"
    joint = "joint"
    cross_tradition_synthesis = "cross_tradition_synthesis"
```

**HypothesisStatus enum**:
```python
class HypothesisStatus(str, Enum):
    active = "active"
    abandoned = "abandoned"
    refined = "refined"      # Replaced by a dialectical_child
    refuted = "refuted"      # Conclusively counter-argued
```

**Validation rules**:
- `confidence_score`: 0.0–1.0 inclusive
- If `status == "abandoned"`, `abandoned_at` and `abandonment_reason` MUST be non-null
- If `status == "refined"`, `dialectical_children` MUST contain at least one hypothesis ID
- `statement`: minimum 10 characters (must be substantive)

### 2.4 UncertaintyRecord

Tracks the epistemic status of a specific claim within the project.

```python
class UncertaintyRecord(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"claim-{uuid4().hex[:8]}")
    claim_text: str = Field(..., min_length=5)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    counter_argument_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    tradition_validity: dict[str, float] = Field(default_factory=dict)  # {tradition: validity_score}
    review_status: ReviewStatus
    stalled_sections: list[str] = Field(default_factory=list)  # Document section IDs
    source_workstream: str | None = Field(default=None)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
```

**ReviewStatus enum**:
```python
class ReviewStatus(str, Enum):
    unreviewed = "unreviewed"
    under_review = "under_review"
    contested = "contested"                          # Reviewers disagree
    accepted_with_reservations = "accepted_with_reservations"
    rejected = "rejected"
```

**Validation rules**:
- `confidence_score` + `counter_argument_strength` ≤ 1.5 (soft constraint; flagged if exceeded)
- `tradition_validity`: Each score must be 0.0–1.0; keys must be registered tradition IDs
- `claim_text`: Minimum 5 characters

**Business rule**: When `review_status` transitions to `rejected`, the Synthesis Agent MUST remove the claim from the active living document and append it to the Dialectical Appendix with a deprecation annotation.

### 2.5 DialecticalMove

Records a single step in the dialectical history: an argument, refutation, revision, or conceptual shift.

```python
class DialecticalMove(BaseModel):
    move_id: str = Field(default_factory=lambda: f"dm-{uuid4().hex[:8]}")
    move_type: DialecticalMoveType
    source_agent: str
    target_hypothesis: str | None = Field(default=None)  # Hypothesis ID
    description: str
    premises: list[str] = Field(default_factory=list)
    conclusion: str | None = Field(default=None)
    references: list[Reference] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

**DialecticalMoveType enum**:
```python
class DialecticalMoveType(str, Enum):
    argument_proposed = "argument_proposed"
    argument_refuted = "argument_refuted"
    concept_revised = "concept_revised"
    hypothesis_abandoned = "hypothesis_abandoned"
    hypothesis_refined = "hypothesis_refined"
    tradition_bridge_proposed = "tradition_bridge_proposed"
    incommensurability_flagged = "incommensurability_flagged"
    review_verdict = "review_verdict"
    user_steering = "user_steering"
```

### 2.6 ConceptNode

Node in the conceptual genealogy tree.

```python
class ConceptNode(BaseModel):
    node_id: str = Field(default_factory=lambda: f"cn-{uuid4().hex[:8]}")
    concept_name: str
    tradition: str
    definition: str
    necessary_conditions: list[str] = Field(default_factory=list)
    sufficient_conditions: list[str] = Field(default_factory=list)
    distinctions: list[Distinction] = Field(default_factory=list)
    parent_concepts: list[str] = Field(default_factory=list)  # Node IDs
    child_concepts: list[str] = Field(default_factory=list)   # Node IDs
    thought_experiments: list[ThoughtExperiment] = Field(default_factory=list)
    historical_development: list[HistoricalMoment] = Field(default_factory=list)
```

**Supporting types**:
```python
class Distinction(BaseModel):
    distinction_name: str
    side_a: str
    side_b: str
    examples: list[str] = Field(default_factory=list)

class ThoughtExperiment(BaseModel):
    name: str
    scenario: str
    intended_insight: str
    epistemic_status: str  # e.g., "widely_accepted", "contested"

class HistoricalMoment(BaseModel):
    philosopher: str
    text: str
    contribution: str
    approximate_date: str | None = None
```

### 2.7 ReviewRound

Represents one iteration of the multi-agent review process.

```python
class ReviewRound(BaseModel):
    round_number: int = Field(..., ge=1)
    reviewer_verdicts: list[ReviewerVerdict] = Field(default_factory=list)
    revision_request: str | None = Field(default=None)
    status: ReviewRoundStatus
    escalated_to_coordinator: bool = Field(default=False)
    escalation_reason: str | None = Field(default=None)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = Field(default=None)

class ReviewerVerdict(BaseModel):
    reviewer_id: str
    reviewer_lens: str  # Methodological lens (e.g., "analytic_logician", "phenomenological_critic")
    status: ReviewerVerdictStatus
    comments: str
    identified_issues: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)

class ReviewerVerdictStatus(str, Enum):
    approved = "approved"
    approved_with_reservations = "approved_with_reservations"
    rejected = "rejected"
    needs_clarification = "needs_clarification"

class ReviewRoundStatus(str, Enum):
    in_progress = "in_progress"
    completed = "completed"
    escalated = "escalated"
```

**Validation rules**:
- `round_number`: Sequential integers starting at 1
- Max `round_number`: 5 (hard limit per plan.md §9)
- If `status == "escalated"`, `escalated_to_coordinator` MUST be True and `escalation_reason` non-null
- A round is `completed` only if ALL verdicts are `approved` or `approved_with_reservations`

### 2.8 Message (Inter-Agent Protocol)

Standardized envelope for all inter-agent communication.

```python
class Message(BaseModel):
    message_id: UUID = Field(default_factory=uuid4)
    sender_id: str  # Agent identifier (e.g., "project_coordinator", "ws-001")
    recipient_id: str  # Agent identifier or "broadcast"
    message_type: MessageType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    epistemic_status: EpistemicStatus = Field(default_factory=EpistemicStatus)
    correlation_id: UUID | None = Field(default=None)  # For request/response pairing

class MessageType(str, Enum):
    status_update = "status_update"
    delegation_request = "delegation_request"
    delegation_response = "delegation_response"
    steering_command = "steering_command"
    steering_ack = "steering_ack"
    help_request = "help_request"
    help_response = "help_response"
    review_request = "review_request"
    review_response = "review_response"
    result_delivery = "result_delivery"
    error_notification = "error_notification"
    user_notification = "user_notification"

class EpistemicStatus(BaseModel):
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    review_status: ReviewStatus = Field(default=ReviewStatus.unreviewed)
    tradition_context: list[str] = Field(default_factory=list)
    uncertainty_flags: list[str] = Field(default_factory=list)
```

**Validation rules**:
- `sender_id` and `recipient_id` MUST match registered agent identifiers in the project
- `message_type` determines the expected schema of `payload` (enforced by payload validators)
- `timestamp` MUST be UTC

### 2.9 GoalStatement

Represents a refined, user-approved research goal.

```python
class GoalStatement(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal-{uuid4().hex[:8]}")
    description: str = Field(..., min_length=20)
    success_criteria: list[str] = Field(default_factory=list)
    priority: int = Field(default=1, ge=1, le=5)  # 1 = highest
    approved_by_user: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: datetime | None = Field(default=None)
```

**Validation rules**:
- `description`: Minimum 20 characters (must be substantive enough to guide workstreams)
- A workstream can only be created for a goal with `approved_by_user == True`

### 2.10 Note

Represents a user annotation attached to a project, a living document section, or a specific claim.

```python
class Note(BaseModel):
    note_id: str = Field(default_factory=lambda: f"note-{uuid4().hex[:8]}")
    project_id: str
    content: str = Field(..., min_length=1)
    attach_to: str | None = Field(default=None)  # Claim ID, section heading, or None for project-level
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Validation rules**:
- `content`: Minimum 1 character
- `attach_to`: Optional reference to a claim ID, hypothesis ID, or living document section heading; if None, the note is project-level

### 2.11 Artifact

Represents a file produced or uploaded in the project.

```python
class Artifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: f"art-{uuid4().hex[:8]}")
    filename: str
    file_path: str  # Absolute path within workspace
    artifact_type: ArtifactType
    uploaded_by: str  # "user" or agent identifier
    description: str | None = Field(default=None)
    mime_type: str | None = Field(default=None)
    size_bytes: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ArtifactType(str, Enum):
    uploaded_pdf = "uploaded_pdf"
    generated_latex = "generated_latex"
    generated_markdown = "generated_markdown"
    code_script = "code_script"
    data_file = "data_file"
    simulation_result = "simulation_result"
```

### 2.12 ProgressUpdate

Incremental status report from a running workstream.

```python
class ProgressUpdate(BaseModel):
    update_id: str = Field(default_factory=lambda: f"upd-{uuid4().hex[:8]}")
    workstream_id: str
    agent_id: str
    status: str  # Human-readable status
    progress_percent: int = Field(default=0, ge=0, le=100)
    deliverable_snippet: str | None = Field(default=None)  # e.g., "Found 12 papers..."
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### 2.13 FailedExploration

Records a workstream or sub-investigation that concluded in failure.

```python
class FailedExploration(BaseModel):
    exploration_id: str = Field(default_factory=lambda: f"exp-{uuid4().hex[:8]}")
    workstream_id: str
    goal_attempted: str
    failure_reason: str
    lessons_learned: str
    related_hypotheses: list[str] = Field(default_factory=list)  # Hypothesis IDs
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

---

## 3. SQLite Schema

### 3.1 Tables

```sql
-- Projects
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    original_question TEXT NOT NULL,
    status TEXT DEFAULT 'created' CHECK (status IN ('created', 'clarifying', 'goals_approved', 'active', 'paused', 'completed', 'archived')),
    living_document TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    external_layer_config_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workstreams
CREATE TABLE workstreams (
    workstream_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('literature_search', 'concept_analysis', 'cross_traditional_comparison', 'argumentation', 'critical_review', 'phenomenological_description', 'ethical_analysis', 'synthesis')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed', 'stalled')),
    goal_statement_json TEXT NOT NULL,
    assigned_coordinator TEXT NOT NULL,
    assigned_sub_agents_json TEXT DEFAULT '[]',
    results TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hypotheses
CREATE TABLE hypotheses (
    hypothesis_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    strength TEXT CHECK (strength IN ('strong', 'moderate', 'weak', 'refuted', 'underdetermined')),
    origin TEXT CHECK (origin IN ('user', 'ai', 'joint', 'cross_tradition_synthesis')),
    status TEXT CHECK (status IN ('active', 'abandoned', 'refined', 'refuted')),
    epistemic_tradition TEXT,
    confidence_score REAL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    supporting_evidence_json TEXT DEFAULT '[]',
    counter_arguments_json TEXT DEFAULT '[]',
    dialectical_children_json TEXT DEFAULT '[]',
    abandonment_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    abandoned_at TIMESTAMP
);

-- Uncertainty Registry
CREATE TABLE uncertainty_registry (
    claim_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    counter_argument_strength REAL DEFAULT 0.0 CHECK (counter_argument_strength >= 0.0 AND counter_argument_strength <= 1.0),
    tradition_validity_json TEXT DEFAULT '{}',
    review_status TEXT DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed', 'under_review', 'contested', 'accepted_with_reservations', 'rejected')),
    stalled_sections_json TEXT DEFAULT '[]',
    source_workstream TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages (Queue)
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL,
    recipient_id TEXT NOT NULL,
    message_type TEXT NOT NULL CHECK (message_type IN ('status_update', 'delegation_request', 'delegation_response', 'steering_command', 'steering_ack', 'help_request', 'help_response', 'review_request', 'review_response', 'result_delivery', 'error_notification', 'user_notification')),
    payload_json TEXT DEFAULT '{}',
    epistemic_status_json TEXT DEFAULT '{}',
    correlation_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Review Rounds
CREATE TABLE review_rounds (
    round_id TEXT PRIMARY KEY,
    workstream_id TEXT NOT NULL REFERENCES workstreams(workstream_id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL CHECK (round_number >= 1),
    verdicts_json TEXT DEFAULT '[]',
    revision_request TEXT,
    status TEXT CHECK (status IN ('in_progress', 'completed', 'escalated')),
    escalated_to_coordinator BOOLEAN DEFAULT FALSE,
    escalation_reason TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Artifacts
CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    artifact_type TEXT CHECK (artifact_type IN ('uploaded_pdf', 'generated_latex', 'generated_markdown', 'code_script', 'data_file', 'simulation_result')),
    uploaded_by TEXT NOT NULL,
    description TEXT,
    mime_type TEXT,
    size_bytes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notes
CREATE TABLE notes (
    note_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    attach_to TEXT,  -- Claim ID, hypothesis ID, or section heading; NULL for project-level
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_workstreams_project ON workstreams(project_id);
CREATE INDEX idx_workstreams_status ON workstreams(status);
CREATE INDEX idx_hypotheses_project ON hypotheses(project_id);
CREATE INDEX idx_hypotheses_status ON hypotheses(status);
CREATE INDEX idx_uncertainty_project ON uncertainty_registry(project_id);
CREATE INDEX idx_uncertainty_review ON uncertainty_registry(review_status);
CREATE INDEX idx_messages_project ON messages(project_id);
CREATE INDEX idx_messages_recipient ON messages(recipient_id);
CREATE INDEX idx_review_rounds_ws ON review_rounds(workstream_id);
CREATE INDEX idx_notes_project ON notes(project_id);
CREATE INDEX idx_notes_attach ON notes(attach_to);
```

---

## 4. State Transition Diagrams

### 4.1 Project Lifecycle

```
[User: new project]
    ↓
created ──→ clarifying ──→ goals_approved ──→ active
                                              ↑ ↓
                                          paused
                                              ↓
                                        completed | archived
```

**Transitions**:
- `created → clarifying`: On `new project` command
- `clarifying → goals_approved`: When user approves at least one refined goal
- `goals_approved → active`: When first workstream starts
- `active → paused`: On user `pause` command or system interrupt
- `paused → active`: On user `resume` command
- `active → completed`: When all workstreams completed and user exports final document
- `active → archived`: On user `archive` command (preserves data but read-only)

### 4.2 Workstream Lifecycle

```
[user approves goal]
    ↓
pending ──→ running ──→ completed
              ↑ ↓         ↑
          paused   failed |
              ↑           |
          stalled ←───────┘
              ↑
        [user steering]
              ↓
          running
```

**Transitions**:
- See §2.2 for complete transition rules

### 4.3 Uncertainty Lifecycle

```
[claim generated]
    ↓
unreviewed ──→ under_review ──→ contested ──→ accepted_with_reservations
                  ↓                ↓
              rejected      rejected
                  ↓
        [Dialectical Appendix]
```

---

## 5. Key Invariants

1. **Project consistency**: A project with `status == "goals_approved"` or later MUST have at least one `GoalStatement` with `approved_by_user == True`.
2. **Workstream integrity**: A workstream with `status == "running"` MUST have a non-empty `assigned_coordinator` and a valid `goal_statement`.
3. **Hypothesis immutability**: Once created, a `HypothesisRecord`'s `statement`, `origin`, and `created_at` fields MUST NOT be modified. Status changes (active → refuted) are recorded as new `DialecticalMove` entries.
4. **Uncertainty sync**: The number of non-trivial claims in `living_document.md` MUST equal the number of `UncertaintyRecord` entries with matching `claim_text` hashes (verified on document save).
5. **Message ordering**: Messages within a project MUST be processable in `timestamp` order without loss of semantics.
6. **Review round limit**: `ReviewRound.round_number` MUST NOT exceed 5 for any workstream.
7. **Tradition validity**: All keys in `UncertaintyRecord.tradition_validity` MUST exist in the `TraditionRegistry` (loaded from `data/traditions/`).
8. **Storage authority**: SQLite is the authoritative source for structured data (projects, workstreams, hypotheses, uncertainty, messages, notes). JSONL/JSON files in the workspace are derived exports for human convenience; they MUST NOT be used as primary sources.
9. **Immutability**: Domain entities (`HypothesisRecord`, `DialecticalMove`, `Note`) follow a command-sourced mutation pattern — new state replaces old via explicit commands, not in-place mutation. Where full immutability is required, Pydantic models SHOULD use `model_config = ConfigDict(frozen=True)`.

---

**Data Model Version**: 1.0.0 | **Last Updated**: 2026-05-13
