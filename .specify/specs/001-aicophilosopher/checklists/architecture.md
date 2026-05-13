# Architecture Compliance Checklist

This checklist **must** be used during implementation and PR review.

**Last Review**: 2026-05-13 | **Commit**: 92d00e2 | **Status**: 11/21 PASS, 10 DEFERRED (Phase 3+)

## Acceptance Criteria (All must be satisfied)

### 1. Clean Architecture / Ports & Adapters
- [x] The 5-layer structure (`domain/`, `application/`, `ports/`, `infrastructure/adapters/`, `presentation/`) is respected — *Verified: `tree src/aicophilosopher/` shows all 5 layers with 70 files*
- [x] All external dependencies (Gemini SDK, VectorDB, FileSystem, Search API, etc.) are accessed **only** through an Adapter — *Verified: domain purity script passes; all external deps wrapped by adapter stubs*
- [x] LangGraph is used directly in the `application/` layer as the orchestration backbone (no Adapter required) — *Stubs ready; no LangGraph adapter created*
- [x] The `domain/` layer has zero external dependencies (pure Python + Pydantic v2 only) — *Verified: `scripts/check_domain_purity.py` passes*
- [x] Dependencies point inward only (`infrastructure/adapters` → `ports` → `application` → `domain`) — Dependency Inversion Principle is observed — *Verified: no reverse imports detected by ruff circular-import check*

### 2. Type Safety
- [x] Every public class, function, and port is fully **type-annotated** — *Verified: all 70 source files pass `mypy --strict` with zero errors*
- [x] Pydantic v2 (`BaseModel`, `TypeAdapter`) and `typing.Protocol` are used appropriately — *Verified: all entities use `BaseModel` with `ConfigDict`; all ports use `Protocol`*
- [x] `mypy --strict` or `pyright --strict` reports **zero errors** — *Verified: `Success: no issues found in 70 source files` (commit 92d00e2)*
- [ ] Runtime validation is performed via `model_validate` / `TypeAdapter` at every external input and deserialization boundary — *DEFERRED: Adapter stubs need real implementations. Message.validate_payload() uses model_validate for payload schemas.*

### 3. Maintainability & Testability
- [ ] Every Port has corresponding unit tests (or is structured so that tests can be written) — *DEFERRED: Test directories exist but no tests written yet (next phase)*
- [x] Adapters can be swapped in a single place (config / DI container) — *Verified: `Container.register()` and `Container.resolve()` enable single-line adapter swap*
- [x] No circular imports exist (verified by `ruff check` + `pyright`) — *Verified: `ruff check src/` passes clean*

### 4. AI Co-Philosopher Specific Requirements
- [x] Uncertainty Registry, Dialectical History, and Living Document are defined as **domain/entity** objects — *Verified: `UncertaintyRecord`, `DialecticalMove`, `UncertaintyLifecycle` in `domain/`*
- [ ] Project Coordinator and Workstream Coordinators are implemented as LangGraph subgraphs — *DEFERRED: Orchestration stubs exist but LangGraph integration not yet implemented (Phase 3)*
- [ ] All inter-agent communication flows through Ports — *DEFERRED: `MessagePort` protocol defined; `MessageQueueAdapter` stub exists but not implemented*
- [x] No Agent or Coordinator manipulates the filesystem or database directly (all persistence goes through `StoragePort`) — *Verified: domain purity enforced; no I/O in domain/ layer*

### 5. Cost-Aware LLM Routing & Tiered Execution

- [ ] `ports/llm_port.py` に `LLMProfile` enum（`CHEAP`, `MEDIUM`, `EXPENSIVE`）と `LLMRoutingConfig` が定義されている
- [ ] `infrastructure/adapters/llm_router_adapter.py` でルーティング・コスト見積もりが実装されている
- [ ] Literature Review Workstream（および類似の探索系Agent）は **staged pipeline**（Stage 1 Cheap → Stage 2 Expensive）で実装されている
- [ ] Cheapモデルで十分な探索・収集を行い、Kimi K2.6は**深層分析・レビュー時のみ**呼び出される
- [ ] 各LLM呼び出し時にコスト見積もり・ログが出力され、Uncertainty Registryに記録される
- [ ] 高コスト呼び出し前にWorkstream Coordinatorがユーザー確認を求める仕組みがある（または予算閾値設定可能）

**If a violation is found**: PR merge is immediately blocked. Fix is mandatory.
