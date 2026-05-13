# Contract: External Agent Bridge

**Date**: 2026-05-13  
**Feature**: AiCoPhilosopher v2.0  
**Interface**: External Orchestration Layer Adapter

---

## 1. Overview

The External Agent Bridge translates internal Workstream requests into calls to external agent orchestration layers (e.g., Hermes Agent, OpenCode Go). It implements the **Adapter Pattern** mandated by the specification (spec §8) and constitution (Constitution Principle I: Core Independence).

**Core requirement**: The system MUST run completely without any external layer. The Bridge is strictly optional and MUST NOT break core functionality when disabled or unavailable.

---

## 2. Architecture

```
Internal Workstream Request
        ↓
ExternalAgentBridge
        ↓
    ┌───┴───┐
    ↓       ↓
Hermes   OpenCode Go
Adapter   Adapter
    ↓       ↓
External Layer APIs
```

**Design principles**:
1. **Seamless fallback**: If external layer is unavailable or returns an error, the task is re-routed to internal LangGraph execution automatically
2. **Standardized JSON protocol**: All interactions use the same message schema as internal agents (see `message-protocol.md`)
3. **Zero data leakage**: User data is NEVER transmitted to external layers without explicit per-request consent
4. **Audit logging**: All external interactions are logged locally for transparency

---

## 3. Bridge Interface

```python
class ExternalAgentBridge(ABC):
    """Abstract base for all external layer adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name (e.g., 'Hermes Agent', 'OpenCode Go')."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if external layer is reachable and configured."""

    @abstractmethod
    async def execute_workstream(
        self,
        workstream_type: WorkstreamType,
        goal_statement: GoalStatement,
        context: ProjectState,
        timeout: timedelta = timedelta(hours=24)
    ) -> WorkstreamResult:
        """Delegate a workstream to the external layer.

        Returns:
            WorkstreamResult on success

        Raises:
            ExternalLayerUnavailableError: If layer is unreachable (caller should fallback to internal)
            ExternalLayerExecutionError: If layer fails during execution (caller should fallback to internal)
            ExternalLayerTimeoutError: If execution exceeds timeout (caller should fallback to internal)
        """

    @abstractmethod
    async def get_capabilities(self) -> list[Capability]:
        """List capabilities supported by this external layer.
        Used by Project Coordinator to decide whether to delegate or use internal execution."""

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check connectivity and basic functionality."""
```

### 3.1 Capability Model

```python
class Capability(BaseModel):
    name: str  # e.g., "long_context_reasoning", "persistent_memory", "low_cost_execution"
    description: str
    supported_workstream_types: list[WorkstreamType]
    confidence: float  # 0.0-1.0; how reliable is this capability?
```

### 3.2 WorkstreamResult

```python
class WorkstreamResult(BaseModel):
    status: Literal["success", "partial_success", "failure"]
    report: str | None = None  # Markdown report from external layer
    artifacts: list[Artifact] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    external_log_id: str | None = None  # For cross-referencing external layer logs
```

---

## 4. Concrete Adapters

### 4.1 Hermes Agent Adapter

**Configuration**:
```yaml
external_layers:
  hermes:
    enabled: false  # Default: disabled
    endpoint: "https://hermes.example.com/api/v1"
    api_key: "${HERMES_API_KEY}"  # From environment variable
    timeout_hours: 24
    max_concurrent_workstreams: 3
    allowed_workstream_types:
      - "literature_search"
      - "concept_analysis"
      - "argumentation"
    data_sharing: "explicit_consent"  # Options: "never", "explicit_consent", "always"
```

**Mapping**:
| Internal Concept | Hermes Equivalent |
|-----------------|-------------------|
| Workstream | Hermes "Task" |
| Project Coordinator | Hermes "Orchestrator" |
| Goal Statement | Hermes "Objective" |
| Review Round | Hermes "Validation Loop" |

**Data transmission rules**:
- `data_sharing: "never"`: Bridge only transmits workstream type and goal description. No project context, no living document, no hypotheses.
- `data_sharing: "explicit_consent"`: User is prompted per workstream: "Allow Hermes to access your project context for this Literature Search? [y/N]"
- `data_sharing: "always"`: All project context is shared (NOT recommended; violates Constitution Principle I)

### 4.2 OpenCode Go Adapter

**Configuration**:
```yaml
external_layers:
  opencode_go:
    enabled: false
    endpoint: "http://localhost:8080"  # Local OpenCode Go instance
    timeout_hours: 48
    max_concurrent_workstreams: 5
    allowed_workstream_types:
      - "literature_search"
      - "synthesis"
    data_sharing: "explicit_consent"
```

**Mapping**:
| Internal Concept | OpenCode Go Equivalent |
|-----------------|------------------------|
| Workstream | OpenCode "Mission" |
| Project Coordinator | OpenCode "Director" |
| Sub-agent | OpenCode "Agent" |

**Special considerations**:
- OpenCode Go typically runs locally (localhost), reducing privacy concerns
- Bridge uses OpenCode's native MCP (Model Context Protocol) where available
- Fallback to REST API if MCP is unavailable

---

## 5. Fallback Logic

### 5.1 Automatic Fallback Flow

```python
async def execute_with_fallback(
    bridge: ExternalAgentBridge,
    workstream: WorkstreamState,
    context: ProjectState
) -> WorkstreamResult:
    try:
        if not bridge.is_available:
            logger.info(f"{bridge.name} unavailable; using internal execution")
            return await internal_executor.run(workstream, context)

        if not await user_consent_for_external(bridge, workstream):
            logger.info(f"User denied consent for {bridge.name}; using internal execution")
            return await internal_executor.run(workstream, context)

        result = await bridge.execute_workstream(
            workstream.type,
            workstream.goal_statement,
            context
        )

        if result.status == "failure":
            logger.warning(f"{bridge.name} failed; falling back to internal execution")
            return await internal_executor.run(workstream, context)

        return result

    except (ExternalLayerUnavailableError, ExternalLayerTimeoutError) as e:
        logger.warning(f"{bridge.name} error: {e}; falling back to internal execution")
        return await internal_executor.run(workstream, context)
```

### 5.2 Fallback Triggers

| Condition | Action | Log Level |
|-----------|--------|-----------|
| External layer not configured | Skip bridge, use internal | INFO |
| External layer unreachable (network error) | Fallback to internal | WARNING |
| External layer returns 5xx | Retry once, then fallback | WARNING |
| External layer returns 4xx (bad request) | Fallback immediately | ERROR |
| User denies consent | Skip bridge, use internal | INFO |
| Timeout exceeded | Fallback to internal | WARNING |
| External result confidence < 0.5 | Accept result but flag for review | INFO |

---

## 6. Security & Privacy

### 6.1 Data Classification

| Data Type | Can Transmit to External Layer? | Conditions |
|-----------|--------------------------------|------------|
| Workstream type | Yes | Always |
| Goal statement text | Yes | Always |
| Living document content | No | Never transmitted |
| Hypothesis records | No | Never transmitted |
| User-uploaded PDFs | No | Never transmitted |
| Project metadata (title, dates) | Yes | If user consents |
| Agent-generated reports | Yes | If user consents |
| Conversation history | No | Never transmitted |

### 6.2 Consent Flow

```
[Workstream creation]
    ↓
[Project Coordinator checks if external layer is preferred]
    ↓
[If external layer enabled AND workstream type supported]
    ↓
[Prompt user: "Delegate Literature Search to Hermes Agent?
   Data shared: goal description only.
   [y/N/show details]"]
    ↓
[If user accepts → delegate to external layer]
[If user rejects → use internal execution]
```

### 6.3 Audit Logging

All external layer interactions logged to:
```json
{
  "timestamp": "2026-05-13T10:00:00Z",
  "adapter": "hermes",
  "action": "execute_workstream",
  "workstream_id": "ws-a1b2c3d4",
  "request_hash": "sha256:abc123...",
  "response_hash": "sha256:def456...",
  "duration_ms": 45000,
  "fallback_triggered": false,
  "data_shared": ["workstream_type", "goal_statement"]
}
```

Stored in: `projects/<id>/logs/external_bridge.jsonl`

---

## 7. Configuration

### 7.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AICOPHERMES_ENABLED` | Enable Hermes Agent bridge | `false` |
| `AICOPHERMES_ENDPOINT` | Hermes API endpoint | `null` |
| `AICOPHERMES_API_KEY` | Hermes API key | `null` |
| `AICOPENCODE_ENABLED` | Enable OpenCode Go bridge | `false` |
| `AICOPENCODE_ENDPOINT` | OpenCode Go endpoint | `http://localhost:8080` |
| `AICOPHILOSOPHER_EXTERNAL_DATA_SHARING` | Default data sharing policy | `explicit_consent` |

### 7.2 Runtime Configuration

Users can override defaults via CLI:
```
> config external.hermes.enabled true
> config external.hermes.endpoint https://hermes.example.com/api/v1
> config external.data_sharing explicit_consent
```

---

## 8. Testing Strategy

### 8.1 Mock Adapter

For testing without external dependencies:
```python
class MockExternalAdapter(ExternalAgentBridge):
    """Returns pre-configured responses for deterministic tests."""

    def __init__(self, responses: dict[str, WorkstreamResult]):
        self.responses = responses

    async def execute_workstream(self, ...):
        return self.responses.get(workstream_type, default_success_result)
```

### 8.2 Fallback Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| External layer unavailable | Internal executor invoked; no error surfaced to user |
| External layer timeout | Internal executor invoked; warning logged |
| External layer 5xx error | Retry once, then fallback to internal |
| User denies consent | Internal executor invoked; no external call made |
| External returns low confidence | Result accepted but flagged for review |

---

**Contract Version**: 1.0.0 | **Last Updated**: 2026-05-13
