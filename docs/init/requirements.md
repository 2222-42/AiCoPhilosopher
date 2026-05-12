# AI Co-Philosopher - Requirements

## 1. Core Purpose
- The system MUST function as an interactive AI Co-Philosopher that accelerates human philosophical research and thinking.
- The system MUST support open-ended, exploratory, and iterative philosophical inquiry rather than single-turn question answering.
- The system SHOULD emulate the workflow of a human philosophical collaborator (ideation → literature review → concept analysis → argumentation → critique → synthesis → writing).

## 2. Architectural Requirements
- The system MUST use a hierarchical multi-agent architecture with at least one Project Coordinator agent and multiple specialized sub-agents.
- The Project Coordinator MUST serve as the single point of user interaction and orchestrate all sub-agents.
- The system MUST maintain a persistent shared workspace that all agents can read from and write to.
- The system MUST support stateful conversations and long-running research projects that can be resumed across sessions.
- The system SHOULD allow asynchronous execution of heavy tasks while the user continues working.

## 3. Functional Requirements - Agents
- The system MUST include a Literature Search Agent capable of querying PhilPapers, Stanford Encyclopedia of Philosophy, arXiv (philosophy section), and Semantic Scholar.
- The system MUST include a Concept Analysis Agent that performs precise conceptual clarification and thought-experiment generation.
- The system MUST include an Argumentation Agent that constructs formal and informal arguments, identifies premises, and generates counter-arguments.
- The system MUST include a Critical Review Agent that checks logical consistency, identifies fallacies, and evaluates philosophical strength of arguments.
- The system MUST include a Synthesis Agent that integrates findings into coherent philosophical drafts.
- All agents SHOULD operate with clearly defined roles and communicate through structured messages.

## 4. User Interaction Requirements
- The user MUST be able to start a new research project with an ambiguous or partially-formed philosophical question.
- The Project Coordinator MUST engage in iterative dialogue to refine the user's intent before launching sub-tasks.
- The user MUST be able to intervene, steer, pause, or redirect any ongoing workstream at any time.
- The system SHOULD implement progressive disclosure: high-level summaries are shown first, with details available on user request.

## 5. Output and Documentation Requirements
- The system MUST maintain a living working document (Markdown by default, LaTeX export supported) that evolves throughout the project.
- Every major claim or argument in the working document MUST include margin notes or annotations indicating source, confidence, and origin (user vs AI).
- The system MUST preserve a complete history of hypotheses, failed paths, and abandoned lines of thought for future reference.
- The final output SHOULD be suitable for direct use in academic papers or personal notes.

## 6. Knowledge and Tool Integration
- The system MUST have access to up-to-date philosophical literature via APIs and search tools.
- The system SHOULD support retrieval-augmented generation (RAG) over user-uploaded papers and personal notes.
- The system MUST be able to call external tools (code execution for formal logic, web search, PDF parsing).

## 7. Non-Functional Requirements
- The system MUST prioritize philosophical accuracy, nuance, and intellectual honesty over speed.
- The system MUST be fully self-contained and operable without any external agent orchestration layers (Hermes Agent, OpenCode Go, etc.).
- The system SHOULD provide clean optional integration points for external agent orchestration layers such as Hermes Agent and OpenCode Go.
- The system MUST gracefully degrade and remain fully functional when external layers are unavailable or disabled.
- The system MUST be built using open-source components and be fully self-hostable.
- All user data and research projects MUST remain private and stored locally by default.
- The system SHOULD be extensible so new agent roles or tools can be added without major refactoring.

## 8. Implementation Technology Constraints
- The core system SHOULD be implemented in Python using LangGraph (or an equivalent stateful multi-agent framework) as the default orchestration layer.
- The system MUST support an Adapter Pattern so that external orchestration layers (Hermes Agent, OpenCode Go, or others) can be plugged in without modifying core logic.
- The system MAY use other languages or frameworks if they provide comparable capabilities for hierarchical stateful orchestration and persistence.
- External layers SHALL be treated strictly as optional enhancers, never as hard dependencies.

## 9. External Layer Integration
- The system MUST provide a clean Adapter / Bridge interface that allows external layers (Hermes Agent, OpenCode Go, etc.) to execute specific workstreams or long-running tasks.
- Integration with external layers MUST be optional and configurable at runtime or via environment variables.
- The core project logic, state management, and living document MUST remain completely independent of any external layer.
- When an external layer is used, the system SHOULD leverage its strengths (e.g., persistent memory, skill creation, low-cost execution) while maintaining full control and auditability.

## 10. Success Criteria
- The system MUST enable a user to complete a philosophical literature review and draft a 2000-word position paper faster and with higher quality than working alone.
- The system MUST reduce the cognitive load of tracking multiple lines of thought and references.
- A minimum viable product (MVP) MUST demonstrate at least Project Coordinator + Literature Search + Synthesis capabilities and run completely independently of external layers.
