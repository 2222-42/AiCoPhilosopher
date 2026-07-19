# ADR-0001: Persistence source of truth (filesystem + StoragePort)

- **Status:** Accepted
- **Date:** 2026-07-19
- **Deciders:** project maintainers (Issue #67)
- **Related:** Constitution I (Local-First Privacy), StoragePort, FileSystemAdapter, SQLiteAdapter, Issue #61 / #62 / #63

## Context

AiCoPhilosopher is a local-first research workbench. Project state currently
lands in more than one place:

1. **Filesystem project tree** — CLI commands default to `./projects/<id>/`
   (`presentation/commands.py`) and also talk to `FileSystemAdapter` rooted at
   `Config.workspace_dir` (default `~/.aicophilosopher`). Artifacts include
   `metadata.json`, `living_document.md`, workstream outputs, margin notes,
   logs, and a per-project `vector_db/`.
2. **SQLite schema** — `SQLiteAdapter` owns tables for projects, workstreams,
   hypotheses, uncertainty, messages, **sessions**, dialogue turns, approval
   requests, and related indexes (`infrastructure/adapters/sqlite_adapter.py`).
3. **StoragePort** — a Protocol that both adapters are expected to satisfy for
   project/session I/O (`ports/storage_port.py`). Session persistence for the
   002-console-agent REPL is designed to go through this port
   (`presentation/session_manager.py`), but production wiring is still
   incomplete (see Issue #61).
4. **In-memory coordinator state** — `ProjectCoordinatorAgent.active_workstreams`
   is a plain `dict` that is not yet durably synced with FS or SQLite
   (Issue #63).

Without an explicit source-of-truth policy, later work (resume, multi-process
safety, export, CI fixtures) will keep inventing ad-hoc dual writes.

## Decision

**Split persistence by concern; do not force a single store for everything.**

| Concern | Canonical store | Access path |
|---------|-----------------|-------------|
| Project **artifacts** (living document, notes, exports, workstream result files, logs) | **Filesystem** under the configured workspace | `FileSystemAdapter` / project directory layout |
| Project **metadata** that must be queried (lists, status, hypotheses index, uncertainty registry) | Prefer **SQLite** via StoragePort; FS `metadata.json` remains a human-readable mirror / bootstrap until dual-write is retired |
| **Session / REPL** state (session row, dialogue turns, approvals, heartbeat) | **StoragePort only** — backend may be SQLite (preferred) or a FS-backed implementation of the same Protocol | `SessionManager` → `StoragePort` |
| **Ephemeral orchestration** state (in-flight workstream handles) | In-memory in the Coordinator; durable snapshots of IDs/status must be written through StoragePort or FS before process exit | see ADR-0002 |

Rules:

1. Application and presentation code MUST depend on **ports** (`StoragePort`,
   filesystem port/adapter interface), not on concrete SQLite or path constants,
   except at composition roots (CLI entrypoints).
2. New session features MUST NOT invent a third store outside StoragePort.
3. Workspace path resolution (`./projects` vs `AICOPH_WORKSPACE_DIR` /
   `~/.aicophilosopher`) is a configuration concern (Issue #62); the ADR
   requires a single resolved root at runtime, not two independent trees.
4. Vector / RAG indexes (ChromaDB under project `vector_db/`) are derived
   artifacts of the FS tree; they are not the system of record for claims.

## Consequences

### Positive

- Matches local-first UX: users can open `living_document.md` and project
  folders with ordinary tools.
- Session durability can mature behind StoragePort without rewriting documents.
- Tests can swap in-memory or temp-dir adapters without network or a shared DB.

### Negative / risks

- Dual representation of project metadata (FS JSON + SQLite) can drift until
  write paths are unified.
- Operators must understand which store to back up (workspace tree **and**
  SQLite file, when used).

### Follow-ups (out of scope for this ADR)

- Wire production SessionManager to a real StoragePort backend (Issue #61).
- Unify workspace path resolution (Issue #62).
- Persist workstream results out of the in-memory dict (Issue #63).
- Optionally drop redundant `metadata.json` fields once SQLite is always
  present, or treat FS as export-only.

## Alternatives considered

1. **SQLite-only for everything** — Rejected for MVP/local-first: living
   documents and notes are first-class files users edit and export; stuffing
   large Markdown blobs solely into BLOB columns hurts inspectability.
2. **Filesystem-only (no SQLite)** — Rejected for sessions and relational
   queries (one-active-session index, heartbeat reclaim, approval queues).
   Those need transactional updates that JSON files handle poorly.
3. **External DB (Postgres, etc.)** — Rejected: violates Constitution I
   (self-contained, local-first) for the default path. External DBs may appear
   only as optional adapters later.
