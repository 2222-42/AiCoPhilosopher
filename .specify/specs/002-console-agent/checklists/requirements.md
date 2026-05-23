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
- [x] REPL Rendering contract (`contracts/repl-rendering.md` — 5-section progressive disclosure format)
- [x] NLU Intent Schema (`contracts/nlu-intent-schema.md` — 16 intent types, entity schemas, classification prompt, fallback)

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

- [x] Principle I (Core Independence): REPL wraps existing Project Coordinator; no new orchestration layers. Rich + SQLite are local, open-source. ✅
- [x] Principle I (Local-First Privacy): FR-026 mandates no external data transmission without explicit consent. `external_search_consent` ApprovalRequest type gates all external calls. ✅
- [x] Principle II (Intellectual Honesty): FR-007 mandates Epistemic Status always visible. EpistemicSnapshot tracks claims/hypotheses. `/dead-ends` preserves failed explorations. ApprovalRequest with `blocking` urgency ensures human judgment gates. ✅
- [x] Principle III (Code Quality): Data model uses Pydantic BaseModel with validation rules. REPL is presentation-layer adapter wrapping core domain — Clean Architecture now explicit in spec Assumptions. ✅
- [x] Principle IV (Testing): SC-002 defines NLU accuracy test (≥90%, 100-utterance test set). SC-009 tests concurrent session detection. Session persistence testable via US2 scenarios. ✅
- [x] Principle V (MVP-First): P1 = natural language + session persistence (core). P2 = slash commands + full inquiry cycle (enhancement). Web UI deferred to Phase 4; additional languages post-MVP. ✅
- [x] Architecture Constraints: Python + LangGraph ✓, Pydantic ✓, Progressive disclosure (FR-007) ✓✓. RETRY LOGIC: not addressed for REPL-specific operations (stale reclaim, concurrent detection) — recommended for implementation phase. ⚠️
- [x] Dev Workflow: Progressive disclosure (FR-007 + contracts) ✓✓. Logging (FR-017 auditability) ✓. External Agent Bridge inherited from wrapped coordinator. ✅

**Constitution Review Result**: COMPLIANT — 2 minor recommendations for implementation phase (Clean Architecture reference, retry logic). No blocking violations.

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
3. Should the REPL support scrolling through command history (like readline)? ✅ Resolved — FR-027 added to spec.md.
4. Should the REPL support tab-completion of slash commands and project/workstream IDs?
5. How are binary files (PDF upload paths, export output paths) handled in the REPL? Currently via `/upload <path>` and `/export <format>`.

---

**Checklist Version**: 1.0.0 | **Last Updated**: 2026-05-18
