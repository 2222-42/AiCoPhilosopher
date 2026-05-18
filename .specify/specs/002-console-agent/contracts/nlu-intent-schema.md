# Contract: NLU Intent Schema

**Date**: 2026-05-18
**Feature**: 002-console-agent
**Interface**: Natural Language Understanding (NLU) Intent Classifier

---

## 1. Overview

The NLU Intent Classifier transforms natural language user input into a structured `UserIntent` with a classified intent type, confidence score, and extracted entities. When confidence is below the configurable threshold (`nlu.confidence_threshold`, default 0.85), the system asks a clarifying question instead of acting.

**Design principle**: The classifier is permissive in understanding but strict in execution — it will try to interpret vague input but refuses to act on low-confidence interpretations.

---

## 2. Intent Types

### 2.1 Full Intent Catalog

| Intent Type | Description | Example User Input | Typical Entities Extracted |
|-------------|-------------|-------------------|---------------------------|
| `start_inquiry` | Begin a new philosophical investigation | "I want to explore free will" | `topic`, `tradition` |
| `clarify_question` | Answer a Socratic clarification | "From an ontological angle" | `angle`, `tradition` |
| `propose_workstream` | Accept/reject proposed workstreams | "Yes, go ahead" / "Not yet" | `acceptance`, `workstream_type` |
| `steer_workstream` | Redirect or refine a workstream | "Focus on post-1980 papers" | `workstream_id`, `instruction`, `filter` |
| `request_status` | Ask for current project/workstream status | "How are things going?" | `workstream_id` (optional) |
| `request_detail` | Ask for deeper explanation of a concept/claim | "Tell me more about Frankfurt cases" | `concept_name`, `claim_id` |
| `request_export` | Request document export | "Can you export this as markdown?" | `format`, `section_name` |
| `approve_action` | Approve a pending coordinator proposal | "Yes, launch it" | `request_id` |
| `reject_action` | Reject a pending coordinator proposal | "No, let's try another approach" | `request_id`, `reason` |
| `ask_question` | Ask a meta-question about the system or process | "What's a workstream?" | `question_topic` |
| `inject_information` | Provide new data or context | "Uploading Pereboom's 2001 paper" | `data_type`, `source` |
| `request_help` | Explicitly request help or guidance | "I'm stuck, what should I do next?" | — |
| `pause_session` | Request session pause/exit | "Let's take a break" / "I need to go" | — |
| `resume_session` | Indicate readiness to continue | "I'm back, let's continue" | — |
| `archive_project` | Request project archival | "Archive this project" | `project_id` |
| `compare_traditions` | Request cross-traditional comparison | "How would a phenomenologist approach this?" | `topic`, `tradition_a`, `tradition_b` |

### 2.2 Intent Priority & Disambiguation

When multiple intents have high confidence, the classifier resolves by priority:

1. `pause_session` / `archive_project` (session lifecycle — highest priority)
2. `approve_action` / `reject_action` (explicit responses to pending requests)
3. `steer_workstream` (explicit steering — overrides implicit)
4. `request_status` / `request_export` (explicit commands)
5. `clarify_question` / `propose_workstream` (dialogue continuation)
6. `start_inquiry` / `ask_question` (general inquiry — lowest priority)

---

## 3. Classification Output Schema

### 3.1 UserIntent (Pydantic Model)

```python
class UserIntent(BaseModel):
    intent_type: IntentType
    confidence: float                    # 0.0 to 1.0
    extracted_entities: dict[str, Any]   # Intent-specific entity map
    raw_input: str                       # Original user input text
    alternative_intents: list[AlternativeIntent]  # Top 3 alternatives
    needs_clarification: bool            # True when confidence < threshold

class AlternativeIntent(BaseModel):
    intent_type: IntentType
    confidence: float
    rationale: str                       # Why this might be the intent
```

### 3.2 Entity Schemas by Intent

#### `start_inquiry`
```json
{
  "topic": "string (required)",
  "tradition": "string | null",
  "scope": "string | null (e.g., 'historical', 'contemporary', 'both')",
  "specific_question": "string | null (explicit question if stated)"
}
```

#### `clarify_question`
```json
{
  "angle": "string (e.g., 'ontological', 'epistemological', 'ethical')",
  "tradition": "string | null",
  "agreement_level": "string | null (one of: 'full', 'partial', 'corrective')",
  "additional_context": "string | null"
}
```

#### `steer_workstream`
```json
{
  "workstream_id": "string | null (null if implicit — infer from focus)",
  "instruction": "string (required)",
  "filter": "string | null (e.g., 'post-1980', 'compatibilist only')",
  "intensity": "string | null (one of: 'focus', 'expand', 'pivot')"
}
```

#### `request_status`
```json
{
  "workstream_id": "string | null",
  "scope": "string | null (one of: 'all', 'project', 'single_workstream')",
  "detail_level": "string | null (one of: 'brief', 'detailed')"
}
```

#### `request_export`
```json
{
  "format": "string (one of: 'markdown', 'html', 'latex')",
  "section_name": "string | null",
  "include_annotations": "bool (default: true)"
}
```

#### `compare_traditions`
```json
{
  "topic": "string (required)",
  "tradition_a": "string (required)",
  "tradition_b": "string (required)",
  "focus": "string | null (e.g., 'ontology', 'methodology', 'conclusions')"
}
```

#### `inject_information`
```json
{
  "data_type": "string (one of: 'pdf', 'text', 'url', 'observation')",
  "source": "string (file path, URL, or description)",
  "relevance": "string | null (how it relates to current inquiry)"
}
```

#### `approve_action` / `reject_action`
```json
{
  "request_id": "string | null (infer from pending if null)",
  "reason": "string | null (for reject: why it was rejected)",
  "modification": "string | null (for partial approval: 'yes, but...')"
}
```

---

## 4. Clarification Logic

### 4.1 Confidence Threshold

- `nlu.confidence_threshold` (default: 0.85)
- Below threshold → `needs_clarification = True`
- The coordinator presents the top alternative intents as options

### 4.2 Clarification Prompt Templates

**When top intent is near threshold (0.70–0.85) but ambiguous**:
```
"I want to make sure I understand — did you mean [interpretation A] or [interpretation B]?"
```

**When multiple intents are equally likely (variance < 0.1 among top 3)**:
```
"I see a few possibilities here. Are you trying to:
  1. [intent_1_explanation]
  2. [intent_2_explanation]"

```

**When confidence is very low (< 0.50)**:
```
"I'm not sure I understand what you'd like me to do. Could you rephrase?
  (You can also use /help to see what I can do.)"
```

**When input is empty or just noise**:
```
"What philosophical question would you like to explore?"
```

---

## 5. Classification Prompt (LLM System Prompt)

```markdown
You are an intent classifier for AiCoPhilosopher, a philosophical research REPL.
Your job: classify the user's natural language input into one of 16 intent types.

## Intent Types
[Full list from §2.1 with descriptions and examples]

## Context
The user is in a REPL session. The current context is:
- Project: {project_title}
- Active workstreams: {workstream_list}
- Last topic discussed: {active_topic}
- Pending decisions: {pending_count} approvals awaiting response

## Output Format
Return ONLY valid JSON, no markdown, no code fences:
{
  "intent_type": "<one of the 16 types>",
  "confidence": <float 0.0-1.0>,
  "extracted_entities": {<intent-specific entity map per §3.2>},
  "alternative_intents": [
    {"intent_type": "<type>", "confidence": <float>, "rationale": "<why>"}
  ],
  "needs_clarification": <bool>
}

## Rules
- Confidence MUST reflect how certain you are. Be honest: 0.95 for clear matches, 0.60 for guesses.
- alternative_intents: top 1-3 alternatives only. Leave empty if no alternatives.
- extracted_entities: only extract what the user explicitly stated. Don't invent entities.
- needs_clarification: true if confidence < 0.85 OR if multiple intents are plausible.

## Input
{user_input}
```

---

## 6. Rule-Based Fallback (Offline Mode)

When the LLM backend is unavailable (offline, network failure, budget cap):

```python
# Pattern matching for common intent signals
FALLBACK_PATTERNS = {
    "start_inquiry": [r"\bexplore\b", r"\binvestigate\b", r"\bunderstand\b", r"\bwhat is\b", r"とは", r"調べ"],
    "steer_workstream": [r"\bfocus on\b", r"\binstead\b", r"\bactually\b", r"\bchange\b"],
    "request_status": [r"\bhow.*going\b", r"\bstatus\b", r"\bprogress\b", r"\bupdate\b"],
    "request_export": [r"\bexport\b", r"\bsave as\b", r"\bdownload\b"],
    "approve_action": [r"\byes\b", r"\bgo ahead\b", r"\bsure\b", r"\bapproved\b", r"はい", r"いい"],
    "reject_action": [r"\bno\b", r"\bstop\b", r"\bdon't\b", r"\bnot yet\b", r"いいえ", r"やめ"],
    "pause_session": [r"\bexit\b", r"\bquit\b", r"\bgoodbye\b", r"\bbreak\b"],
}
```

Fallback classification returns `confidence: 0.80` (below threshold → will ask clarification) with the pattern-matched intent as `alternative_intents[0]`.

---

## 7. Validation Rules

- `confidence` must be in [0.0, 1.0]
- `intent_type` must be one of the 16 valid IntentType enum values
- `extracted_entities` must match the schema for that intent type (per §3.2)
- `alternative_intents` must contain 0-3 entries
- `needs_clarification` must be True when `confidence < nlu.confidence_threshold`
- `raw_input` must be non-empty (empty input handled by REPL loop before classification)

---

**Contract Version**: 1.0.0 | **Last Updated**: 2026-05-18
