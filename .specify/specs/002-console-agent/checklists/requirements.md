# Checklist: Console Agent — Continuous Dialogue REPL

**Date**: 2026-05-18
**Feature**: 002-console-agent
**Spec**: `.specify/specs/002-console-agent/spec.md`

---

## 1. Specification Completeness

- [x] User Story 1: Casual Philosophical Inquiry in Natural Language (P1)
- [x] User Story 2: Session Persistence and Seamless Resumption (P1)
- [x] User Story 3: Slash Commands as Power-User Shortcuts (P2)
- [x] User Story 4: Full Inquiry Cycle as Single Conversation (P2)
- [x] Edge cases documented (9 scenarios)
- [x] Functional requirements documented (FR-001 through FR-026)
- [x] Key entities documented (SessionState, DialogueTurn, ContextBlock, FocusContext, ApprovalRequest, UserIntent)
- [x] Success criteria documented (SC-001 through SC-009)
- [x] Assumptions documented (12 items)

## 2. Contract Completeness

- [x] REPL Slash Commands contract (`contracts/repl-commands.md`)
- [ ] REPL Rendering contract (progressive disclosure output format)
- [ ] NLU Intent Schema (formal specification of intent types and entity schemas)

## 3. Data Model Completeness

- [x] Entity relationship diagram
- [x] SessionState with status transitions
- [x] DialogueTurn with speaker types
- [x] UserIntent with intent types and alternatives
- [x] ContextBlock with epistemic snapshots
- [x] FocusContext with pending decisions
- [x] ApprovalRequest with urgency classification
- [x] ActionTaken for coordinator actions
- [x] SQLite schema extensions
- [x] Key invariants

## 4. Constitution Compliance

- [ ] Principle I (Core Independence): REPL MUST function without external orchestration layers
- [ ] Principle I (Local-First Privacy): No session data transmitted externally without explicit consent
- [ ] Principle II (Intellectual Honesty): All coordinator responses include confidence and epistemic status
- [ ] Principle III (Code Quality): REPL code follows Clean Architecture layers (presentation/ → application/)
- [ ] Principle IV (Testing): NLU intent classification and session persistence MUST have automated tests
- [ ] Principle V (MVP-First): Natural language and session persistence are P1; slash commands are P2

## 5. Integration Points

- [ ] With existing Project Coordinator Agent (wraps, not replaces)
- [ ] With existing message protocol (no new message types)
- [ ] With existing workstream lifecycle (surfacing status asynchronously)
- [ ] With existing LangGraph checkpointing (workstream continuation across sessions)
- [ ] With existing SQLite schema (extensions must not break existing tables)
- [ ] With existing CLI entry point (`aicophilosopher` → REPL mode)

## 6. Open Questions

1. Should the NLU intent classifier be LLM-based (prompt with in-context examples) or a fine-tuned classifier? LLM-based is simpler for MVP but adds latency. Fine-tuned classifier requires training data but is faster.
2. How many dialogue turns should be in the active LLM context window by default? 20 is specified but needs empirical validation.
3. Should the REPL support scrolling through command history (like readline)? Yes—this is a standard expectation. Specify as FR-027.
4. Should the REPL support tab-completion of slash commands and project/workstream IDs?
5. How are binary files (PDF upload paths, export output paths) handled in the REPL? Currently via `/upload <path>` and `/export <format>`.

---

**Checklist Version**: 1.0.0 | **Last Updated**: 2026-05-18
