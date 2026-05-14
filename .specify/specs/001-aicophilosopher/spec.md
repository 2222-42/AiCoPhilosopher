# AI Co-Philosopher - Refined Specification (v2.0)

**Branch**: `feat/specify/init` | **Date**: 2026-05-13 | **Constitution**: `.specify/memory/constitution.md` v0.1.0

**Input**: Inspired by Google DeepMind's *AI Co-Mathematician* (arXiv:2605.06651v1, 2026); evolved from `docs/init/requirements.md`, `docs/init/spec.md`, `docs/init/design.md`; integrated with project constitution.

## 1. Overview & Design Philosophy

The AI Co-Philosopher is a stateful, hierarchical multi-agent workbench for philosophical research, strongly inspired by the *AI Co-Mathematician* paradigm but fundamentally reimagined for the unique epistemological and methodological demands of philosophy.

While mathematics pursues necessary truths through formal proof, philosophy engages with contingent conceptual frameworks, normative judgments, phenomenological descriptions, and cross-traditional worldviews. This demands a system that does not merely "solve" philosophical problems but *co-investigates* them through dialectical exploration, conceptual genealogy, and rigorous argumentation across diverse traditions.

### 1.1 Core Design Principles (derived from Co-Mathematician analogies)

| Co-Mathematician Principle | Co-Philosopher Analog | Rationale |
|---------------------------|----------------------|-----------|
| Embrace mathematics beyond proofs | **Embrace philosophy beyond arguments** | Philosophy involves conceptual clarification, phenomenological description, thought experiments, cross-traditional dialogue, and worldview comparison—not just premise-conclusion reasoning. |
| Support iterative refinement of intent | **Dialectical refinement of inquiry** | Philosophical questions are inherently vague and open-ended. The system MUST engage in Socratic clarification dialogue until the user's inquiry is sufficiently refined to launch workstreams. |
| Produce native mathematical artifacts | **Produce native philosophical artifacts** | Output is a living "working paper" with margin annotations, conceptual genealogy, dialectical history, and cross-traditional comparisons—not transient chat logs. |
| Enable async interaction & flexible steering | **Enable async philosophical investigation with steering** | Heavy workstreams (literature review across traditions, deep conceptual analysis) run in parallel while the user steers, intervenes, or redirects inquiry at any time. |
| Manage cognitive load via progressive disclosure | **Progressive disclosure for philosophical depth** | High-level summaries and strategic suggestions are shown first; detailed argument maps, counter-argument trees, and source analyses are available on demand. |
| Track, manage, and communicate uncertainty | **Track philosophical uncertainty and epistemic status** | Philosophical claims carry confidence scores, counter-argument strength ratings, tradition-specific validity flags, and explicit acknowledgment of methodological limitations. |
| Preserve history of failed explorations | **Preserve dialectical dead ends and refuted arguments** | In philosophy, refutation is as valuable as proof. Failed hypotheses, abandoned arguments, and rejected conceptual frameworks MUST be retained as first-class project history. |

### 1.2 Scope & Boundaries

**In Scope**:
- Philosophical research assistance across analytic, continental, pragmatic, Eastern (Buddhist, Confucian, Daoist), and indigenous philosophical traditions
- Conceptual analysis, argument reconstruction, counter-argument generation, phenomenological description, ethical dilemma analysis, metaphysical inquiry
- Living document generation with margin annotations and dialectical history
- Local-first, privacy-preserving operation with optional external layer integration

**Explicitly Out of Scope** (to prevent scope creep pre-MVP):
- Real-time collaborative editing by multiple human users
- Automated peer-review submission to journals
- Fully autonomous philosophical "discovery" without human oversight
- Translation of philosophical texts between languages (post-MVP feature)

## 2. Differentiation & Literature Survey

### 2.1 Existing Systems Landscape

| System / Approach | Capabilities | Limitations | Our Differentiation |
|-------------------|-------------|-------------|---------------------|
| **PhilPapers + SEP search** | Bibliographic search, structured taxonomy | Static, no agentic reasoning, no synthesis | Stateful multi-agent orchestration with synthesis and living document generation |
| **Argument mapping tools** (e.g., Kialo, Argumentful) | Visual argument mapping, pro/con structuring | No deep conceptual analysis, no cross-traditional support, no async workstreams | Native conceptual genealogy, cross-traditional comparison, async agentic workstreams |
| **General-purpose LLM chatbots** (Claude, GPT-4) | Broad philosophical knowledge, conversational | Transient state, no persistent workspace, no structured philosophical methodology, no uncertainty tracking | Persistent stateful workspace, structured agent roles, explicit uncertainty management, dialectical history preservation |
| **Formal logic provers** (Lean, Coq) | Formal proof verification | Limited to formal/analytic philosophy; cannot handle phenomenological, ethical, or cross-traditional inquiry | Supports both formal and informal reasoning; explicitly handles conceptual ambiguity and normative judgment |
| **AI Co-Mathematician** (DeepMind, 2026) | Agentic mathematical research, async workstreams, native artifacts | Optimized for formal proof and computation; no support for conceptual ambiguity, normative reasoning, or cross-traditional dialogue | Philosophy-specific agent roles, conceptual analysis, phenomenological description, ethical reasoning, cross-traditional support |

### 2.2 Differentiation Thesis

The AI Co-Philosopher is the first agentic AI system designed specifically for the **full messy reality of philosophical research**, not merely question-answering or argument mapping. Key differentiators:

1. **Cross-Traditional Competence**: Unlike systems rooted in analytic philosophy alone, the Co-Philosopher MUST support dialogue across Western (analytic, continental, pragmatic), Eastern (Buddhist, Confucian, Daoist), and indigenous traditions, recognizing incommensurability where it exists and seeking bridge concepts where possible.

2. **Dialectical History as First-Class Artifact**: The system treats the process of philosophical inquiry—failed arguments, abandoned hypotheses, conceptual revisions—as equally important to final conclusions, mirroring Lakatos's *Proofs and Refutations* but for philosophical methodology.

3. **Epistemic Status Transparency**: Every claim carries explicit metadata about confidence, methodological tradition, counter-argument strength, and phenomenological grounding. The system NEVER presents a philosophical position as definitively "proven."

4. **Human-in-the-Loop with Bidirectional Steering**: The user can steer agents, but agents can also explicitly request human judgment when facing incommensurable traditions, underdetermined ethical dilemmas, or phenomenological descriptions requiring lived-experience validation.

## 3. System Architecture

### 3.1 Agent Hierarchy

```
User
↓ (Chat Interface + Steering Commands)
Project Coordinator Agent (Sole User-Facing Interface)
↓ (Delegates via Message Protocol)
Workstream Coordinators (One per active goal)
├── Literature Search Coordinator
├── Concept Analysis Coordinator
├── Cross-Traditional Comparison Coordinator
├── Argumentation Coordinator
├── Critical Review Coordinator
├── Phenomenological Description Coordinator
├── Ethical Analysis Coordinator
└── Synthesis Coordinator
    ↓ (Delegates to Specialized Sub-Agents)
    Specialized Sub-Agents
    ├── Deep Think / Reasoning Agent
    ├── Literature Query Agent
    ├── PDF RAG Agent (local)
    ├── Formal Logic Agent
    └── Coding Agent (for simulations, probability, formal models)
```

**Communication Protocol**:
- All agents communicate via a standardized JSON message protocol
- Messages include: `sender_id`, `recipient_id`, `message_type` (status_update, delegation_request, steering_command, help_request, review_request), `payload`, `timestamp`, `epistemic_status`
- The shared file system is the single source of truth for documents, code, and data

### 3.2 Workspace Architecture

Each project has a persistent workspace:

```
projects/<project_id>/
├── metadata.json                 # Project state, goals, configuration
├── living_document.md            # Working paper with YAML frontmatter
├── dialectical_history.jsonl     # Derived export: complete argument/refutation history (SQLite is authoritative)
├── hypotheses.jsonl              # Derived export: all hypotheses (SQLite is authoritative)
├── conceptual_genealogy/         # Concept maps, distinction matrices, tradition trees
├── artifacts/                    # Uploaded PDFs, generated LaTeX, code, simulations
├── vector_db/                    # Chroma/LanceDB collection for RAG
├── workstreams/                  # Per-workstream reports, incremental updates, reviews
│   ├── <ws_id>_report.md
│   ├── <ws_id>_incremental.log
│   └── <ws_id>_review_rounds.json
├── margin_notes/                 # Standalone margin annotations linked to living_document
├── uncertainty_registry.json     # Derived export: confidence scores and review status (SQLite is authoritative)
└── logs/                         # Agent decision logs, tool call logs
```

### 3.3 State Schema (Pydantic)

```python
class ProjectState(BaseModel):
    project_id: str                          # UUID
    title: str
    original_question: str
    status: ProjectStatus                    # Project lifecycle state
    refined_goals: list[GoalStatement]
    workstreams: dict[str, WorkstreamState]
    living_document: str                     # Markdown with embedded annotations
    dialectical_history: list[DialecticalMove]
    hypotheses: list[HypothesisRecord]
    conceptual_genealogy: dict[str, ConceptNode]
    uncertainty_registry: list[UncertaintyRecord]
    artifacts: list[Artifact]
    metadata: ProjectMetadata
    external_layer_config: Optional[ExternalConfig]

class WorkstreamState(BaseModel):
    workstream_id: str
    type: WorkstreamType                     # Enum: see Section 5
    status: WorkstreamStatus                 # Enum: pending, running, paused, completed, failed, stalled
    goal_statement: GoalStatement
    assigned_coordinator: str
    assigned_sub_agents: list[str]
    results: str                             # Compiled report
    incremental_updates: list[ProgressUpdate]
    review_rounds: list[ReviewRound]
    uncertainty_flags: list[UncertaintyFlag]
    failed_explorations: list[FailedExploration]

class HypothesisRecord(BaseModel):
    statement: str
    strength: HypothesisStrength             # strong, moderate, weak, refuted, underdetermined
    origin: Origin                           # user, ai, joint, cross_tradition_synthesis
    supporting_evidence: list[Reference]
    counter_arguments: list[CounterArgument]
    dialectical_children: list[str]          # Hypotheses that refined/replaced this one
    status: HypothesisStatus                 # active, abandoned, refined, refuted
    epistemic_tradition: Optional[str]       # e.g., "analytic", "phenomenological", "confucian"

class UncertaintyRecord(BaseModel):
    claim_id: str
    claim_text: str
    confidence_score: float                  # 0.0–1.0
    counter_argument_strength: float         # 0.0–1.0
    tradition_validity: dict[str, float]     # {tradition: validity_score}
    review_status: ReviewStatus              # unreviewed, under_review, contested, accepted_with_reservations, rejected
    stalled_sections: list[str]              # Links to document sections where review deadlocked
    last_updated: str                        # ISO timestamp
```

### 3.4 Implementation Architecture Principles (Mandatory)

The AI Co-Philosopher **must** be implemented following **Pragmatic Clean Architecture** (Ports & Adapters / Hexagonal Architecture) with strong emphasis on type safety and maintainability.

#### Core Rules

- **Language**: Python 3.11+ (targeting 3.12+ in future)
- **Architecture Style**: Ports & Adapters (Clean Architecture)
  - `domain/`: Pure business logic—Entities, Value Objects, and domain services. Must have zero external dependencies.
  - `application/`: Orchestration and use cases—LangGraph state graphs, Project Coordinator, Workstream Coordinators, and Synthesis workflows. Depends only on `domain/` and `ports/`.
  - `ports/`: Abstract interfaces—`LLMPort`, `StoragePort`, `ReviewerPort`, `DialecticalHistoryPort`, etc. Must import no third-party libraries.
  - `infrastructure/adapters/`: Concrete implementations—`GeminiAdapter`, `FileSystemAdapter`, `ChromaAdapter`, `SqliteAdapter`, etc. Implement the interfaces declared in `ports/`.
  - `presentation/`: CLI / Chat interface—Rich-based terminal UI, command parsing, and human-in-the-loop breakpoints. Depends only on `application/` and `ports/`.
- **Type Safety**:
  - All public APIs, ports, and data classes **must** be strictly defined with **Pydantic v2** (see §3.3 and `data-model.md`).
  - Static type checking enforced via `typing.Protocol` + `mypy --strict`.
  - Runtime validation via Pydantic `model_validate` / `TypeAdapter` on every external input and deserialization boundary.
- **Dependency Direction**:
  - `infrastructure/adapters` → `ports` → `application` → `domain` (dependencies point inward only; outer layers depend on inner layers, never the reverse).
  - All external libraries and I/O concerns (LLM SDKs, vector databases, filesystem, search APIs) **must** be wrapped by adapters behind the interfaces declared in `ports/`.
  - The orchestration framework (LangGraph) may be used directly in the `application/` layer as it realises the orchestration use-case itself; it does not require an adapter, but all state schemas it manipulates must be Pydantic models defined in `domain/`.
- **Additional Mandates**:
  - No circular imports (enforced by `ruff` + `pyright`).
  - All state changes **must** be immutable or follow an explicit command pattern; in-place mutation of domain objects is prohibited.
  - Uncertainty Registry, Dialectical History, and Living Document **must** be treated as first-class domain entities. Agents and coordinators are forbidden from direct filesystem or database manipulation; all persistence flows through the `StoragePort`.

These principles are mandatory to faithfully realise the **stateful / uncertainty-aware / auditable workspace** demanded by the AI Co-Mathematician paper, adapted for philosophical research.

### 3.5 Cost-Aware LLM Routing & Tiered Execution (Mandatory)

For literature-search and exploration workstreams, **cost-optimised multi-stage execution is mandatory**.

#### 3.5.1 Design Principles
- **Exploration / Collection tasks** (paper search, abstract retrieval, citation graph construction, initial relevance filtering) **must** run on **low-cost models** (e.g., Gemini 2.5 Flash, DeepSeek R1, Moonshot cheap tier).
- **Analysis / Synthesis tasks** (deep critical review, conceptual genealogy analysis, Cross-Traditional Comparison, Uncertainty evaluation, integration into the Working Paper) **must** use the **high-quality model (Kimi K2.6)** exclusively.
- Each task is automatically routed by an **LLM Router** that selects the appropriate model for the task tier.
- When cumulative cost exceeds a configurable threshold, the Workstream Coordinator **must** surface a confirmation request to the user via progressive disclosure.

#### 3.5.2 Implementation Requirements (Ports & Adapters)
- Add `LLMProfile` enum (`CHEAP`, `MEDIUM`, `EXPENSIVE`) and `LLMRoutingConfig` to `ports/llm_port.py`.
- Implement actual routing and cost estimation logic in `infrastructure/adapters/llm_router_adapter.py`.
- The Literature Review Sub-Agent (and related Phenomenological / Cross-Traditional Agents) **must** operate as a **staged pipeline**:
  1. **Stage 1 (CHEAP)**: Search, Abstract retrieval, Citation collection.
  2. **Stage 2 (EXPENSIVE)**: Deep review and synthesis via Kimi K2.6 (only when needed).
- Cost logs are recorded alongside the `uncertainty_registry` (enabling future budget-cap configuration).

This mechanism ensures the **AI Co-Philosopher dramatically reduces routine exploration costs** while reserving Kimi K2.6's philosophical depth for the core analytical work that demands it.

### 3.6 Domain-Aware Query Strategy (Mandatory)

Literature Review Workstream and Cross-Traditional Comparison Agent **must** use a philosophically sophisticated query strategy, avoiding naive keyword matching.

#### 3.6.1 Core Philosophical Domains (First-Class Treatment)

The following domains are **Core Domains** with explicit priority and expansion:

- **Philosophy of Mathematics** (foundations, structuralism, formalism, intuitionism, mathematical realism/anti-realism)
- **Logic** (model theory, proof theory, non-classical logics, categorial logic, modal logic)
- **Pragmatism** (Peirce, James, Dewey, Rorty, neopragmatism, pragmatic naturalism)
- **Philosophy of Science** (scientific realism/anti-realism, epistemology of science, underdetermination, theory change, STS)
- **Philosophy of Technology** (post-phenomenology, technological mediation, STS, critical theory of technology, AI ethics)
- **Model Theory** (applications to philosophy, philosophical logic, structuralism, category-theoretic foundations, model-theoretic semantics)

These domains receive **weighted priority during Query Expansion**, automatically including relevant subtopics (e.g., structuralism, formalism, causal inference, computational philosophy, technological mediation).

#### 3.6.2 Query Strategy Requirements

1. **Semantic Query Expansion**
   - Naive keyword matching is **prohibited**; LLM-based (Cheap-tier permitted) **semantic expansion** is mandatory.
   - Automatically detect Core Domains from user queries and generate philosophically optimised expanded queries.
   - Example: "moving sofa problem" → `philosophy of mathematics + computational geometry + intuitionism + continuous mathematics`

2. **Tradition-Aware Query**
   - Recognise sub-traditions within Core Domains (Logicism, Intuitionism, Formalism, Structuralism, Category-theoretic foundations) alongside broad traditions (Analytic, Continental, Pragmatist, Eastern).

3. **Staged Query Pipeline** (tied to Cost-Aware §3.5)
   - **Stage 1 (CHEAP)**: Broad exploration query generation + Abstract retrieval.
   - **Stage 2 (EXPENSIVE: Kimi K2.6)**: Deep critical review and concept mapping **only** for papers highly relevant to Core Domains.

#### 3.6.3 Implementation Requirements (Ports & Adapters)

- Define `PhilosophicalQueryStrategy` in `ports/query_port.py`.
- `infrastructure/adapters/search_adapter.py` **must** fully conform to this strategy (the naive keyword dict from PR #11 is to be replaced incrementally).
- Core Domains are defined in `domain/core_domains.py` (or constitution) and shared across all Agents.

This mechanism ensures the **AI Co-Philosopher accurately understands the user's specialist philosophical interests, producing high-quality philosophical literature discovery without relying on naive search heuristics**.

## 4. Agent Specifications

### 4.1 Project Coordinator Agent

**Role**: The sole user-facing agent. Acts as dialectical partner, project manager, and steering interface.

**Behavior**:
- MUST engage in Socratic clarification dialogue before launching workstreams. The dialogue continues until:
  - The user's philosophical question is disambiguated (analytic vs continental vs Eastern framing identified or explicitly left open)
  - Key concepts are preliminary scoped
  - The user's methodological preferences (if any) are understood
  - At least one concrete, achievable research goal is formulated
- MUST propose workstreams based on refined goals and MUST obtain explicit user approval before creating them.
- MUST provide high-level progress summaries with epistemic status overview (e.g., "2 workstreams completed, 1 stalled awaiting your input on ethical framework preference").
- MUST accept steering commands:
  - `pause workstream <id>` / `resume workstream <id>`
  - `abandon hypothesis <id>`
  - `deepen analysis on <concept>`
  - `compare traditions on <topic>`
  - `request phenomenological description of <phenomenon>`
  - `redirect workstream <id> to <new_goal>`
- MUST flag roadblocks and request human assistance when:
  - Agents reach incommensurable positions across traditions
  - Ethical dilemma analysis requires the user's normative commitments
  - Phenomenological description requires first-person validation
  - Review process enters non-termination ("death spiral")
- MUST implement progressive disclosure: every response starts with a concise summary, followed by `[Details]` and `[Suggestions]` expandable sections.

### 4.2 Literature Search Agent

**Role**: Discovers, retrieves, and synthesizes philosophical literature across traditions and languages.

**Capabilities**:
- MUST query: PhilPapers API, Stanford Encyclopedia of Philosophy (SEP), Internet Encyclopedia of Philosophy (IEP), arXiv philosophy (cs.AI, humanities), Semantic Scholar, and tradition-specific databases (e.g., Daoist texts corpus, Buddhist Digital Resource Center if available).
- MUST support cross-traditional literature bridging: when the user inquires about a concept (e.g., "mind"), the agent MUST search for analogues across traditions (e.g., 心 xīn, citta, nous, Geist) and explicitly note where direct translation is contested.
- MUST obtain explicit user consent before using external search services per project/request.
- MUST transmit only minimum necessary search data to external services; MUST NOT transmit project content, living-document text, or uploaded PDF contents without explicit consent.
- MUST support user-uploaded PDFs for local RAG; PDF ingestion and retrieval MUST be performed locally by default.

**Output**: Structured bibliography with:
- Title, authors, year, abstract snippet, relevance score, BibTeX entry
- Tradition tag (e.g., `analytic_philosophy`, `phenomenology`, `buddhist_philosophy`, `confucian_ethics`)
- Conceptual bridge notes (e.g., "Discusses 'qualia'—compare with Buddhist vinnana (consciousness) concepts")
- Confidence score for relevance and for cross-traditional analogy validity

### 4.3 Concept Analysis Agent

**Role**: Performs precise conceptual clarification, distinction mapping, thought-experiment generation, and conceptual genealogy.

**Capabilities**:
- MUST perform:
  - Necessary vs sufficient condition analysis
  - Distinction mapping (e.g., de re vs de dicto, a priori vs a posteriori, 理 li vs 氣 qi)
  - Thought experiment generation and evaluation (e.g., trolley problems, brain-in-a-vat, Zhuangzi's butterfly dream)
  - Conceptual genealogy (historical development of a concept across texts and traditions)
  - Cross-traditional concept bridging (identifying functional analogues and incommensurabilities)
- MUST flag when concepts are fundamentally contested or incommensurable across traditions.
- MUST generate confidence scores for conceptual analyses and explicitly state methodological assumptions.

**Output**: Structured concept analysis including:
- Concept map (graph of related concepts, distinctions, oppositions)
- Distinction matrix (comparing definitions across traditions)
- Thought experiment catalog with epistemic status
- Conceptual genealogy tree

### 4.4 Cross-Traditional Comparison Agent

**Role**: NEW specialized agent for the Co-Philosopher. Compares philosophical positions across traditions, identifies bridge concepts and incommensurabilities.

**Capabilities**:
- MUST identify functional analogues of concepts across traditions (e.g., Aristotelian eudaimonia → Confucian junzi ideal → Buddhist bodhisattva path).
- MUST explicitly flag incommensurabilities where no satisfactory bridge exists.
- MUST evaluate arguments within their native methodological frameworks before cross-comparison.
- MUST avoid "colonizing" one tradition with another's categories (e.g., forcing Buddhist anatta into Cartesian substance dualism).

**Output**: Cross-traditional comparison report with:
- Tradition profiles (key assumptions, methodological norms, evaluative criteria)
- Bridge concept map (where valid)
- Incommensurability register (where comparison breaks down)
- Synthesis proposals (if user requests) with explicit methodology

### 4.5 Argumentation Agent

**Role**: Constructs, reconstructs, and evaluates arguments in standard and non-standard forms.

**Capabilities**:
- MUST construct arguments in standard form (premises + conclusion) with explicit inference rules.
- MUST generate multiple competing positions (e.g., compatibilist vs incompatibilist free will; consequentialist vs deontological ethics).
- MUST identify implicit assumptions, suppressed premises, and argumentative circularity.
- MUST support both formal logical arguments (syllogistic, propositional, predicate) and informal argument schemes (analogical, abductive, phenomenological).
- MUST evaluate arguments within their tradition's accepted norms (e.g., pramana standards in Indian philosophy, phenomenological reduction in Husserlian tradition).

**Output**: Formal argument list with:
- Premises, conclusion, inference rule, validity assessment
- Implicit assumptions list
- Competitor argument summaries
- Tradition-specific validity assessment

### 4.6 Critical Review Agent

**Role**: Detects logical fallacies, evaluates validity, soundness, and philosophical plausibility; generates counter-arguments.

**Capabilities**:
- MUST detect logical fallacies (formal and informal) with explanation and severity rating.
- MUST evaluate validity, soundness, and philosophical plausibility separately.
- MUST generate counter-arguments and objections from multiple traditions and methodological frameworks.
- MUST perform adversarial review: actively attempt to refute arguments before accepting them.
- MUST flag "reviewer-pleasing bias" (false consensus) risk when arguments appear to satisfy review constraints without genuine rigor.

**Output**: Critique report with:
- Fallacy inventory (if any) with severity and correction suggestions
- Validity/soundness/plausibility assessments
- Counter-argument tree
- Adversarial stress-test results
- Review confidence score and uncertainty flags

### 4.7 Phenomenological Description Agent

**Role**: NEW specialized agent. Generates and evaluates phenomenological descriptions of lived experience.

**Capabilities**:
- MUST generate phenomenological descriptions using methodological frameworks (e.g., Husserlian epoché, Merleau-Pontyan embodied perception, Buddhist vipassana-based description).
- MUST distinguish between first-person phenomenological claims and third-person scientific descriptions.
- MUST flag when phenomenological claims require first-person validation from the user or from reported experiences in literature.
- MUST support comparison of phenomenological descriptions across traditions (e.g., Husserl's noema vs Buddhist nimitta).

**Output**: Phenomenological description with:
- Methodological framework explicit
- Epoché bracketing declarations
- Confidence score (higher for structural features, lower for subjective quality claims)
- Cross-traditional phenomenological comparison (if applicable)
- User validation request (if first-person verification needed)

### 4.8 Ethical Analysis Agent

**Role**: NEW specialized agent. Analyzes ethical dilemmas, normative frameworks, and moral arguments.

**Capabilities**:
- MUST identify the ethical framework(s) implicit in a dilemma or argument (consequentialist, deontological, virtue ethical, care ethical, Buddhist ethics, Confucian ethics, etc.).
- MUST generate analyses from multiple normative frameworks.
- MUST flag underdetermined dilemmas where no single framework yields a clear resolution.
- MUST explicitly request the user's normative commitments when the analysis requires them.
- MUST distinguish between descriptive ethics, normative ethics, and meta-ethical analysis.

**Output**: Ethical analysis report with:
- Framework identification and application
- Multi-framework analysis
- Underdetermination flags
- User normative commitment requests (if needed)
- Confidence scores for each framework's applicability

### 4.9 Synthesis Agent

**Role**: Merges outputs from multiple workstreams into coherent sections of the living document.

**Capabilities**:
- MUST merge outputs while maintaining consistent philosophical voice and citation style.
- MUST preserve epistemic status annotations (confidence, origin, review status) in synthesized content.
- MUST generate margin notes linking claims to workstream reports, literature sources, and dialectical history.
- MUST flag conflicts between workstream outputs for human resolution.
- MUST support multiple output formats: Markdown (default), LaTeX, HTML.

**Output**: Updated living document sections with:
- Synthesized prose
- Embedded margin annotations
- Conflict flags (if workstreams disagree)
- Synthesis confidence score

### 4.10 External Agent Bridge

**Role**: Translates internal workstream requests into calls to external orchestration layers (Hermes Agent, OpenCode Go, etc.).

**Requirements**:
- MUST support seamless fallback to internal LangGraph execution if the external layer is unavailable or returns an error.
- MUST use standardized JSON protocol.
- MUST log all external interactions for auditability.
- MUST NOT transmit user data to external layers without explicit consent.

## 5. User Interaction Specification

### 5.1 Primary Interface

Chat-based interface (terminal/Rich for MVP; Gradio/Streamlit for future).

### 5.2 Steering Commands

- `new project <title>` — Start a new research project
- `refine goal` — Enter/continue dialectical clarification dialogue
- `start workstream <type>` — Propose and launch a workstream (requires coordinator approval flow)
- `pause/resume <id>` — Control workstream execution
- `export [latex|pdf|html|obsidian]` — Export living document
- `show hypotheses` — Display hypothesis history with epistemic status
- `show dead ends` — Display failed explorations and refuted arguments
- `add note` — Add user note to workspace
- `steer <workstream_id> <instruction>` — Direct steering of a specific workstream
- `compare traditions <topic>` — Request cross-traditional comparison
- `phenomenological description <phenomenon>` — Request phenomenological analysis
- `ethical analysis <dilemma>` — Request ethical framework analysis
- `request help` — Explicitly request human assistance flag from coordinator

### 5.3 Progressive Disclosure Format

Every coordinator response MUST follow:

```markdown
**Summary**
[Concise overview of status, new results, or requests for input]

**Epistemic Status Overview**
[Active hypotheses: N | Refuted: N | Under review: N | Stalled: N]

**Active Workstreams**
[WS-001: Literature Search — running | WS-002: Concept Analysis — completed]

[Details]
[Detailed findings, argument excerpts, literature summaries]

[Suggestions]
[Proposed next actions: "Start Argumentation workstream?", "Deepen phenomenological description?"]
```

## 6. Living Document Specification

### 6.1 Format

Markdown with YAML frontmatter, designed to be native to philosophical workflows.

### 6.2 Structure

```markdown
---
title: "[Project Title]"
project_id: "[UUID]"
version: "[Document Version]"
last_updated: "[ISO Date]"
epistemic_status: "[Draft | Under Review | Final]"
traditions_referenced: ["analytic", "phenomenology", "buddhist", ...]
---

# Introduction
[Research question, methodological framing, scope]

# Key Concepts
[Conceptual analyses with embedded genealogy]

# Cross-Traditional Perspectives
[Comparison across philosophical traditions]

# Arguments
[Reconstructed arguments with standard form annotations]

# Objections and Replies
[Counter-arguments and responses, including refuted objections]

# Phenomenological Descriptions
[First-person structural descriptions where applicable]

# Ethical Analysis
[Multi-framework normative assessment]

# Conclusion
[Synthesized position, open questions, future directions]

# References
[BibTeX-compatible citations with tradition tags]

# Dialectical Appendix
[History of abandoned arguments, refuted hypotheses, conceptual revisions]
```

### 6.3 Margin Annotations

Every non-trivial claim MUST have an inline annotation:

```markdown
The concept of qualia appears irreducible to physical descriptions <!--
Source: Concept Analysis WS-003 | Confidence: 0.72 | Origin: AI-assisted |
Counter-argument strength: 0.65 | Tradition: analytic_philosophy |
Review status: contested | Phenomenological grounding: partial -->
```

Annotations MUST include:
- `Source`: Workstream ID or user note
- `Confidence`: 0.0–1.0
- `Origin`: user, ai, joint, cross_tradition_synthesis
- `Counter-argument strength`: 0.0–1.0
- `Tradition`: primary methodological tradition
- `Review status`: unreviewed, under_review, contested, accepted_with_reservations, rejected
- `Phenomenological grounding`: none, partial, full (if applicable)

### 6.4 Review Process for Workstream Reports

Before a workstream report is finalized, it MUST undergo an iterative review process:
- Reviewer agents (at least 2) scrutinize the report for logical correctness, conceptual clarity, citation accuracy, and tradition-appropriate methodology.
- Reviewer agents persist between rounds, creating an iterative refinement process.
- Review concludes only when all reviewers formally approve OR the workstream coordinator escalates non-termination to the Project Coordinator.
- If escalation occurs, the workstream is marked `stalled` with a clear user-facing alert.

## 7. Uncertainty Management & Failed Exploration Tracking

### 7.1 Uncertainty Lifecycle

The system treats uncertainty as a core variable to be orchestrated, not an error state:

1. **Track**: Maintain a detailed version history of claims; monitor how claims evolve or are called into question.
2. **Manage**: Trade compute for validation (continuous reviews, cross-traditional checks, formal verification where applicable, phenomenological consistency checks).
3. **Communicate**: Use inline highlighting and margin notes to draw user attention to stalled sections, contested claims, or underdetermined dilemmas.

### 7.2 Failed Exploration Registry

When a workstream concludes in failure (refuted hypothesis, unsolvable contradiction, non-terminating review), the system MUST:
- Preserve the full workstream report with failure reason
- Log the failed exploration in SQLite `hypotheses` table (and export to `hypotheses.jsonl`) with status `refuted` or `abandoned`
- Generate a "lessons learned" summary accessible to future workstreams
- Surface the failure to the user via the Project Coordinator with context on why the failure is informative

## 8. Tool Integration

The system MUST provide tools for:
- **Web/Philosophical search**: PhilPapers, SEP, IEP, arXiv, Semantic Scholar, tradition-specific databases
- **PDF text extraction and chunking**: Local RAG over uploaded papers
- **Code execution**: Formal logic (Prolog, Lean interface), probability simulations, decision-theoretic calculations, agent-based ethical dilemma simulations
- **LaTeX/PDF generation**: Export living document to publication-ready formats
- **Argument map visualization**: Generate graph representations of argument structures (post-MVP)

All tool calls SHALL be logged in the project workspace with caller agent, timestamp, input/output hashes, and epistemic status of results.

## 9. Non-Functional Specifications

- **Core independence**: The entire system MUST run completely without Hermes Agent, OpenCode Go, or any external orchestration layer.
- **External layer integration** is strictly optional and MUST NOT break core functionality.
- **Privacy**: All user data and research projects MUST remain private and stored locally by default. Explicit consent required for any external data transmission.
- **Philosophical accuracy over speed**: The system MUST prioritize nuance, intellectual honesty, and methodological appropriateness over response speed.
- **Extensibility**: New agent roles (e.g., Aesthetic Analysis Agent, Political Philosophy Agent) and tools MUST be addable without major refactoring via a `ToolRegistry` and `AgentRegistry`.
- **Self-hostability**: The system MUST be built using open-source components and be fully self-hostable.
- **Auditability**: All agent decisions, tool uses, review rounds, and uncertainty state changes MUST be logged.

## 10. MVP Scope (First Iteration) with Acceptance Criteria

### 10.1 MVP Components

- **Project Coordinator Agent** with dialectical clarification dialogue
- **Literature Search Agent** (PhilPapers, SEP, arXiv, Semantic Scholar)
- **Concept Analysis Agent** (basic conceptual clarification, distinction mapping, thought experiments)
- **Argumentation Agent** (standard form reconstruction, competing positions)
- **Critical Review Agent** (fallacy detection, basic counter-arguments)
- **Synthesis Agent** (living document generation with margin annotations)
- **Cross-Traditional Comparison Agent** (basic tradition tagging and bridge concept identification)
- Persistent Markdown living document with YAML frontmatter and margin annotations
- Basic workstream management (create, pause, resume, view status, review process)
- Local file-based workspace with SQLite metadata
- Full operation without any external layers
- Support for Claude / Gemini / Ollama backends

### 10.2 Explicit Acceptance Criteria

| ID | Criterion | Measurement | Acceptance Threshold |
|---|---|---|---|
| AC-001 | A user can start a new project with a vague philosophical question and, through dialogue, arrive at a refined research goal with at least one scoped sub-question. | Time to approved goal; number of clarification turns | ≤ 5 turns; ≤ 10 minutes |
| AC-002 | The Literature Search Agent returns relevant philosophical papers with tradition tags and cross-traditional bridge notes. | Precision@5 on known queries | ≥ 70% relevance; ≥ 1 bridge note per cross-traditional query |
| AC-003 | The Concept Analysis Agent produces a structured concept map with distinction matrix for a given philosophical concept. | Human expert evaluation of conceptual accuracy | ≥ 80% accuracy on analytic concepts; ≥ 60% accuracy on cross-traditional concepts |
| AC-004 | The Argumentation Agent reconstructs at least 2 competing positions for a philosophical question, each in standard form. | Completeness of position coverage | ≥ 2 distinct traditions or methodological frameworks represented |
| AC-005 | The Critical Review Agent identifies at least 1 valid counter-argument or implicit assumption for each reconstructed argument. | Counter-argument validity (human review) | ≥ 1 substantive counter-argument per argument; ≥ 70% validity rate |
| AC-006 | The Synthesis Agent generates a living document section with embedded margin annotations including confidence scores and review status. | Annotation completeness | 100% of non-trivial claims annotated; all required fields present |
| AC-007 | The user can pause, resume, and steer any workstream via chat commands, with changes reflected in the living document within 30 seconds. | Command latency | ≤ 30 seconds for status reflection |
| AC-008 | The system preserves all hypotheses including refuted/abandoned ones, accessible via `show dead ends` command. | Hypothesis history completeness | 100% retention; user-accessible within 5 seconds |
| AC-009 | The entire MVP runs without any external orchestration layer (Hermes, OpenCode Go) and without internet access after initial setup. | Offline functionality test | All core features operational; only external search requires connectivity |
| AC-010 | A user can complete a philosophical literature review and draft a 2000-word position paper using only the Co-Philosopher interface. | Time-to-draft vs baseline (user working alone) | ≥ 30% faster than self-reported baseline; user satisfaction ≥ 4/5 |

### 10.3 MVP Exclusions

- Phenomenological Description Agent (full version)
- Ethical Analysis Agent (full multi-framework version)
- LaTeX export (Markdown only for MVP)
- Formal logic prover integration (post-MVP)
- Advanced RAG with vector database (basic file-based retrieval for MVP)
- Web UI (terminal/Rich interface only)
- Multi-project management

## 11. Future Phases (Post-MVP)

- **Phase 2**: Full Phenomenological Description Agent, Ethical Analysis Agent, LaTeX/PDF export, vector database RAG
- **Phase 3**: Formal logic integration (Lean/Prolog), agent-based ethical dilemma simulations, argument map visualization
- **Phase 4**: Web UI (Gradio/Streamlit), full asynchronous workstream execution, multi-project management
- **Phase 5**: Advanced cross-traditional RAG over personal philosophy library, Obsidian vault export, plugin system for domain-specific areas (Philosophy of Mind, Ethics, Metaphysics, etc.)
- **Phase 6**: Full Hermes Agent and OpenCode Go adapters, cross-project knowledge sharing, community-contributed tradition modules

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Reviewer-pleasing bias (false consensus) | High | Multiple reviewer agents with divergent methodological frameworks; explicit uncertainty flags; human escalation on deadlock |
| Intractable disagreements / non-termination | High | Review round limits; automatic escalation to Project Coordinator; "death spiral" detection heuristic |
| Semantic overconfidence (well-formatted but shallow output) | High | Mandatory confidence scores; adversarial review; explicit "underdetermined" status; user final approval gate |
| Cross-traditional colonization (forcing one tradition's categories onto another) | High | Cross-Traditional Comparison Agent with incommensurability flagging; tradition-specific review norms; user validation for bridge concepts |
| Signal-to-noise in philosophical literature | Medium | Margin annotations with provenance; review process; user-controlled synthesis approval |
| System autonomy vs user controllability | Medium | Explicit steering commands; bidirectional help requests; configurable autonomy levels |

---

**Version**: 2.0.0 | **Last Updated**: 2026-05-13 | **Next Review**: Upon MVP completion
