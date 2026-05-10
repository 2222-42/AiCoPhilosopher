# AI Co-Philosopher - design.md

## 1. High-Level Architecture

The system follows a **hierarchical multi-agent architecture** based on LangGraph (or equivalent stateful orchestration framework).

```
User
↓ (Chat Interface)
Project Coordinator Agent (Supervisor)
↓
Workstream Orchestrator
├── Literature Search Workstream
├── Concept Analysis Workstream
├── Argumentation Workstream
├── Critical Review Workstream
└── Synthesis Workstream
Shared Persistent Workspace (File System + Vector DB + SQLite)
```

- **Project Coordinator** acts as the brain and user proxy.
- Each **Workstream** is a sub-graph that can run asynchronously.
- All agents share a common **Workspace** for state and artifacts.

## 2. Technology Stack (Recommended)

- **Core Framework**: LangGraph (Python) — stateful graphs and multi-agent orchestration
- **LLM Backends** (pluggable):
  - Primary: Claude 3.5/4 (Sonnet/Opus) — best for philosophical depth
  - Secondary: Gemini 2.5 Pro, Groq (Llama-4), Ollama (local)
- **Vector Database**: Chroma or LanceDB (for RAG over papers and notes)
- **Persistence**:
  - SQLite (project metadata + state)
  - Local file system (living document, artifacts, hypothesis logs)
- **Frontend Options**:
  - Terminal / Rich (for MVP)
  - Gradio or Streamlit (web UI)
- **Other Libraries**:
  - `langchain`, `pydantic`, `arxiv`, `PyMuPDF`, `bibtexparser`, `pylatex`

## 3. Core Components Design

### 3.1 Shared Workspace
- Directory structure per project:
```
projects/<project_id>/
├── metadata.json
├── living_document.md
├── hypotheses.jsonl
├── artifacts/
├── vector_db/          # Chroma collection
├── workstreams/
└── logs/
```
- All agents access workspace via a `WorkspaceManager` class with thread-safe / async-safe methods.

### 3.2 State Schema (Pydantic)
```python
class ProjectState(TypedDict):
  project_id: str
  messages: list[Message]
  living_document: str
  workstreams: dict[str, WorkstreamState]
  hypotheses: list[Hypothesis]
  artifacts: list[Artifact]
  current_goal: str
  context_summary: str
```

### 3.3 Agent Design Pattern

Each agent follows the ReAct + Structured Output pattern:

Planner → Tool Use → Reflection → Output
Uses Pydantic models for all outputs (guaranteed structure)


## 4. Agent Detailed Design

| Agent                  | Role                                      | Key Tools                              | Output Format                    |
|------------------------|-------------------------------------------|----------------------------------------|----------------------------------|
| Project Coordinator    | User dialogue & orchestration             | None (delegates)                       | ProgressSummary + NextAction     |
| Literature Search      | Find & summarize sources                  | PhilPapers, Semantic Scholar, PDF RAG  | StructuredPaperList              |
| Concept Analysis       | Clarify concepts, thought experiments     | Pure reasoning                         | ConceptMap + ThoughtExperiments  |
| Argumentation          | Build arguments                           | Logic checker tool                     | FormalArgumentList               |
| Critical Review        | Critique & find weaknesses                | Fallacy detector                       | CritiqueReport                   |
| Synthesis              | Merge into living document                | Document writer                        | UpdatedDocumentSection           |

## 5. Prompt Engineering Strategy

- **System Prompt Template** for every agent includes:
  - Role definition
  - Philosophical principles (charity, precision, intellectual honesty)
  - Output format enforcement (JSON mode + Pydantic)
  - Reference to current project context

- **Chain-of-Thought + Self-Critique** is mandatory for all reasoning agents.
- **Few-shot examples** are used for philosophical argument structure and Socratic questioning.

## 6. Data Flow Example (Typical Research Cycle)

1. User inputs vague question → Project Coordinator
2. Clarification dialogue (3–5 turns)
3. Coordinator proposes 2–3 workstreams → User approval
4. Workstreams run in parallel (async)
5. Results flow back → Synthesis Agent updates `living_document.md`
6. Coordinator presents summary with annotations
7. User steers or adds notes → loop continues

## 7. Progressive Disclosure & User Control

- Every Coordinator response follows this structure:
  ```markdown
  **Summary**
  ...

  **Active Workstreams**
  ...

  [Details] → expandable section
  [Suggestions] → next actions
  ```
- User can issue commands at any time:
  - `pause 3`
  - `deepen concept X`
  - `abandon hypothesis Y`
  - `export latex`
 
## 8. Extensibility Points

- New agents can be added by registering a new Workstream type and corresponding LangGraph subgraph.
- Custom tools can be injected via a `ToolRegistry` class.
- Prompt templates are stored in a dedicated `prompts/` directory for easy customization and versioning.
- New output formats (e.g., additional export to PDF, HTML, or Obsidian vault) can be added through the Synthesis Agent.
- The system SHALL support plugin-style extensions for domain-specific philosophical areas (e.g., Philosophy of Mind, Ethics, Philosophy of Science).

## 9. Error Handling & Safety

- All LLM outputs MUST be validated against Pydantic schemas before being accepted.
- Failed tool calls SHALL be retried up to 3 times with exponential backoff, then escalated to the Project Coordinator.
- The system MUST implement philosophical overconfidence mitigation: every major claim or argument generated by any agent SHALL include a confidence score (0.0–1.0) and a brief justification.
- The user SHALL always have final approval on any content that is permanently added to the living document.
- Sensitive user data and entire research projects MUST remain locally stored by default with no automatic external transmission.
- The system SHOULD log all agent decisions and tool uses for auditability and debugging.

## 10. MVP Implementation Plan (Phase 1)

- Core: Project Coordinator Agent + Literature Search Agent + Synthesis Agent
- Persistent file-based workspace (no external database required for MVP)
- Terminal interface using Rich library for clean formatting
- Support for at least two backends: Claude (via Anthropic API) and local Ollama models
- Basic living document management with Markdown and annotation support
- Project creation, save, and load functionality
- Progressive disclosure in Coordinator responses
- Basic workstream management (create, pause, resume, view status)

## 11. Future Phases (Post-MVP)

- Phase 2: Add Concept Analysis, Argumentation, and Critical Review Agents
- Phase 3: Full asynchronous workstream execution + web UI (Gradio/Streamlit)
- Phase 4: Advanced RAG over personal philosophy library + LaTeX export
- Phase 5: Multi-project management and cross-project knowledge sharing

---
