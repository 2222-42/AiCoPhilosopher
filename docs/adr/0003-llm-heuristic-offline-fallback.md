# ADR-0003: LLM fallback — heuristic offline is a production path

- **Status:** Accepted
- **Date:** 2026-07-19
- **Deciders:** project maintainers (Issue #67)
- **Related:** Constitution I (Core Independence) & IV (Testing / no network),
  `LLMPort`, agent modules under `application/agents/`,
  `tests/verification/test_constitution.py` (T-073)

## Context

Agents can optionally call an LLM through **`LLMPort`**
(`ports/llm_port.py`) with concrete adapters (Ollama, Claude, Gemini, …).
Early design also assumes richer LLM-backed analysis for many workstreams.

Constitutional constraints conflict with “LLM always on”:

- **Principle I** — fully self-contained; must work without external services.
- **Principle IV** — core tests MUST NOT require network access.
- Cost-aware tiering (constitution §3.5) implies LLM is valuable but not free.

The implementation already encodes a two-layer strategy in multiple agents
(argumentation, critical review, synthesis, cross-traditional, concept
analysis, literature search):

1. Build a **heuristic / template / pattern-based** result with no model call.
2. If `llm is not None` (and `use_llm` is allowed), attempt LLM refinement;
   on failure or empty parse, **keep or merge the heuristic result**.

Verification suite `TestConstitutionIOfflineOperation` constructs agents with
`llm=None` and asserts non-empty structured outputs. That suite is not a
dev-only convenience: it **defines** the offline production guarantee.

## Decision

**Heuristic (offline) execution is a first-class production path, not a test stub.**

1. **Default capability**
   - Every core agent MUST produce a usable result when no LLM backend is
     configured or when the backend is unreachable.
   - `LLMPort` is an **optional enhancer**. Call sites treat `llm is None` as
     normal, not as a hard error.

2. **Failure policy when LLM is present**
   - Timeouts, API errors, schema-invalid output, and empty parses MUST fall
     back to the heuristic path (or a documented merge of heuristic + partial
     LLM data). They MUST NOT crash the workstream solely because the model
     failed.

3. **Quality signaling**
   - Offline / heuristic outputs MUST still carry confidence scores and
     uncertainty where the domain model requires them (Constitution II).
   - When a result is heuristic-only, agents SHOULD make that visible in
     metadata or lower confidence rather than silently claiming model-grade
     certainty (implementations may improve labeling over time; the rule is
     not to hide the degradation).

4. **Testing contract**
   - The verification tests under T-073 (and equivalent unit tests that run
     agents with `llm=None`) are **normative**. Regressions that make core
     agents require a live LLM are constitution violations.
   - Mocks may exercise the LLM branch; the offline branch remains mandatory.

5. **External search / tools**
   - Networked tools (literature APIs, external agent bridges) follow the same
     spirit: disabled or failed tools degrade to local/heuristic behavior under
     consent and config flags (`allow_external_search`, etc.). Detailed search
     policy may get its own ADR later; this ADR binds the **LLM** path.

## Consequences

### Positive

- Guarantees a working research loop on air-gapped machines and in CI.
- Separates “product works” from “product is smart with a model.”
- Encourages pure domain heuristics that remain reviewable without prompt
  opacity.

### Negative / risks

- Heuristic quality is uneven across topics; users may over-trust offline
  drafts if confidence labeling is weak.
- Maintaining dual paths (heuristic + LLM parse/merge) increases agent
  complexity.

### Follow-ups

- Improve explicit “source: heuristic | llm | mixed” tagging in agent results.
- Keep cost-aware routing (when LLM is on) consistent with constitution §3.5
  without ever removing the offline base path.
- Issue #66 (verification E2E) should continue to include offline scenarios.

## Alternatives considered

1. **LLM-required production path; heuristics only in unit tests** — Rejected:
   breaks Constitution I/IV and local-first product promise.
2. **Silent no-op when LLM missing** — Rejected: produces empty research
   sessions and masks configuration errors without delivering value.
3. **Hard-coded remote model with offline cache only** — Rejected: still
   requires prior network seeding; not acceptable as the sole mode.
