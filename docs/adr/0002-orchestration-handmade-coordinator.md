# ADR-0002: Orchestration — handmade Coordinator is canonical

- **Status:** Accepted
- **Date:** 2026-07-19
- **Deciders:** project maintainers (Issue #67)
- **Related:** Constitution (Architecture Constraints mention LangGraph),
  `application/orchestration/*`, `external_bridge_adapter.py`, Issue #60

## Context

Early design docs (`docs/init/design.md`) and the project constitution describe
**LangGraph** (or an equivalent stateful multi-agent framework) as the default
internal orchestration layer, with external bridges (Hermes, OpenCode Go)
falling back to “internal LangGraph execution.”

What the codebase actually runs today:

- **`ProjectCoordinatorAgent`** (`application/orchestration/coordinator.py`) —
  a handmade class over `BaseAgent`. Dialogue, goal approval, and workstream
  bookkeeping use ordinary Python control flow and an in-memory
  `active_workstreams: dict[str, dict]`.
- **`WorkstreamCoordinatorAgent`** and a simple type registry
  (`workstream_coordinator.py`) — also handmade, not a graph runtime.
- **Specialized agents** (literature, concept, argumentation, etc.) are plain
  async classes invoked as use-cases, not LangGraph nodes.
- **`langgraph` is listed in `pyproject.toml`** but there is **no runtime
  `import langgraph` / graph definition** driving the product path.
- **`ExternalAgentBridge.fallback`** documents “LangGraph fallback” in strings
  and comments, yet returns a structured fallback payload without invoking a
  graph engine.

Treating the constitution text as binding would force a large rewrite that the
MVP does not use. Treating LangGraph as already adopted would mislead
contributors and reviewers.

## Decision

**The handmade Coordinator hierarchy is the canonical orchestration model.**

1. **Canonical runtime**
   - Project-level orchestration: `ProjectCoordinatorAgent`
   - Workstream-level orchestration: `WorkstreamCoordinatorAgent` (+ type
     registry)
   - Agent execution: application-layer agent classes called from coordinators
     / CLI / REPL (Ports & Adapters; no framework graph required)

2. **LangGraph status**
   - **Not part of the production control plane today.**
   - Remains an **optional future candidate** if/when we need durable graph
     checkpoints, complex branching policies, or standardized multi-agent
     topologies that justify the dependency cost.
   - Until a dedicated ADR supersedes this one, **do not** build new features
     that require LangGraph APIs.
   - **Dependency removal** (`langgraph` from `pyproject.toml`) is allowed as a
     follow-up cleanup once call sites and docs no longer claim it; it is
     **not** required by this ADR’s acceptance (documentation-first).

3. **External bridges**
   - Remain optional enhancers (Constitution I).
   - On failure or disablement, fallback MUST return control to the **handmade
     internal path** (Coordinator + agents), not to a non-existent LangGraph
     runtime. Comments/messages that say “LangGraph fallback” should be read
     as historical wording until updated.

4. **Constitution / design drift**
   - This ADR **supersedes** the constitution’s “implemented using LangGraph as
     the default orchestration layer” wording for practical engineering
     decisions until the constitution is amended to match.
   - Specs may still mention LangGraph as an aspirational or alternative
     backend; implementers follow this ADR.

## Consequences

### Positive

- Matches the code that ships and is tested.
- Keeps orchestration inspectable and debuggable without a graph DSL.
- Aligns with MVP-first delivery: finish Coordinator → Agent wiring
  (Issue #60) before introducing another framework.

### Negative / risks

- Temporary inconsistency with constitution and `docs/init/design.md` until
  those are amended.
- Unused `langgraph` dependency may confuse dependency audits and inflate
  install size until removed or justified.

### Follow-ups

- Issue #60: wire workstream launch to real agent execution (still under the
  handmade model).
- Amend constitution Architecture Constraints to say “handmade Coordinator
  (LangGraph optional)” or equivalent.
- Either remove `langgraph` dependency or land a real adapter behind a port
  with a new ADR.

## Alternatives considered

1. **Adopt LangGraph now as the real orchestrator** — Rejected for current
   scope: no existing graph, high rewrite cost, blocks higher-priority
   wiring/persistence issues. Revisit only with a concrete graph design and
   migration plan.
2. **Adopt another framework (CrewAI, AutoGen, etc.)** — Rejected: same cost
   as LangGraph, plus weaker fit with local-first / offline guarantees.
3. **Keep dual story (“LangGraph is default” in docs, handmade in code)** —
   Rejected: this ADR exists precisely to end that ambiguity.
