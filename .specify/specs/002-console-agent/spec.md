# Feature Specification: Console Agent — Continuous Dialogue REPL

**Feature Branch**: `002-console-agent`

**Created**: 2026-05-18

**Status**: Draft

**Input**: Issue #35 — "一般的なAI Agentのように、consoleの中で続けて打ち込んで行きたい" (Want to interact continuously inside the console, like a general AI Agent). Parent spec: 001-aicophilosopher v2.0.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Casual Philosophical Inquiry in Natural Language (Priority: P1)

A philosopher launches `aicophilosopher` and enters a REPL. They type a vague question in natural Japanese or English—no command prefix, no subcommand name, no project ID. The Project Coordinator responds in natural language, asks Socratic clarifying questions, proposes workstreams, and launches them—all within the same continuous dialogue. The user never leaves the conversation flow.

**Why this priority**: This is the core paradigm shift from CLI-command-driven interaction to agent-like continuous dialogue. It directly addresses Issue #35's complaint: "いちいちコマンドを探して、毎回接頭辞にaicophilosopherと打つのが面倒だから" (It's tedious to look up commands and type `aicophilosopher` prefix every time). Without this, the product remains a CLI tool, not an AI agent.

**Independent Test**: Launch `aicophilosopher`, type a philosophical question in natural language, and complete at least one full inquiry cycle (clarification → workstream launch → result review → tentative answer) without ever typing a command prefix or `/` shortcut. Verify the entire dialogue is in natural language.

**Acceptance Scenarios**:

1. **Given** the REPL is running with no active project, **When** the user types "I want to understand whether abstraction in software has philosophical grounding beyond just engineering practice", **Then** the coordinator responds in natural language with a Socratic clarification (e.g., asks about ontological vs epistemological vs normative angle), and does NOT require the user to type `new project` or `refine goal`.

2. **Given** a clarification dialogue is in progress, **When** the user answers the coordinator's clarifying questions, **Then** the coordinator progressively refines the inquiry and eventually proposes concrete research goals and workstreams, all in natural language.

3. **Given** the coordinator has proposed workstreams, **When** the user types "Yes, go ahead" or "Let's do it", **Then** the workstreams are created and launched, and the coordinator reports their status, without the user typing `start workstream literature_search`.

4. **Given** a running workstream, **When** the user types "Actually, focus specifically on post-1980 compatibilism literature instead", **Then** the coordinator interprets this as a steering command, applies it to the relevant workstream, and confirms the updated plan, without the user typing `steer <ws_id> <instruction>`.

5. **Given** the coordinator presents a request for human judgment (e.g., "The reviewers disagree on this methodology—which framework should take priority?"), **When** the user replies with their preference in natural language, **Then** the coordinator routes the decision to the appropriate workstream and continues.

---

### User Story 2 — Session Persistence and Seamless Resumption (Priority: P1)

A philosopher is mid-inquiry with 3 running workstreams. They type `/exit` (or press Ctrl+D, or the terminal is closed). Later—hours or days later—they run `aicophilosopher` again. The system detects the previous session, presents a summary of what was in progress, and offers to resume. All workstreams continue from their last state. The conversation context is restored.

**Why this priority**: Philosophical inquiry spans days, not minutes. Without session persistence, every restart means losing context and forcing the user to re-establish where they were. This is a critical differentiator from transient chatbots and directly addresses Issue #35's requirement: "sessionの再開ができるようにする" (Enable session resumption).

**Independent Test**: Start a session, create a project, launch a workstream, type `/exit`. Then restart `aicophilosopher`, open the project, and verify the dialogue history, context blocks, and workstream states are all restored and the conversation can continue seamlessly.

**Acceptance Scenarios**:

1. **Given** an active session with dialogue history, context blocks, and running workstreams, **When** the user types `/exit` (or the process receives SIGTERM), **Then** the full session state is atomically persisted (dialogue history, context blocks, pending approvals, active workstream handles, focus context), and workstreams continue running in the background.

2. **Given** a previously exited session exists, **When** the user restarts `aicophilosopher`, **Then** the system lists available projects with their last-active timestamps and session status, and prompts the user to select one or start fresh.

3. **Given** the user selects a project to resume, **When** the session is loaded, **Then** the coordinator presents a structured summary: "Welcome back. You were exploring [topic]. Workstream WS-001 completed its literature review (23 papers); WS-002 is still analyzing Frankfurt cases. Would you like a summary of findings or should we continue where we left off?"

4. **Given** a resumed session, **When** the user continues the conversation, **Then** the coordinator has access to the full dialogue history, context blocks, and pending approvals from the previous session, and responds with full awareness of prior context.

5. **Given** a session with workstreams that were `running` at exit time, **When** the session is resumed, **Then** those workstreams are still `running` (they continued via LangGraph checkpointing, independent of the REPL process), and their incremental progress since exit is reported.

---

### User Story 3 — Slash Commands as Power-User Shortcuts (Priority: P2)

Power users who know exactly what they want can use `/` shortcuts (`/search`, `/pause ws-001`, `/export markdown`, `/status`) to bypass natural language intent parsing. These are accelerators, never required. The full slash command set covers session management, inquiry, steering, viewing, and export.

**Why this priority**: While natural language is the primary interface, explicit commands are essential for precision (e.g., `/pause ws-001` vs "please stop that one workstream") and for users who have learned the system and want speed. They also serve as an escape hatch when NLU intent classification is ambiguous.

**Independent Test**: Type each slash command from the full command set and verify the correct action is performed immediately, without NLU ambiguity. Verify that every action achievable via natural language is also achievable via a `/` command.

**Acceptance Scenarios**:

1. **Given** the REPL is active, **When** the user types `/help`, **Then** all available commands are listed with brief descriptions, grouped by category (Session, Inquiry, Steering, View, Other).

2. **Given** a running workstream `ws-001`, **When** the user types `/pause ws-001`, **Then** the workstream transitions to `paused` status and the coordinator confirms, all within 5 seconds.

3. **Given** natural language would be ambiguous ("check on the thing"), **When** the user instead types `/status`, **Then** a precise status overview is displayed (active project, workstream states, epistemic status counts, LLM backend status).

4. **Given** the user wants to export the living document, **When** they type `/export markdown`, **Then** the document is exported without any clarification dialogue, and the file path is reported.

---

### User Story 4 — The Full Inquiry Cycle as a Single Conversation (Priority: P2)

A philosopher executes the complete philosophical workflow—initial question → Socratic refinement → literature search → concept analysis → argumentation → critical review → synthesis → tentative answer—entirely within the REPL, without mode-switching or leaving the conversation. At any point, they can steer, deepen, pivot, or request help.

**Why this priority**: This validates the end-to-end promise of the Console Agent: that philosophical research can be conducted as a flowing conversation, not a sequence of tool invocations. It directly corresponds to Issue #35's flow requirement: "問い→Refine→サーチ→議論→仮の答え" (Inquiry → Refine → Search → Discussion → Tentative Answer).

**Independent Test**: Start from a vague question, complete all phases through a tentative answer, and verify the living document reflects the full inquiry with margin annotations, dialectical history, and uncertainty tracking.

**Acceptance Scenarios**:

1. **Given** a new REPL session, **When** the user poses a vague philosophical question and engages with the coordinator's Socratic dialogue, **Then** within ≤5 turns, at least one refined research goal is approved.

2. **Given** approved goals, **When** the user agrees to the coordinator's workstream proposals, **Then** literature search and concept analysis workstreams launch and produce structured outputs (bibliography with tradition tags, concept map with distinction matrix).

3. **Given** completed literature search and concept analysis, **When** the coordinator proposes argumentation and the user agrees, **Then** standard-form arguments with competing positions are generated, and the critical review agent produces counter-arguments.

4. **Given** completed argumentation and review, **When** the coordinator triggers synthesis, **Then** the living document is updated with synthesized prose, full margin annotations, and conflict flags for any workstream disagreements.

5. **Given** the living document is updated, **When** the user asks "What's our tentative conclusion?", **Then** the coordinator presents a synthesized answer with explicit epistemic status (confidence, counter-argument strength, unresolved issues, open questions).

---

### Edge Cases

- **NLU misclassification**: When the coordinator cannot confidently classify the user's intent from natural language, it MUST ask a clarifying question rather than silently taking a wrong action. The confidence threshold for silent action is configurable (default: 0.85). Below threshold, the coordinator says "I want to make sure I understand—did you mean [interpretation A] or [interpretation B]?"

- **Empty/incomplete input**: When the user types empty input or an incomplete sentence (e.g., just "free will"), the coordinator treats it as the start of an inquiry and asks "What about free will are you interested in exploring?"

- **Command injection via natural language**: Natural language input that resembles a slash command (e.g., "What does /search do?") MUST be treated as natural language, not as a command. Only input starting with `/` at position 0 is treated as a slash command.

- **Session corruption on crash**: If the process crashes (SIGKILL, power loss), session state is recovered from the most recent successful atomic write (every coordinator response triggers a checkpoint). At most one dialogue turn is lost.

- **Concurrent session conflict**: A project MUST NOT have two active REPL sessions simultaneously. If the user attempts to open a project that already has an active session (possibly from another terminal), the system warns and offers to either terminate the other session or open in read-only mode.

- **Very long sessions**: Sessions spanning thousands of dialogue turns MUST degrade gracefully. The active LLM context window includes only the last N turns + summaries of older context blocks. The full dialogue history remains persisted and searchable.

- **Non-philosophical input**: When the user types something unrelated to philosophical inquiry (e.g., "What's the weather?"), the coordinator MUST NOT attempt to treat it as a philosophical question. It responds: "I'm focused on philosophical research. I can help with conceptual analysis, argumentation, literature review, or cross-traditional comparison. What philosophical question would you like to explore?"

- **Workstream completion during session absence**: If workstreams complete or fail while the user is not in an active REPL session, their status transitions are persisted via LangGraph checkpointing. On session resume, the coordinator surfaces all state changes that occurred during absence.

- **Steering an already-completed workstream**: If the user attempts to steer a workstream that is already `completed` or `failed`, the coordinator explains the workstream's current state and asks whether the user wants to create a new workstream to pursue the new direction.

---

## Requirements *(mandatory)*

### Functional Requirements

#### REPL Core

- **FR-001**: System MUST provide an interactive REPL (Read-Eval-Print-Loop) accessible via `aicophilosopher` command, without requiring subcommands or arguments.

- **FR-002**: System MUST accept and process natural language input as the primary interaction mode. Natural language input MUST NOT require any prefix, command name, or structured syntax.

- **FR-003**: System MUST classify user intent from natural language input using the Project Coordinator's NLU capabilities. Supported intent categories: `start_inquiry`, `clarify_question`, `propose_workstream`, `steer_workstream`, `request_status`, `request_detail`, `request_export`, `approve_action`, `reject_action`, `ask_question`, `inject_information`, `request_help`, `pause_session`, `resume_session`, `archive_project`, `compare_traditions`.

- **FR-004**: When NLU confidence is below the configurable threshold (default: 0.85), the coordinator MUST ask a clarifying question before acting. It MUST NOT silently execute a low-confidence interpretation.

- **FR-005**: System MUST support `/` prefix shortcuts as explicit commands that bypass NLU classification entirely. Full slash command set defined in `contracts/repl-commands.md`.

- **FR-006**: Input starting with `/` at character position 0 MUST be routed to the slash command handler. `/` appearing elsewhere in natural language input MUST NOT trigger command routing.

- **FR-007**: System MUST render all coordinator responses using progressive disclosure: **Summary** (always visible), **Epistemic Status** (always visible), **Active Workstreams** (always visible), **[Details]** (collapsed by default), **[Suggestions]** (collapsed by default).

#### Session Management

- **FR-008**: System MUST maintain a `SessionState` for each REPL session, including: `session_id`, `project_id`, `status` (active/paused/closed), `created_at`, `last_active_at`, `dialogue_history`, `context_blocks`, `current_focus`, `pending_approvals`, `active_workstreams`.

- **FR-009**: On `/exit`, `/quit`, Ctrl+D (EOF), or SIGTERM, the system MUST atomically persist the full `SessionState` to the project's SQLite database and filesystem. Workstreams marked `running` MUST continue execution via LangGraph checkpointing, independent of the REPL process.

- **FR-010**: On `aicophilosopher` startup with no `--project` argument, the system MUST list all projects with their last-active timestamps and session status. The user MUST be able to select a project by number, by ID, or by typing a new question to start fresh.

- **FR-011**: On session resume, the coordinator MUST present a structured summary including: last active topic, completed workstreams since last session, running workstreams with their current status, pending approval requests awaiting user response.

- **FR-012**: On session resume, the coordinator's LLM context window MUST be populated with: system prompt, last N dialogue turns (configurable, default 20), summaries of older context blocks, active workstream status summaries, and any pending approvals.

- **FR-013**: A project MUST NOT have more than one active REPL session. Attempting to open a project with an existing active session MUST trigger a warning and a choice: terminate other session, open read-only, or cancel.

#### Context & Memory

- **FR-014**: System MUST group dialogue turns into thematic `ContextBlock`s. Each context block has: a UUID, a human-readable label, the list of turn IDs it contains, an auto-generated summary, an optional parent context for branching discussions, and the epistemic state (claims/hypotheses discussed).

- **FR-015**: System MUST track a `FocusContext` for the current conversation, including: active topic, last workstream mentioned, last hypothesis mentioned, pending decisions awaiting user response, and recent claims (last N claim IDs).

- **FR-016**: For implicit steering (e.g., "Deepen that analysis" without specifying which workstream), the coordinator MUST infer the target from `FocusContext.last_workstream_id`. If ambiguous, the coordinator MUST ask "Which analysis would you like me to deepen?"

- **FR-017**: The system MUST log all dialogue turns (user input + coordinator response + actions taken) to the session's dialogue history, with timestamps, context block associations, and parsed intents.

#### Inquiry Cycle

- **FR-018**: The system MUST support the full philosophical inquiry cycle within the REPL: inquiry → clarification → literature survey → concept analysis → argumentation → critical review → cross-traditional comparison → synthesis → tentative answer.

- **FR-019**: At any point in the cycle, the user MUST be able to naturally pivot: "Actually, let's examine this from a phenomenological angle instead" triggers a context shift and appropriate workstream creation/modification.

- **FR-020**: At any point, the user MUST be able to request deeper analysis: "Could you drill into Frankfurt's 1969 argument more?" triggers the coordinator to launch or steer a workstream for detailed analysis of that specific sub-topic.

- **FR-021**: At any point, the user MUST be able to request the dialectical history: "Show me how we arrived at this claim" triggers the coordinator to present the relevant dialectical lineage from the history.

- **FR-022**: At any point, the user MUST be able to inject new data: "I'm uploading a paper by Pereboom" triggers PDF ingestion into the local RAG corpus with relevance analysis.

#### Integration with Agent Hierarchy

- **FR-023**: The REPL Project Coordinator MUST delegate workstream creation and steering to the existing Workstream Coordinators via the standardized JSON message protocol defined in 001 contracts.

- **FR-024**: Workstream status updates (progress, completion, failure, stall) MUST be surfaced asynchronously in the REPL. If the user is mid-input, the update is queued and presented after the current interaction completes.

- **FR-025**: Bidirectional help requests (agents requesting human judgment) MUST be surfaced in the REPL as conversational interjections with structured options for the user to choose from.

- **FR-026**: All REPL interactions MUST respect the existing constitution principles: local-first privacy (no external data transmission without explicit consent), intellectual honesty (confidence scores on all claims), and auditability (all actions logged).

### Key Entities

- **SessionState**: Represents a single REPL session. Contains session_id, project_id, status (active/paused/closed), timestamps, dialogue_history (list of DialogueTurns), context_blocks (list of ContextBlocks), current_focus (FocusContext), pending_approvals, active_workstream_handles. Persisted to SQLite on exit; loaded on resume.

- **DialogueTurn**: A single exchange in the REPL. Contains turn_id, speaker (user/coordinator/system), raw content text, parsed intent (for user turns), actions_taken list (what the coordinator did), context_block_id, timestamp. Immutable once created.

- **ContextBlock**: A thematic grouping of dialogue turns. Contains context_id, label, turn_id list, auto-generated summary, parent_context_id (nullable), epistemic_state snapshot. Used for session resumption context reconstruction.

- **FocusContext**: The coordinator's current attention window. Contains active_topic string, last_workstream_id (nullable), last_hypothesis_id (nullable), pending_decisions list, recent_claim_ids list. Updated on every coordinator response.

- **ApprovalRequest**: A pending decision requiring user input. Contains request_id, request_type (workstream_proposal, normative_judgment, incommensurability_resolution, review_escalation), description, options list, urgency (blocking/non_blocking), created_at. Persisted across sessions; re-presented on resume.

- **UserIntent**: Parsed from natural language input. Contains intent_type (enum of supported intents), confidence_score, extracted_entities dict (workstream_id, concept_name, topic, etc.), raw_input reference. Generated by NLU classification; validated before action.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with no prior knowledge of AiCoPhilosopher commands can launch `aicophilosopher`, pose a philosophical question in natural language, and receive a coherent Socratic response within 10 seconds of their first input.

- **SC-002**: NLU intent classification achieves ≥90% accuracy on a test set of 100 diverse philosophical inquiry utterances spanning inquiry initiation, clarification, steering, status requests, and data injection (measured against human-labeled ground truth).

- **SC-003**: A user can complete a full inquiry cycle (question → refine → search → argumentation → tentative answer) without typing any command prefix, slash command, or project ID, in ≤1 session, with the user satisfaction rating ≥4/5.

- **SC-004**: Session exit and resume preserves 100% of critical session state (dialogue history, context blocks, pending approvals, workstream handles) with zero data loss on graceful exit. On crash recovery, at most 1 dialogue turn is lost.

- **SC-005**: On session resume, the coordinator presents a contextually accurate summary within 30 seconds of project selection, and the user can immediately continue the conversation with full awareness of prior context.

- **SC-006**: Every slash command in the full command set executes its intended action within 5 seconds of input (measured from Enter keypress to command acknowledgement).

- **SC-007**: The coordinator's progressive disclosure rendering works correctly: **Summary** section is always ≤5 lines, and **[Details]** and **[Suggestions]** are independently togglable via `/details` and `/suggestions` commands.

- **SC-008**: The system gracefully handles a 1000-turn session without performance degradation (response latency remains ≤30 seconds for the 1000th turn, comparable to the 10th turn).

- **SC-009**: Concurrent session conflict detection works: attempting to open a project with an active session in another terminal correctly triggers the warning and choice interface.

---

## Assumptions

- The existing agent hierarchy (Project Coordinator, Workstream Coordinators, specialized sub-agents) from 001-aicophilosopher is available and operational. The Console Agent wraps the Project Coordinator with a REPL interface rather than replacing it.

- The existing message protocol (`contracts/message-protocol.md`) is used for all inter-agent communication. The REPL introduces no new message types; it routes user input through the existing protocol.

- LangGraph checkpointing provides the underlying workstream persistence. The Console Agent's session persistence is an additional layer that preserves dialogue context and REPL-specific state.

- The Rich library (already in dependencies) is used for terminal rendering, including progressive disclosure panels, live status updates, and Markdown formatting.

- The user's terminal supports standard ANSI escape sequences (Linux/macOS Terminal, Windows Terminal, iTerm2, etc.). No special terminal capabilities beyond Rich's requirements are needed.

- Users are philosophers, philosophy students, or researchers with basic terminal familiarity. They are NOT expected to be developers or CLI power users.

- Japanese and English are the two primary supported languages for natural language input. The NLU system must handle both. Additional languages are post-MVP.

- The console REPL is the sole user-facing interface for MVP. Web UI (Gradio/Streamlit) is deferred to Phase 4 of the parent 001 spec.

- Session persistence relies on SQLite (already in the tech stack). No additional database infrastructure is introduced.

- Workstreams continue executing via LangGraph's async runtime even when no REPL session is active. The Console Agent does not need to proxy or manage workstream execution—only to surface their status.
