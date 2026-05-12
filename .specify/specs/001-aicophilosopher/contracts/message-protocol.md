# Contract: Inter-Agent Message Protocol

**Date**: 2026-05-13  
**Feature**: AiCoPhilosopher v2.0  
**Interface**: Internal Agent Communication

---

## 1. Overview

All agents communicate via a standardized JSON message protocol over a shared filesystem and SQLite-backed queue. The protocol is designed to be:
- **Debuggable**: Every message is a JSON file on disk, inspectable with `cat` or `jq`
- **Async-safe**: SQLite handles concurrent writes from parallel workstream coordinators
- **Local-first**: No network stack required

**Transport layers**:
1. **Filesystem**: Large payloads (reports, code attachments) written to `projects/<id>/messages/<msg_id>.json`
2. **SQLite queue**: Message metadata and routing information in `messages` table for fast querying

---

## 2. Message Schema

### 2.1 Base Message

```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "sender_id": "project_coordinator",
  "recipient_id": "ws-001",
  "message_type": "delegation_request",
  "payload": { /* type-specific */ },
  "timestamp": "2026-05-13T10:00:00Z",
  "epistemic_status": {
    "confidence": 0.85,
    "review_status": "unreviewed",
    "tradition_context": ["analytic_philosophy"],
    "uncertainty_flags": []
  },
  "correlation_id": null
}
```

**Field specifications**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_id` | UUID | Yes | Unique message identifier |
| `sender_id` | str | Yes | Agent identifier (e.g., `project_coordinator`, `ws-001`, `lit_search_agent_01`) |
| `recipient_id` | str | Yes | Agent identifier or `broadcast` for multi-cast |
| `message_type` | enum | Yes | See §3 |
| `payload` | object | Yes | Type-specific payload schema |
| `timestamp` | ISO8601 | Yes | UTC timestamp |
| `epistemic_status` | object | No | Confidence, review status, tradition context |
| `correlation_id` | UUID | No | For request/response pairing |

### 2.2 Agent Identifier Naming Convention

```
project_coordinator           # Top-level coordinator
ws-<8_hex_chars>              # Workstream coordinator (e.g., ws-a1b2c3d4)
<ws_id>_<agent_type>_<seq>    # Sub-agent within workstream (e.g., ws-a1b2c3d4_lit_search_01)
reviewer_<lens>_<seq>         # Reviewer agent (e.g., reviewer_analytic_01)
broadcast                     # Special identifier for multi-cast
user                          # Special identifier for human user messages
```

---

## 3. Message Types & Payload Schemas

### 3.1 `status_update`

Sent by workstream coordinators to report progress.

```json
{
  "message_type": "status_update",
  "payload": {
    "workstream_id": "ws-a1b2c3d4",
    "status": "running",
    "progress_percent": 45,
    "current_action": "Querying PhilPapers for 'compatibilism'",
    "deliverable_snippet": "Found 23 papers; 12 appear directly relevant.",
    "uncertainty_flags": ["search_term_ambiguity: 'free will' may retrieve non-philosophical results"]
  }
}
```

### 3.2 `delegation_request`

Sent by Project Coordinator or Workstream Coordinator to assign a task to a sub-agent.

```json
{
  "message_type": "delegation_request",
  "payload": {
    "task_id": "task-001",
    "task_type": "literature_search",
    "goal_statement": {
      "goal_id": "goal-001",
      "description": "Find analytic compatibilist literature from 1980-2020"
    },
    "constraints": {
      "max_results": 20,
      "required_traditions": ["analytic_philosophy"],
      "exclude_keywords": ["neuroscience", "psychology"]
    },
    "deadline": "2026-05-13T12:00:00Z",
    "attachments": ["projects/proj-001/artifacts/user_primer.pdf"]
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 3.3 `delegation_response`

Response to `delegation_request`.

```json
{
  "message_type": "delegation_response",
  "payload": {
    "task_id": "task-001",
    "status": "accepted",  // or "rejected"
    "rejection_reason": null,  // if rejected
    "estimated_completion": "2026-05-13T11:30:00Z"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 3.4 `steering_command`

Sent by user (via Project Coordinator) to direct a workstream.

```json
{
  "message_type": "steering_command",
  "payload": {
    "workstream_id": "ws-a1b2c3d4",
    "command": "refocus",
    "parameters": {
      "new_scope": "Focus specifically on Frankfurt-style compatibilism",
      "priority_shift": true
    }
  }
}
```

### 3.5 `steering_ack`

Acknowledgement of steering command.

```json
{
  "message_type": "steering_ack",
  "payload": {
    "workstream_id": "ws-a1b2c3d4",
    "command_received": "refocus",
    "new_plan_summary": "Will narrow search to Frankfurt-style compatibilism (1980-2020)",
    "impact_assessment": "Estimated +2 turns to completion"
  }
}
```

### 3.6 `help_request`

Sent by an agent when it encounters an intractable problem requiring human judgment.

```json
{
  "message_type": "help_request",
  "payload": {
    "requesting_agent": "ws-a1b2c3d4",
    "problem_type": "incommensurability",  // or "ethical_dilemma", "phenomenological_validation", "review_deadlock"
    "problem_description": "Cannot construct valid bridge concept between 'anatta' (Buddhist) and 'Cartesian ego' (Western). The two frameworks deny each other's foundational assumptions.",
    "attempted_solutions": [
      "Tried functionalist reduction: failed due to differing criteria for persistence",
      "Tried neutral description: failed due to theory-ladenness of all descriptions"
    ],
    "options_for_user": [
      "Accept incommensurability and proceed with parallel analyses",
      "Provide a bridging concept or analogy",
      "Exclude one tradition from the comparison"
    ],
    "urgency": "blocking",  // or "non_blocking"
    "context_attachments": ["projects/proj-001/workstreams/ws-a1b2c3d4_report.md"]
  }
}
```

### 3.7 `help_response`

Human response to `help_request`.

```json
{
  "message_type": "help_response",
  "payload": {
    "response_to": "help-request-001",
    "selected_option": 0,
    "user_comment": "Accept incommensurability. Note it explicitly in the cross-traditional report.",
    "additional_instructions": null
  }
}
```

### 3.8 `review_request`

Sent by Workstream Coordinator to initiate a review round.

```json
{
  "message_type": "review_request",
  "payload": {
    "workstream_id": "ws-a1b2c3d4",
    "round_number": 1,
    "report_path": "projects/proj-001/workstreams/ws-a1b2c3d4_report.md",
    "review_criteria": [
      "logical_correctness",
      "conceptual_clarity",
      "citation_accuracy",
      "tradition_appropriateness"
    ],
    "reviewer_lenses": ["analytic_logician", "phenomenological_critic"],
    "max_reviewers": 2
  }
}
```

### 3.9 `review_response`

Sent by reviewer agent upon completing review.

```json
{
  "message_type": "review_response",
  "payload": {
    "workstream_id": "ws-a1b2c3d4",
    "round_number": 1,
    "reviewer_id": "reviewer_analytic_01",
    "reviewer_lens": "analytic_logician",
    "verdict": {
      "status": "approved_with_reservations",
      "confidence": 0.72,
      "comments": "Argument valid but premise 3 requires stronger support. Suggest citing Frankfurt 1969 directly.",
      "identified_issues": [
        {
          "severity": "moderate",
          "location": "Section 2.3, Premise 3",
          "description": "Insufficient empirical support for claim about alternate possibilities"
        }
      ]
    }
  }
}
```

### 3.10 `result_delivery`

Sent by sub-agent to deliver completed work.

```json
{
  "message_type": "result_delivery",
  "payload": {
    "task_id": "task-001",
    "workstream_id": "ws-a1b2c3d4",
    "result_type": "literature_bibliography",
    "deliverable_path": "projects/proj-001/workstreams/ws-a1b2c3d4_bibliography.json",
    "summary": "23 papers found; 12 directly relevant; 3 cross-traditional bridge notes generated",
    "confidence": 0.81,
    "metadata": {
      "papers_found": 23,
      "relevant_papers": 12,
      "bridge_notes": 3,
      "traditions_covered": ["analytic_philosophy", "phenomenology"]
    }
  }
}
```

### 3.11 `error_notification`

Sent by any agent on failure.

```json
{
  "message_type": "error_notification",
  "payload": {
    "error_code": "E2002",
    "severity": "warning",  // or "critical"
    "source_agent": "ws-a1b2c3d4_lit_search_01",
    "description": "PhilPapers API returned 503 (Service Unavailable). Retrying with exponential backoff.",
    "retry_count": 2,
    "max_retries": 3,
    "fallback_activated": false
  }
}
```

### 3.12 `user_notification`

Sent by Project Coordinator to surface information to the user.

```json
{
  "message_type": "user_notification",
  "payload": {
    "notification_type": "workstream_completed",  // or "review_escalation", "help_needed", "goal_achieved"
    "workstream_id": "ws-a1b2c3d4",
    "summary": "Literature search workstream completed with approved report.",
    "action_required": false,
    "suggested_next_steps": ["Start Argumentation workstream", "Review bibliography"]
  }
}
```

---

## 4. Message Routing

### 4.1 Routing Logic

Messages are routed by the `MessageRouter` based on `recipient_id`:

1. **`broadcast`**: Message is copied to all active agents in the project
2. **`user`**: Message is surfaced to the CLI by the Project Coordinator
3. **Specific agent ID**: Message is queued in the recipient's inbox (SQLite `messages` table with `recipient_id` index)

### 4.2 Inbox Pattern

Each agent polls its inbox:
```python
class AgentInbox:
    async def poll(self, agent_id: str, timeout: float = 5.0) -> list[Message]:
        # Query SQLite for messages where recipient_id = agent_id
        # ORDER BY timestamp ASC
        # Mark as "delivered" to prevent duplicate processing
```

### 4.3 Correlation IDs

Request/response pairs use `correlation_id`:
- `delegation_request` → `delegation_response`
- `review_request` → `review_response`
- `help_request` → `help_response`

The requester polls for messages with matching `correlation_id`.

---

## 5. Message Persistence

### 5.1 Retention Policy

| Message Type | Retention | Rationale |
|--------------|-----------|-----------|
| `status_update` | 30 days | Ephemeral; only latest status matters for most queries |
| `delegation_request/response` | Permanent | Audit trail of task assignments |
| `steering_command/ack` | Permanent | Audit trail of user interventions |
| `help_request/response` | Permanent | Critical for understanding project history |
| `review_request/response` | Permanent | Review process must be fully auditable |
| `result_delivery` | Permanent | Deliverables are permanent project artifacts |
| `error_notification` | 90 days | Debugging aid; not critical long-term |
| `user_notification` | 30 days | UI event; historical value limited |

### 5.2 Archive Process

Messages older than retention period are moved to `projects/<id>/archive/messages/<year>/<month>/` as compressed JSONL files.

---

## 6. Validation

All messages are validated against Pydantic schemas before persistence:
1. **Structure validation**: Required fields present, types correct
2. **Agent existence**: `sender_id` and `recipient_id` MUST be registered agents in the project
3. **Payload schema**: `payload` MUST match the schema for the given `message_type`
4. **Timestamp**: MUST be within 60 seconds of server time (prevents replay attacks in future distributed mode)

**Validation failures**:
- Logged to `projects/<id>/logs/invalid_messages.log`
- Not routed to recipient
- Error notification sent to sender if `sender_id` is valid

---

**Contract Version**: 1.0.0 | **Last Updated**: 2026-05-13
