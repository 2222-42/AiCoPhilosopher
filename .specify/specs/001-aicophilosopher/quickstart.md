# Quickstart: AiCoPhilosopher Development

**Date**: 2026-05-13  
**Feature**: AiCoPhilosopher v2.0  
**Audience**: Developers contributing to the project

---

## 1. Prerequisites

- Python 3.11 or higher
- Git
- (Optional) Ollama for local LLM testing
- (Optional) Anthropic API key for Claude backend
- (Optional) Google API key for Gemini backend

## 2. Environment Setup

### 2.1 Clone & Install

```bash
# Clone the repository
git clone <repository-url>
cd aicophilosopher

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 2.2 Configuration

Create `.env` file in project root:

```bash
# LLM Backends (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
# OLLAMA_BASE_URL=http://localhost:11434  # Default; uncomment if non-standard

# Privacy & External Services
ALLOW_EXTERNAL_SEARCH=true  # Set to false for fully offline operation
EXTERNAL_DATA_SHARING=explicit_consent

# Workspace
AICOPHILOSOPHER_WORKSPACE_DIR=~/.aicophilosopher

# External Layers (optional)
HERMES_ENABLED=false
HERMES_ENDPOINT=https://hermes.example.com/api/v1
HERMES_API_KEY=...
OPENCODE_ENABLED=false
OPENCODE_ENDPOINT=http://localhost:8080
```

**Security note**: Never commit `.env` to Git. It is already in `.gitignore`.

### 2.3 Verify Installation

```bash
# Check CLI is available
python -m aicophilosopher --help

# Run smoke test
python -m pytest tests/unit/test_models.py -v
```

## 3. Project Structure for Development

```
src/aicophilosopher/
├── core/           # State schemas, workspace, config
├── agents/         # Agent implementations
├── reasoning/      # Logic engine, tradition manager, uncertainty
├── artifacts/      # Living document, review process
├── tools/          # Search, PDF RAG, code execution
├── interfaces/     # CLI, external bridge
├── messaging/      # Message protocol, queue
└── persistence/    # SQLite, vector store
```

## 4. Running the MVP

### 4.1 Start Interactive Session

```bash
# Start with default settings
python -m aicophilosopher

# Or specify backend
python -m aicophilosopher --backend ollama --model llama3:8b
```

### 4.2 Basic Workflow

```bash
# 1. Create a new project
> new project "Free Will and Determinism" -q "Is compatibilism a coherent position?"

# 2. Engage in clarification dialogue
> refine goal
# ... answer coordinator's questions ...
# ... approve refined goal ...

# 3. Start literature search workstream
> start workstream literature_search
# Coordinator proposes configuration; you approve

# 4. Check status while workstream runs asynchronously
> status

# 5. Start concept analysis in parallel
> start workstream concept_analysis

# 6. Pause a workstream if needed
> pause ws-a1b2c3d4

# 7. View hypotheses
> show hypotheses

# 8. View living document
> show document

# 9. Export (MVP: Markdown only)
> export markdown
```

### 4.3 Running Offline

```bash
# Disable all external services
export ALLOW_EXTERNAL_SEARCH=false
export HERMES_ENABLED=false
export OPENCODE_ENABLED=false

# Use local Ollama backend
python -m aicophilosopher --backend ollama --model llama3:8b
```

**Note**: Literature Search Agent will use only locally cached papers and RAG corpus when offline.

## 5. Development Commands

### 5.1 Testing

```bash
# Run all tests
make test
# or: python -m pytest

# Run with coverage
make test-cov
# or: python -m pytest --cov=src/aicophilosopher --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_logic_engine.py -v

# Run integration tests (requires mock LLM responses)
python -m pytest tests/integration/ -v

# Run property-based tests
python -m pytest tests/unit/ --hypothesis-seed=0
```

### 5.2 Code Quality

```bash
# Format code
make format
# or: ruff format src/ tests/

# Lint
make lint
# or: ruff check src/ tests/

# Type check
make typecheck
# or: mypy src/aicophilosopher

# Run all quality checks
make check
# Equivalent to: format + lint + typecheck + test
```

### 5.3 Database Inspection

```bash
# SQLite CLI
sqlite3 ~/.aicophilosopher/projects/<project_id>/metadata.db

# List tables
.tables

# Query workstreams
SELECT workstream_id, type, status FROM workstreams;

# Query uncertainty registry
SELECT claim_id, confidence_score, review_status FROM uncertainty_registry;
```

## 6. Adding a New Agent

1. **Create agent file**: `src/aicophilosopher/agents/<agent_name>.py`
2. **Inherit from BaseAgent**: Implement `run()`, `validate_output()`, `get_capabilities()`
3. **Register in ToolRegistry**: `src/aicophilosopher/tools/registry.py`
4. **Add prompt template**: `prompts/agent/<agent_name>.md`
5. **Add tests**: `tests/unit/test_<agent_name>.py`
6. **Update spec**: Document in `.specify/specs/001-aicophilosopher/spec.md`

Example skeleton:
```python
from aicophilosopher.agents.base import BaseAgent

class MyNewAgent(BaseAgent):
    async def run(self, goal: GoalStatement, context: ProjectState) -> AgentResult:
        # Implementation
        return AgentResult(status="success", deliverable="...")
```

## 7. Adding a New Philosophical Tradition

1. **Create tradition profile**: `data/traditions/<tradition_id>.json`
2. **Follow schema**:
```json
{
  "id": "my_tradition",
  "name": "My Tradition",
  "assumptions": ["assumption_1", "assumption_2"],
  "methodological_norms": ["norm_1", "norm_2"],
  "evaluative_criteria": ["criterion_1", "criterion_2"],
  "key_figures": ["Philosopher A", "Philosopher B"],
  "bridge_warnings": []
}
```
3. **Register**: Traditions are auto-discovered from `data/traditions/` on startup
4. **Test**: Add tradition-specific tests to `tests/unit/test_tradition_manager.py`

## 8. Debugging

### 8.1 Enable Verbose Logging

```bash
export AICOPHILOSOPHER_LOG_LEVEL=DEBUG
python -m aicophilosopher
```

### 8.2 Inspect Agent Messages

```bash
# Real-time message stream
watch -n 1 'cat ~/.aicophilosopher/projects/<project_id>/messages/latest.json | jq .'

# Message queue status
sqlite3 ~/.aicophilosopher/projects/<project_id>/metadata.db \
  "SELECT sender_id, recipient_id, message_type, timestamp FROM messages ORDER BY timestamp DESC LIMIT 10;"
```

### 8.3 Review Process Inspection

```bash
# View review rounds for a workstream
sqlite3 ~/.aicophilosopher/projects/<project_id>/metadata.db \
  "SELECT round_number, status, verdicts_json FROM review_rounds WHERE workstream_id = 'ws-a1b2c3d4';"
```

## 9. Common Issues

| Issue | Solution |
|-------|----------|
| `chromadb` fails to import | `pip install --upgrade chromadb` or use LanceDB fallback |
| Ollama connection refused | Ensure Ollama is running: `ollama serve` |
| Anthropic rate limit | Switch backend: `config llm.backend gemini` or wait |
| SQLite locked | Another process is holding the DB. Check for zombie Python processes: `pkill -f aicophilosopher` |
| PDF extraction slow | PyMuPDF should handle 50-page docs in <2s. If slower, check disk I/O or use smaller test PDFs |
| Review process non-termination | Check `review_rounds` table. Max 5 rounds enforced. If stuck, use `steer <ws_id> "override review"` |

## 10. Contributing

1. Create feature branch: `git checkout -b feat/<short-name>`
2. Make changes with tests
3. Run quality checks: `make check`
4. Update documentation if needed
5. Commit: `git commit -m "feat: description"`

See `CONTRIBUTING.md` (post-MVP) for detailed guidelines.

---

**Quickstart Version**: 1.0.0 | **Last Updated**: 2026-05-13
