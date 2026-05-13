# Contract: CLI Commands

**Date**: 2026-05-13  
**Feature**: AiCoPhilosopher v2.0  
**Interface**: Terminal Command-Line Interface

---

## 1. Overview

The CLI is the primary human interface to the AI Co-Philosopher. All commands are parsed by Click and rendered via Rich. Commands follow a consistent schema: `verb [noun] [options]`.

**Progressive disclosure**: The CLI renders responses in three sections:
1. **Summary** (always visible)
2. **Details** (collapsible, default collapsed)
3. **Suggestions** (collapsible, default collapsed)

---

## 2. Command Reference

### 2.1 Project Lifecycle

#### `new project <title>`
- **Purpose**: Create a new philosophical research project
- **Arguments**:
  - `title` (str, required): Project title (1-500 chars)
- **Options**:
  - `--question`, `-q` (str, optional): Initial philosophical question. If omitted, coordinator asks interactively.
  - `--directory`, `-d` (path, optional): Custom workspace directory. Default: `~/.aicophilosopher/projects/`
- **Returns**:
  - `project_id` (UUID)
  - `status`: `created` → immediate transition to `clarifying`
  - Coordinator begins Socratic clarification dialogue
- **Example**:
  ```
  > new project "Free Will and Moral Responsibility" -q "Do we have free will if determinism is true?"
  [Project created: proj-a1b2c3d4]
  Coordinator: "To help me understand your inquiry, could you clarify whether you're approaching this from a compatibilist, libertarian, or skeptical framework?"
  ```

#### `list projects`
- **Purpose**: List all projects with status summary
- **Options**:
  - `--status` (enum, optional): Filter by status
- **Returns**: Table with `project_id`, `title`, `status`, `last_updated`, `active_workstreams`

#### `open project <project_id>`
- **Purpose**: Resume an existing project
- **Arguments**:
  - `project_id` (UUID, required)
- **Returns**: Project state loaded; coordinator provides status summary

#### `archive project <project_id>`
- **Purpose**: Archive a completed or inactive project (read-only preservation)
- **Confirmation**: Required ("This will make the project read-only. Continue? [y/N]")

### 2.2 Goal & Workstream Management

#### `refine goal`
- **Purpose**: Enter or continue dialectical clarification dialogue
- **Context**: Must have an active project open
- **Interaction**: Interactive multi-turn dialogue with Project Coordinator
- **Returns**: Refined `GoalStatement` proposals; user can approve, edit, or reject
- **Exit condition**: User approves at least one goal with `approved_by_user = True`

#### `start workstream <type>`
- **Purpose**: Propose and launch a new workstream
- **Arguments**:
  - `type` (enum, required): One of `literature_search`, `concept_analysis`, `cross_traditional_comparison`, `argumentation`, `critical_review`, `synthesis`
- **Options**:
  - `--goal`, `-g` (str, optional): Goal ID to attach workstream to. If omitted, coordinator prompts.
  - `--instructions`, `-i` (str, optional): Additional instructions for the workstream coordinator
- **Flow**:
  1. User issues command
  2. Project Coordinator proposes workstream configuration
  3. User approves or modifies
  4. Workstream created with status `pending` → `running`
- **Returns**: `workstream_id`, `status`, `assigned_coordinator`

#### `pause <workstream_id>`
- **Purpose**: Pause a running workstream
- **Arguments**:
  - `workstream_id` (str, required)
- **Returns**: Updated status `paused`, timestamp

#### `resume <workstream_id>`
- **Purpose**: Resume a paused or stalled workstream
- **Arguments**:
  - `workstream_id` (str, required)
- **Returns**: Updated status `running`

#### `steer <workstream_id> <instruction>`
- **Purpose**: Direct steering of a specific workstream
- **Arguments**:
  - `workstream_id` (str, required)
  - `instruction` (str, required): Free-text steering command
- **Examples**:
  - `steer ws-001 "Focus on compatibilist literature from the 1980s onward"`
  - `steer ws-002 "Abandon the phenomenological approach and switch to analytic conceptual analysis"`
- **Returns**: Steering acknowledgement, updated workstream plan

### 2.3 Inquiry & Analysis

#### `show hypotheses`
- **Purpose**: Display hypothesis history with epistemic status
- **Options**:
  - `--status` (enum, optional): Filter by `active`, `abandoned`, `refined`, `refuted`
  - `--tradition` (str, optional): Filter by epistemic tradition
- **Returns**: Table with `hypothesis_id`, `statement`, `strength`, `confidence`, `status`, `origin`

#### `show dead ends`
- **Purpose**: Display failed explorations and refuted arguments
- **Returns**: Table with `exploration_id`, `goal_attempted`, `failure_reason`, `lessons_learned`, `timestamp`
- **Rationale**: Surfaces the "negative space" of the project (spec §7.2)

#### `compare traditions <topic>`
- **Purpose**: Request cross-traditional comparison
- **Arguments**:
  - `topic` (str, required): Concept or question to compare (e.g., "mind", "virtue", "causation")
- **Options**:
  - `--traditions`, `-t` (list, optional): Specific traditions to include. Default: all registered traditions
- **Returns**: CrossTraditionalComparison report with bridge concept map and incommensurability register

#### `phenomenological description <phenomenon>`
- **Purpose**: Request phenomenological analysis (MVP: basic skeleton; full version post-MVP)
- **Arguments**:
  - `phenomenon` (str, required): Phenomenon to describe (e.g., "the experience of listening to music")
- **Options**:
  - `--framework`, `-f` (enum, optional): `husserlian`, `merleau_pontyan`, `buddhist_vipassana`
- **Returns**: Phenomenological description with methodological framework, epoché declarations, confidence scores

#### `ethical analysis <dilemma>`
- **Purpose**: Request ethical framework analysis (MVP: basic skeleton; full version post-MVP)
- **Arguments**:
  - `dilemma` (str, required): Ethical dilemma or question
- **Options**:
  - `--frameworks` (list, optional): Specific frameworks to apply
- **Returns**: Multi-framework analysis with underdetermination flags

### 2.4 Document & Export

#### `show document`
- **Purpose**: Display the current living document
- **Options**:
  - `--section`, `-s` (str, optional): Display only a specific section (e.g., "arguments", "objections")
  - `--annotations`, `-a` (flag): Show margin annotations inline
- **Returns**: Rendered Markdown with optional annotation highlighting

#### `export <format>`
- **Purpose**: Export living document to external format
- **Arguments**:
  - `format` (enum, required): `markdown` (default), `latex`, `pdf`, `html`, `obsidian`
- **Constraints**:
  - `latex`, `pdf`: Post-MVP (MVP supports Markdown only)
  - `obsidian`: Post-MVP
- **Returns**: File path to exported artifact

#### `add note <text>`
- **Purpose**: Add user note to workspace
- **Arguments**:
  - `text` (str, required)
- **Options**:
  - `--attach-to` (str, optional): Hypothesis ID, claim ID, or workstream ID to link note to
- **Returns**: Note ID, timestamp

### 2.5 System & Help

#### `status`
- **Purpose**: Display system-wide status overview
- **Returns**:
  - Active project
  - Running/paused/stalled workstreams
  - Epistemic status overview (active/refuted/under_review/stalled counts)
  - LLM backend status

#### `request help`
- **Purpose**: Explicitly request human assistance flag from coordinator
- **Returns**: Coordinator surfaces current roadblocks and requests guidance

#### `config <key> <value>`
- **Purpose**: View or set configuration
- **Examples**:
  - `config llm.backend claude` — Set default LLM backend
  - `config llm.model claude-3-5-sonnet-20241022` — Set specific model
  - `config privacy.allow_external_search false` — Disable external search
  - `config` (no args) — Display all configuration values

---

## 3. Error Responses

All errors follow a consistent format:

```
❌ Error [<code>]: <message>
   Details: <context>
   Suggestion: <recovery action>
```

**Common error codes**:

| Code | Scenario | Message | Suggestion |
|------|----------|---------|------------|
| `E1001` | No active project | "No project is currently open. Use `new project` or `open project`." | `new project <title>` |
| `E1002` | Invalid workstream ID | "Workstream 'ws-xyz' not found in active project." | `list workstreams` |
| `E1003` | Workstream not runnable | "Workstream 'ws-xyz' is already running." | `status` |
| `E1004` | Goal not approved | "Cannot start workstream: no approved goals. Use `refine goal` first." | `refine goal` |
| `E2001` | External service denied | "External search requires consent. Run `config privacy.allow_external_search true`." | `config privacy.allow_external_search true` |
| `E2002` | LLM backend unavailable | "Claude API returned 429 (rate limit)." | `config llm.backend gemini` or wait |
| `E3001` | Review deadlock | "Workstream 'ws-xyz' review process stalled after 5 rounds." | `steer ws-xyz "override review and accept with reservations"` or `pause ws-xyz` |
| `E3002` | Incommensurability | "Cross-traditional comparison cannot bridge 'anatta' and 'Cartesian ego'." | `add note "User accepts incommensurability; proceed with parallel analyses."` |

---

## 4. Progressive Disclosure Rendering

All coordinator responses are rendered via Rich with this structure:

```python
from rich.panel import Panel
from rich.console import Console
from rich.markdown import Markdown

console = Console()

# Summary (always visible)
console.print(Panel("[bold]Summary[/bold]\n\n" + summary_text, title="AiCoPhilosopher"))

# Epistemic Status
console.print(f"Active: {active} | Refuted: {refuted} | Under Review: {under_review} | Stalled: {stalled}")

# Active Workstreams
console.print("[bold]Active Workstreams[/bold]")
for ws in workstreams:
    console.print(f"  {ws.id}: {ws.type} — {ws.status}")

# Details (collapsible via custom Rich component or command toggle)
if show_details:
    console.print(Panel(Markdown(details_text), title="[Details]"))

# Suggestions (collapsible)
if show_suggestions:
    console.print(Panel(Markdown(suggestions_text), title="[Suggestions]"))
```

**User toggle commands**:
- `show details` / `hide details` — Toggle details visibility for subsequent responses
- `show suggestions` / `hide suggestions` — Toggle suggestions visibility

---

**Contract Version**: 1.0.0 | **Last Updated**: 2026-05-13
