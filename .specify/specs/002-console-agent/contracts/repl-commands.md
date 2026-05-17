# Contract: REPL Slash Commands

**Date**: 2026-05-18
**Feature**: 002-console-agent
**Interface**: Console REPL Slash Command Handler

---

## 1. Overview

Slash commands (`/command`) are power-user shortcuts that bypass natural language intent classification. Every action achievable via natural language is also available as a `/` command. Commands are routed by the REPL input handler when input starts with `/` at character position 0.

**Design principle**: Slash commands are accelerators, never required. The system MUST be fully usable with natural language alone.

---

## 2. Command Reference

### 2.1 Session Commands

| Command | Arguments | Action | Example |
|---------|-----------|--------|---------|
| `/help` | — | Display all commands with brief descriptions, grouped by category | `/help` |
| `/exit` | — | Persist session state and exit REPL | `/exit` |
| `/quit` | — | Alias for `/exit` | `/quit` |
| `/new` | `<question>` | Create a new project and immediately begin clarification dialogue | `/new "What is truth?"` |
| `/open` | `<project_id>` | Open an existing project and resume or start a session | `/open proj-a1b2c3d4` |
| `/projects` | `[--status active\|paused\|all]` | List all projects with status, last-active timestamp, workstream count | `/projects --status active` |
| `/archive` | `[project_id]` | Archive a project (read-only). Defaults to current project. Requires confirmation. | `/archive` |

### 2.2 Inquiry Commands

| Command | Arguments | Action | Example |
|---------|-----------|--------|---------|
| `/search` | `<query>` | Launch or steer a literature search workstream | `/search "Frankfurt compatibilism 1980-2020"` |
| `/analyze` | `<concept>` | Launch a concept analysis workstream | `/analyze "qualia"` |
| `/argue` | `<topic>` | Launch an argumentation workstream | `/argue "free will vs determinism"` |
| `/review` | `[ws_id]` | Trigger critical review of a workstream's outputs (defaults to last discussed) | `/review ws-002` |
| `/compare` | `<topic>` `[--traditions a,b,c]` | Launch cross-traditional comparison | `/compare "abstraction" --traditions analytic,philosophy_of_technology` |
| `/synthesize` | `[--sections intro,args]` | Trigger synthesis of completed workstream outputs into living document | `/synthesize` |

### 2.3 Steering Commands

| Command | Arguments | Action | Example |
|---------|-----------|--------|---------|
| `/pause` | `[ws_id]` | Pause a workstream. Defaults to the most recently discussed. | `/pause ws-001` |
| `/resume` | `[ws_id]` | Resume a paused or stalled workstream. | `/resume ws-001` |
| `/steer` | `<ws_id> <instruction>` | Direct steering of a specific workstream with explicit instruction | `/steer ws-001 "Focus only on compatibilist papers"` |
| `/deepen` | `<concept_or_section>` | Request deeper analysis of a concept or document section | `/deepen "Frankfurt's counterfactual intervention premise"` |
| `/abandon` | `<hypothesis_id>` | Mark a hypothesis as abandoned with reason prompt | `/abandon hyp-abc12345` |

### 2.4 View Commands

| Command | Arguments | Action | Example |
|---------|-----------|--------|---------|
| `/status` | — | Display session and workstream status overview (project, workstream states, epistemic counts, LLM backend) | `/status` |
| `/hypotheses` | `[--status active\|refuted\|abandoned\|all]` `[--tradition <name>]` | Display hypothesis history with epistemic status | `/hypotheses --status refuted` |
| `/dead-ends` | — | Display failed explorations and refuted arguments with lessons learned | `/dead-ends` |
| `/document` | `[--section <name>]` `[--annotations]` | Display the living document, optionally scoped to a section, optionally with inline annotations visible | `/document --section Arguments --annotations` |
| `/details` | — | Toggle [Details] sections ON for subsequent responses | `/details` |
| `/hide-details` | — | Toggle [Details] sections OFF for subsequent responses | `/hide-details` |
| `/suggestions` | — | Toggle [Suggestions] sections ON for subsequent responses | `/suggestions` |
| `/hide-suggestions` | — | Toggle [Suggestions] sections OFF for subsequent responses | `/hide-suggestions` |

### 2.5 Export & Data Commands

| Command | Arguments | Action | Example |
|---------|-----------|--------|---------|
| `/export` | `<format>` | Export living document. Supported formats: `markdown` (always), `html` (always), `latex` (post-MVP) | `/export markdown` |
| `/add-note` | `<text>` `[--attach-to <id>]` | Add a user note to the workspace, optionally attached to a hypothesis, claim, or document section | `/add-note "Check Pereboom 2001 for this" --attach-to hyp-abc12345` |
| `/upload` | `<path>` | Upload a PDF for local RAG ingestion. File is chunked and indexed in the project's ChromaDB. | `/upload ~/papers/frankfurt1969.pdf` |

### 2.6 Help & Config Commands

| Command | Arguments | Action | Example |
|---------|-----------|--------|---------|
| `/help-request` | `[description]` | Explicitly request human assistance from the coordinator. Surfaces current roadblocks and requests guidance. | `/help-request` |
| `/config` | `[key]` `[value]` | View or set configuration. No args: display all. One arg: display that key's value. Two args: set value. | `/config llm.backend claude` |

---

## 3. Command Routing Logic

```
REPL Input Handler
    │
    ├── Input starts with "/" at position 0?
    │   ├── YES → Slash Command Parser
    │   │   ├── Parse: /<command> [args...]
    │   │   ├── Validate command exists
    │   │   ├── Validate arguments match command spec
    │   │   └── Route to appropriate handler
    │   │       ├── Session commands → SessionManager
    │   │       ├── Inquiry commands → ProjectCoordinator
    │   │       ├── Steering commands → ProjectCoordinator → WorkstreamCoordinator
    │   │       ├── View commands → ProjectCoordinator
    │   │       └── Export/Data commands → ProjectCoordinator
    │   │
    │   └── NO → Natural Language Intent Parser
    │       ├── Classify intent via NLU (LLM-based)
    │       ├── If confidence ≥ threshold → Route to ProjectCoordinator with parsed intent
    │       └── If confidence < threshold → Ask clarifying question
```

---

## 4. Command Validation Rules

- Unknown commands: Respond with `Unknown command: '/xyz'. Type /help for available commands.`
- Missing required arguments: Respond with usage hint (e.g., `/steer requires <workstream_id> and <instruction>`)
- Invalid workstream IDs: Respond with `Workstream 'ws-xyz' not found. Active workstreams: ws-001, ws-002.`
- Ambiguous omission (e.g., `/pause` with zero workstreams): Respond with `No workstreams are currently running.`
- Ambiguous omission (e.g., `/pause` with multiple workstreams): Respond with `Which workstream? Running: ws-001 (Literature Search), ws-002 (Concept Analysis).`
- Command on wrong project state (e.g., `/argue` without approved goals): Respond with `No approved goals yet. Let's refine your question first. What aspect are you interested in?`

---

## 5. Progressive Disclosure in Command Responses

Even slash commands produce progressive disclosure responses:

```
/status
─────────────

**Summary**
Project: "Ontology of Software Abstraction" — Active
2 workstreams running, 1 completed, 4 hypotheses active

**Epistemic Status**
Active: 4 | Refuted: 1 | Under Review: 2 | Stalled: 0

**Active Workstreams**
WS-001: Literature Search — completed (23 papers)
WS-002: Concept Analysis — running (60%)
WS-003: Cross-Traditional Comparison — running (30%)

[Details]
[List of individual hypotheses, recent claims, review round statuses]

[Suggestions]
"WS-001 is complete. Start Argumentation workstream?"
"WS-002 will finish in ~2 minutes."
```

---

**Contract Version**: 1.0.0 | **Last Updated**: 2026-05-18
