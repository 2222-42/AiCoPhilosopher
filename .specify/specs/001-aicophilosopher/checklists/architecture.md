# Architecture Compliance Checklist

This checklist **must** be used during implementation and PR review.

## Acceptance Criteria (All must be satisfied)

### 1. Clean Architecture / Ports & Adapters
- [ ] The 5-layer structure (`domain/`, `application/`, `ports/`, `infrastructure/adapters/`, `presentation/`) is respected
- [ ] All external dependencies (Gemini SDK, VectorDB, FileSystem, Search API, etc.) are accessed **only** through an Adapter
- [ ] LangGraph is used directly in the `application/` layer as the orchestration backbone (no Adapter required)
- [ ] The `domain/` layer has zero external dependencies (pure Python + Pydantic v2 only)
- [ ] Dependencies point inward only (`infrastructure/adapters` → `ports` → `application` → `domain`) — Dependency Inversion Principle is observed

### 2. Type Safety
- [ ] Every public class, function, and port is fully **type-annotated**
- [ ] Pydantic v2 (`BaseModel`, `TypeAdapter`) and `typing.Protocol` are used appropriately
- [ ] `mypy --strict` or `pyright --strict` reports **zero errors**
- [ ] Runtime validation is performed via `model_validate` / `TypeAdapter` at every external input and deserialization boundary

### 3. Maintainability & Testability
- [ ] Every Port has corresponding unit tests (or is structured so that tests can be written)
- [ ] Adapters can be swapped in a single place (config / DI container)
- [ ] No circular imports exist (verified by `ruff check` + `pyright`)

### 4. AI Co-Philosopher Specific Requirements
- [ ] Uncertainty Registry, Dialectical History, and Living Document are defined as **domain/entity** objects
- [ ] Project Coordinator and Workstream Coordinators are implemented as LangGraph subgraphs
- [ ] All inter-agent communication flows through Ports
- [ ] No Agent or Coordinator manipulates the filesystem or database directly (all persistence goes through `StoragePort`)

**If a violation is found**: PR merge is immediately blocked. Fix is mandatory.
