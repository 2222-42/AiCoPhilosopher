# Research: AiCoPhilosopher v2.0 Technical Decisions

**Date**: 2026-05-13  
**Feature**: AiCoPhilosopher v2.0  
**Source**: Specification `.specify/specs/001-aicophilosopher/spec.md`, Constitution `.specify/memory/constitution.md`

---

## 1. Orchestration Framework

### Decision: LangGraph

**Rationale**:
LangGraph is the only mature Python framework that natively supports all three requirements from the specification:
1. **Stateful graph execution**: Philosophical research requires long-running state persistence across sessions. LangGraph's checkpointing persists graph state to SQLite or memory, enabling session resumption (spec §2, §3.2).
2. **Human-in-the-loop breakpoints**: The Project Coordinator must be able to pause workstreams, request user approval, and steer agents dynamically. LangGraph's `interrupt` and `Command` primitives support this natively (spec §4.1, §5.2).
3. **Hierarchical delegation**: Workstream Coordinators are subgraphs that can run in parallel. LangGraph supports nested graphs and conditional edges for routing between agents (spec §3.1).

**Alternatives considered**:
- **AutoGen** (Microsoft): Excellent for conversational multi-agent scenarios but lacks native stateful checkpointing and hierarchical graph composition. Its group chat pattern does not map cleanly to the workstream coordinator → sub-agent hierarchy required by the Co-Philosopher design.
- **CrewAI**: Higher-level abstraction with pre-defined agent roles. Too rigid for the custom philosophical agent hierarchy (Cross-Traditional Comparison, Phenomenological Description) and does not support the fine-grained state management required for uncertainty tracking.
- **Custom framework**: Would satisfy all requirements but violates the MVP-first principle (Constitution Principle V). Estimated 3-4 months of framework development before feature work could begin.

**Trade-offs**:
- LangGraph is relatively new (v0.2.x) and API-breaking changes occur between minor versions. Mitigation: pin to `>=0.2.0,<0.3.0` and abstract LangGraph-specific code behind internal wrappers in `core/`.
- LangGraph's default checkpointing serializes state with `pickle` which can be brittle with Pydantic v2 models. Mitigation: implement custom `BaseCheckpointSaver` using JSON serialization.

---

## 2. Vector Database for RAG

### Decision: ChromaDB (MVP), LanceDB (future scaling)

**Rationale**:
The specification requires local-first RAG over uploaded papers with tradition-aware metadata filtering (spec §4.2, §6.3). ChromaDB provides:
1. **File-based persistence**: `PersistentClient` stores data in a local directory, requiring no external server process. This satisfies the local-first constraint (Constitution Principle I).
2. **Metadata filtering**: `where={"tradition": "philosophy_of_technology"}` enables tradition-specific retrieval, which is critical for the Cross-Traditional Comparison Agent (spec §4.4).
3. **Simple Python API**: Single `pip install chromadb` with no system dependencies. Fits the self-hostable requirement (spec §9).

**Alternatives considered**:
- **LanceDB**: Better performance (columnar format, vector indexing), smaller disk footprint, and supports SQL-like queries. However, it requires `pylance` native bindings which can have platform-specific installation issues. Selected as the post-MVP migration target when RAG corpus exceeds 1k documents.
- **FAISS** (Meta): Extremely fast similarity search but no native metadata filtering or persistence. Would require building a custom metadata layer on top, adding unnecessary complexity.
- **Weaviate / Pinecone**: Cloud-native solutions that violate the local-first constraint (Constitution Principle I). Explicitly rejected.

**Trade-offs**:
- ChromaDB's default embedding function (`all-MiniLM-L6-v2`) is English-centric and may underperform on non-Western philosophical texts. Mitigation: allow user-configurable embedding models (e.g., multilingual E5, OpenAI `text-embedding-3-large` for users who opt in).
- ChromaDB can be memory-hungry with large collections. Mitigation: one collection per project, aggressive cleanup of completed workstream embeddings.

---

## 3. LLM Backend Abstraction

### Decision: Custom lightweight adapter (not LiteLLM)

**Rationale**:
The specification requires support for exactly three backends: Claude (Anthropic), Gemini (Google), and Ollama (local) (spec §10.1). A custom adapter:
1. **Minimizes dependencies**: LiteLLM pulls 20+ transitive dependencies including HTTP clients, caching layers, and proxy server components. This increases supply-chain risk and binary size, violating the self-hostable requirement.
2. **Enforces privacy**: LiteLLM's proxy mode can inadvertently route requests through external endpoints. A custom adapter ensures every API call is explicit and logged, satisfying the explicit-consent requirement (spec §4.2, §9).
3. **Follows Adapter Pattern**: The specification mandates an Adapter Pattern for external orchestration layers (spec §8). A custom LLM adapter is a natural extension of this architectural principle.

**Adapter design**:
```python
class LLMBackend(ABC):
    @abstractmethod
    async def generate(self, messages: list[Message], tools: list[Tool] | None = None) -> GenerationResult: ...
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[Embedding]: ...

class ClaudeBackend(LLMBackend): ...
class GeminiBackend(LLMBackend): ...
class OllamaBackend(LLMBackend): ...
```

**Alternatives considered**:
- **LiteLLM**: Would reduce adapter code by ~60% but at the cost of dependency bloat and potential privacy leaks. Rejected per Constitution Principle I (local-first privacy).
- **LangChain ChatModels**: LangChain's chat model abstraction is reasonable but couples the core to LangChain's ecosystem. The specification requires core independence from external layers; LangChain is acceptable as a core dependency but we prefer minimal coupling.

---

## 4. PDF Processing for RAG

### Decision: PyMuPDF (fitz)

**Rationale**:
Philosophical papers are often scanned legacy texts with complex layouts (footnotes, marginalia, mixed columns). PyMuPDF provides:
1. **Robust text extraction**: Handles scanned PDFs via OCR integration (Tesseract), multi-column layouts, and footnotes better than alternatives.
2. **Metadata access**: Extracts title, author, creation date, and embedded outlines (table of contents) which feed into the Literature Search Agent's structured output (spec §4.2).
3. **Performance**: C++ backend extracts a 50-page philosophy paper in <2 seconds on modern hardware.

**Alternatives considered**:
- **pdfplumber**: Pure Python, easier to debug, but 5-10x slower and struggles with multi-column academic papers.
- **PyPDF2**: Lightweight but frequently fails on encrypted or malformed PDFs common in preprints.
- **marker / nougat**: ML-based PDF-to-Markdown converters with excellent accuracy but require GPU and large model downloads. Overkill for MVP.

**Trade-offs**:
- PyMuPDF uses a custom AGPL/commercial dual license. The project is open-source (self-hostable) so AGPL is acceptable, but commercial usage would require a license. Mitigation: document this in `LICENSE` and `README.md`.

---

## 5. Terminal UI Framework

### Decision: Rich + Click

**Rationale**:
The specification requires progressive disclosure (spec §4.1, §5.3): concise summary → expandable details → suggestions. Rich provides:
1. **Collapsible panels**: `rich.panel.Panel` with `expandable=True` (or custom implementation using `rich.layout`) for `[Details]` and `[Suggestions]` sections.
2. **Live display**: `rich.live.Live` for updating workstream status in real-time without flooding the terminal.
3. **Markdown rendering**: `rich.markdown.Markdown` renders the living document and margin annotations with syntax highlighting.

Click provides robust command parsing for steering commands (`pause`, `resume`, `steer`, etc.).

**Alternatives considered**:
- **Textual**: Full TUI framework with widgets, events, and layouts. Would enable a more sophisticated interface but adds significant complexity (~6 weeks of UI development vs 1 week with Rich). Deferred to post-MVP (Phase 4).
- **InquirerPy**: Good for interactive prompts but lacks live display and markdown rendering.
- **Blessed / urwid**: Lower-level terminal control; too much boilerplate for MVP.

---

## 6. Formal Logic & Validity Checking

### Decision: Z3-Solver (MVP), Prolog skeleton (post-MVP)

**Rationale**:
The Argumentation Agent must evaluate argument validity (spec §4.5). Z3 provides:
1. **SMT solving**: Determines satisfiability of propositional and first-order formulas. Can verify basic syllogisms, modal logic formulas (via encoding), and consistency of premise sets.
2. **Python integration**: `z3-solver` package is pure Python with bundled native libraries. No external prover installation required.
3. **Speed**: Millisecond-level checking for typical philosophical arguments (3-10 premises).

**Prolog skeleton** (post-MVP): For symbolic reasoning about conceptual relationships (e.g., "if all x are y and all y are z, then all x are z"), Prolog's unification and backward chaining are more natural than SMT encoding.

**Alternatives considered**:
- **Lean 4** (lean4py): The most powerful formal system for mathematics. However, it requires a 200MB+ toolchain download and deep expertise in dependent type theory. Overkill for philosophical argument checking where full formalization is rarely possible (spec §4.5: "informal argument schemes" must also be supported).
- **Natural Language Inference (NLI) models**: Zero-shot NLI (e.g., using LLMs to check entailment) is too unreliable for the 70% validity threshold required by AC-005. Rejected for core logic; may be used as a supplementary heuristic.

**Trade-offs**:
- Z3 cannot directly handle informal arguments, abductive reasoning, or phenomenological descriptions. These remain the domain of LLM-based agents with explicit confidence scores. Z3 is strictly a validation layer, not a reasoning engine.

---

## 7. Message Transport & Agent Communication

### Decision: Shared filesystem + SQLite-backed message queue

**Rationale**:
The AI Co-Mathematician uses a shared filesystem and internal messaging system (paper §3.1). For the Co-Philosopher, this design is ideal because:
1. **Zero network overhead**: All agents run on the same machine. No TCP ports, no serialization overhead, no firewall issues.
2. **Full auditability**: Every message is a JSON file on disk. Developers can inspect agent conversations with `cat` or `jq`.
3. **Natural local-first architecture**: No message broker (RabbitMQ, Redis) required, satisfying Constitution Principle I.
4. **Async safety**: SQLite handles concurrent writes from multiple workstream coordinators. The filesystem handles large payloads (reports, code attachments).

**Protocol design**:
```python
class Message(BaseModel):
    message_id: UUID
    sender_id: str           # agent identifier
    recipient_id: str        # agent identifier or "broadcast"
    message_type: MessageType  # status_update, delegation_request, steering_command, help_request, review_request, result_delivery
    payload: dict[str, Any]  # type-specific payload
    timestamp: datetime
    epistemic_status: EpistemicStatus  # confidence, review_status, tradition_context
```

**Alternatives considered**:
- **gRPC**: Efficient binary protocol with schema enforcement. However, requires protobuf compilation and network stack, violating the zero-network local-first constraint.
- **MQTT (mosquitto)**: Lightweight pub/sub but requires a broker process. Adds operational complexity for a single-user application.
- **Redis Streams**: Fast in-memory message queue but requires Redis server and loses messages on restart unless persisted.

---

## 8. State Persistence Strategy

### Decision: LangGraph checkpointing (graph state) + SQLite (metadata/messages/uncertainty) + Filesystem (documents)

**Rationale**:
The specification requires session resumption for long-running projects (spec §2, §3.2). This three-tier approach:
1. **LangGraph checkpointing**: Automatically persists the execution state of each agent graph (which node is active, what decisions were made) using the `SqliteSaver` backend.
2. **SQLite**: Stores structured relational data: projects, workstreams, messages, uncertainty records, review rounds. `aiosqlite` provides async access.
3. **Filesystem**: Stores unstructured data: Markdown documents, PDFs, generated code, LaTeX outputs. Organized per-project as specified in spec §3.2.

**Schema versioning**: SQLite schema managed via `yoyo-migrations` (lightweight, Python-native) or manual versioned migration scripts. For MVP, manual migrations are acceptable (≤10 tables).

**Alternatives considered**:
- **PostgreSQL**: More robust for concurrent access but requires server setup. Violates self-hostable/zero-config requirement.
- **DuckDB**: Analytical queries on JSON/CSV but less mature for transactional workloads with concurrent writers.
- **JSON files only**: Simple but lacks ACID guarantees for message queue and uncertainty registry updates.

---

## 9. Review Process Algorithm

### Decision: Iterative multi-reviewer with deterministic round limits and escalation

**Rationale**:
The Co-Mathematician paper identifies "reviewer-pleasing bias" and "intractable disagreements / non-termination" as major risks (paper §7). The Co-Philosopher review algorithm must prevent both:

**Algorithm**:
```
function Review(report, reviewers=[AgentA, AgentB], max_rounds=5):
    for round in 1..max_rounds:
        verdicts = []
        for reviewer in reviewers:
            verdict = reviewer.review(report)
            verdicts.append(verdict)
        
        if all(v.status == "approved" for v in verdicts):
            return ReviewResult(status="approved", rounds=round)
        
        if round == max_rounds:
            return ReviewResult(status="escalated", rounds=round, verdicts=verdicts)
        
        # Merge feedback into revision request
        report = WorkstreamCoordinator.revise(report, verdicts)
    
    return ReviewResult(status="stalled", reason="max_rounds_exceeded")
```

**Reviewer diversity**: Each reviewer agent is initialized with a different "methodological lens" (e.g., one analytic logician, one phenomenological critic) to reduce false consensus (paper §7, "reviewer-pleasing bias").

**Escalation**: On `escalated` or `stalled`, the WorkstreamCoordinator surfaces a clear alert to the Project Coordinator, which presents it to the user with context (spec §3.4, §6.4).

**Alternatives considered**:
- **Single reviewer**: Faster but misses the adversarial dynamics needed to catch subtle errors. Rejected.
- **Majority voting with 3+ reviewers**: More robust but computationally expensive (3× LLM calls per round). Deferred to post-MVP.
- **Human-in-the-loop every round**: Too interruptive for async workstreams. Human is only notified on escalation or completion.

---

## 10. Tradition Representation & Norm Enforcement

### Decision: JSON profile files + runtime `TraditionRegistry`

**Rationale**:
The Cross-Traditional Comparison Agent must evaluate arguments within native methodological frameworks (spec §4.4). Storing tradition norms as structured JSON enables:
1. **Extensibility**: New traditions (e.g., African philosophy, Islamic falsafa) can be added by dropping a JSON file into `data/traditions/` without code changes.
2. **Versioning**: Tradition profiles can evolve independently of the core codebase.
3. **Testability**: Tradition norms are explicit and unit-testable, unlike hardcoded prompts.

**Tradition profile schema**:
```json
{
  "id": "philosophy_of_technology",
  "name": "Philosophy of Technology",
  "assumptions": ["technology is not neutral; it embodies values", "artefacts have politics (Winner)", "human-technology co-constitution"],
  "methodological_norms": ["empirical case study", "conceptual analysis of technological mediation", "ethnography of use"],
  "evaluative_criteria": ["conceptual clarity", "empirical grounding", "normative sensitivity", "technological plausibility"],
  "key_figures": ["Heidegger", "Ellul", "Winner", "Latour", "Ihde", "Verbeek"],
  "bridge_warnings": ["software abstraction vs mathematical abstraction: partial overlap but different normative stakes"]
}
```

**Norm enforcement**: The `TraditionManager` (spec §3.3) loads these profiles and validates agent outputs against tradition-specific criteria. For example, a phenomenological description generated by the Concept Analysis Agent can be checked against Husserlian epoché requirements.

**Alternatives considered**:
- **Hardcoded prompts**: Simple but inflexible. Adding a new tradition requires code changes and redeployment. Rejected.
- **LLM-generated tradition norms**: Dynamic but unreliable. The system must guarantee that tradition profiles are stable and auditable. Rejected for core norms; may be used as a suggestion engine for user-created traditions.

---

## 11. Uncertainty Tracking Implementation

### Decision: SQLite `uncertainty_registry` table + inline Markdown annotations

**Rationale**:
The specification requires every non-trivial claim to carry confidence scores, counter-argument strength, tradition validity, and review status (spec §6.3). A dual approach:
1. **SQLite registry**: Authoritative structured storage for querying, filtering, and lifecycle management. Enables fast retrieval of "all contested claims in the active document" or "all claims with confidence < 0.5."
2. **Inline Markdown annotations**: Human-readable provenance embedded directly in the living document. Ensures the document is self-contained and portable.

**Synchronization**: The Synthesis Agent is responsible for keeping inline annotations and the SQLite registry in sync. On document save, annotations are parsed and upserted into the registry. On registry update (e.g., review status change), the living document is re-rendered.

**Uncertainty lifecycle state machine**:
```
unreviewed → under_review → contested → accepted_with_reservations → rejected
                     ↘--------→ accepted_with_reservations
                     ↘--------→ rejected
```

**Alternatives considered**:
- **Pure inline annotations**: No separate database. Simple but querying becomes O(n) text parsing. Rejected for performance (AC-007 requires <30s status reflection).
- **Graph database (Neo4j)**: Excellent for modeling claim relationships but requires external server. Violates local-first constraint.

---

## 12. Embedding Model Strategy

### Decision: `sentence-transformers/all-MiniLM-L6-v2` (default), user-configurable

**Rationale**:
The default model is small (80MB), fast, and works offline. However, philosophical texts contain technical jargon, non-English terms (e.g., Dasein, epoché, mathesis), and nuanced argumentation.

**Configuration**:
```yaml
# config.yaml
embedding:
  default_model: "sentence-transformers/all-MiniLM-L6-v2"
  fallback_model: "intfloat/multilingual-e5-large"  # for non-Western texts
  device: "cpu"  # or "cuda" if available
```

**Post-MVP**: Fine-tune a philosophy-specific embedding model on PhilPapers abstracts + SEP entries. This would improve retrieval precision from 70% to potentially 85%+ (AC-002).

---

## 13. Summary of Technology Stack

| Layer | Technology | Version | Justification |
|-------|-----------|---------|---------------|
| Language | Python | 3.11+ | Typing, async, performance |
| Orchestration | LangGraph | 0.2.x | Stateful graphs, checkpointing, HITL |
| Schema / Validation | Pydantic | 2.7+ | Type safety, JSON serialization |
| Vector DB | ChromaDB | 0.5+ | Local, metadata filtering, simple API |
| Relational DB | SQLite | 3.39+ | Local, zero-config, async via aiosqlite |
| CLI UI | Rich + Click | 13+ / 8+ | Progressive disclosure, live display, command parsing |
| PDF Processing | PyMuPDF | 1.24+ | Robust extraction, metadata access, speed |
| Formal Logic | Z3-Solver | 4.13+ | SAT/SMT for argument validity |
| LLM Backends | Custom adapter | — | Minimal deps, privacy, Adapter Pattern |
| Testing | pytest + asyncio | 8+ | Async testing, mocking, coverage |
| Migrations | Manual SQL | — | Lightweight for MVP schema (≤10 tables) |
| Packaging | pyproject.toml | — | Modern Python standards |

**Total production dependencies** (estimated): ~15 direct, ~50 transitive. Well within reasonable bounds for a self-hostable CLI application.

---

## 14. Open Questions for Post-MVP

1. **Fine-tuned embedding model**: Is the retrieval precision gain (70% → 85%) worth the training infrastructure cost?
2. **Lean 4 integration**: Can formal proof assistants verify informal philosophical arguments via auto-formalization? Likely limited to analytic philosophy subdomains.
3. **Distributed workstreams**: If users request cloud-scale compute for large literature reviews, how does the local-first architecture extend to optional remote execution without violating privacy?
4. **Real-time collaboration**: Multi-user editing of the living document would require CRDTs or operational transformation. Deferred until single-user experience is polished.

---

**Research Version**: 1.0.0 | **Last Updated**: 2026-05-13
