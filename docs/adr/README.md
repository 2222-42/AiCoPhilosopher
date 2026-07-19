# Architecture Decision Records (ADRs)

This directory records **significant, hard-to-reverse design decisions** for AiCoPhilosopher.

ADRs are the source of truth for *why* the system is shaped the way it is.
Specifications under `.specify/` describe *what* to build; ADRs capture the
trade-offs that constrain later implementation.

## Format

Each ADR is a Markdown file named `NNNN-short-title.md` (zero-padded sequential
number). Recommended sections:

| Section | Purpose |
|---------|---------|
| **Status** | `Proposed` / `Accepted` / `Superseded by ADR-NNNN` / `Deprecated` |
| **Context** | Forces, constraints, and the problem that required a decision |
| **Decision** | The chosen option, stated as a binding rule |
| **Consequences** | Positive / negative / follow-ups and known gaps |
| **Alternatives considered** | Options that were rejected and why |

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-persistence-source-of-truth.md) | Persistence source of truth (FS + StoragePort) | Accepted |
| [0002](0002-orchestration-handmade-coordinator.md) | Orchestration: handmade Coordinator is canonical | Accepted |
| [0003](0003-llm-heuristic-offline-fallback.md) | LLM fallback: heuristic offline is a production path | Accepted |

## When to add an ADR

Write a new ADR when you:

- Choose between mutually exclusive architectural options
- Introduce or retire a hard dependency that shapes the core
- Change a local-first / privacy / offline guarantee
- Supersede an existing decision (link both ways)

Trivial implementation choices (variable names, pure refactors) do **not** need ADRs.
