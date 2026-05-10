# AI Co-Philosopher - Specification (spec.md)

## 1. Overview
- This document specifies the detailed behavior, interfaces, data models, and functional flows of the AI Co-Philosopher system based on the requirements.
- The system is a stateful, hierarchical multi-agent application designed for long-running philosophical research collaboration.

## 2. System Architecture
- The system SHALL consist of a central **Project Coordinator Agent** that acts as the sole user-facing interface.
- The Project Coordinator SHALL delegate work to specialized **Workstream Coordinators** and **Specialized Sub-Agents**.
- All agents SHALL communicate via a standardized message protocol (Pydantic models or equivalent structured schema).
- The system SHALL maintain a single **Shared Workspace** per research project, implemented as a persistent directory + database.
- State persistence SHALL support saving/loading entire projects so sessions can be paused and resumed.

## 3. Core Data Models

### 3.1 Project State
- Each project MUST contain:
  - `project_id`: Unique UUID
  - `title`: String (user or AI generated)
  - `original_question`: String
  - `refined_goals`: List of refined goal statements
  - `workstreams`: List of active Workstream objects
  - `living_document`: Markdown content (with version history)
  - `hypothesis_history`: List of Hypothesis records (including failed/abandoned)
  - `artifacts`: List of files (PDFs, notes, generated LaTeX)
  - `metadata`: timestamps, last_updated, owner

### 3.2 Workstream
- Each workstream SHALL have:
  - `workstream_id`
  - `type`: Enum (LiteratureSearch, ConceptAnalysis, Argumentation, CriticalReview, Synthesis, etc.)
  - `status`: Enum (pending, running, paused, completed, failed)
  - `task_description`
  - `assigned_agents`
  - `results`
  - `progress_updates`: List of timestamped updates

### 3.3 Hypothesis Record
- Each hypothesis SHALL record:
  - `statement`
  - `strength`: Enum (strong, moderate, weak, refuted)
  - `origin`: Enum (user, ai, joint)
  - `supporting_evidence`: List of references
  - `counter_arguments`: List of counter points
  - `status`: active / abandoned / refined

## 4. Agent Specifications

### 4.1 Project Coordinator Agent
- Input: User messages (text + optional file uploads)
- Behavior:
  - MUST engage in clarification dialogue until goals are sufficiently refined.
  - MUST propose and get user approval before creating new workstreams.
  - MUST provide high-level progress summaries.
  - MUST accept steering commands ("pause workstream X", "abandon hypothesis Y", "deepen analysis on Z").

### 4.2 Literature Search Agent
- MUST support querying: PhilPapers API, Stanford Encyclopedia of Philosophy (via search/scrape if API unavailable), arXiv philosophy, and Semantic Scholar, but only after the user has explicitly consented to the use of those external services for the current project or request.
- When using external literature-search services, the system MUST transmit only the minimum necessary user-approved search data (e.g., query terms, author names, date ranges, and other bibliographic filters) and MUST NOT send project content, living-document text, notes, hypotheses, or uploaded files/PDF contents unless the user has explicitly approved sending that specific content to a named external service.
- Output: Structured list of papers with title, authors, year, abstract snippet, relevance score, and BibTeX entry.
- MUST support user-uploaded PDFs for RAG, with PDF ingestion and retrieval performed locally by default; uploaded PDFs MUST NOT be sent to external literature-search services unless the user explicitly consents to that transfer.

### 4.3 Concept Analysis Agent
- MUST perform:
  - Conceptual clarification (necessary vs sufficient conditions)
  - Thought experiment generation
  - Distinction mapping (e.g., de re vs de dicto)
- Output: Structured concept map or table.

### 4.4 Argumentation Agent
- MUST construct arguments in standard form (premises + conclusion).
- MUST generate multiple competing positions (e.g., compatibilist vs incompatibilist).
- MUST identify implicit assumptions.

### 4.5 Critical Review Agent
- MUST detect logical fallacies.
- MUST evaluate validity, soundness, and philosophical plausibility.
- MUST generate counter-arguments and objections.

### 4.6 Synthesis Agent
- MUST merge outputs from multiple workstreams into coherent sections of the living document.
- MUST maintain consistent philosophical voice and citation style.

## 5. User Interaction Specification
- Primary interface: Chat-based (terminal, Gradio, or Streamlit).
- Supported commands:
  - `new project <title>`
  - `refine goal`
  - `start workstream <type>`
  - `pause/resume <id>`
  - `export latex`
  - `show hypotheses`
  - `add note`
- Progressive disclosure: Every response MUST start with a concise summary, followed by optional detailed sections marked with `[Details]`.

## 6. Living Document Specification
- Default format: Markdown with YAML frontmatter.
- Structure:
  - Introduction
  - Key Concepts
  - Arguments
  - Objections and Replies
  - Conclusion
  - References (BibTeX compatible)
- Every non-trivial claim MUST have an annotation in the format:
  ```markdown
  <!-- Source: Literature Search #42 | Confidence: 0.85 | Origin: AI-assisted -->
  ```

## 7. Tool Integration

- The system MUST provide tools for:
  - Web/Philosophical search
  - PDF text extraction and chunking
  - Code execution (for formal logic, probability, etc.)
  - LaTeX/PDF generation

All tool calls SHALL be logged in the project workspace.

## 8. Non-Functional Specifications

- Response latency for Coordinator interactions SHOULD be under 8 seconds for simple replies.
- Heavy agent tasks MAY run asynchronously with progress callbacks.
- All LLM calls MUST include system prompts that emphasize philosophical rigor, charity of interpretation, and avoidance of overconfidence.
- Privacy: No project data SHALL be sent to external services without explicit user consent (local models preferred when possible).

## 9. MVP Scope (First Iteration)

- Project Coordinator + Literature Search Agent + Synthesis Agent
- Persistent Markdown living document
- Basic workstream management
- Local file-based workspace
- Support for Claude / Gemini / Ollama backends
