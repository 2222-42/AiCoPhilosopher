"""NLU intent classifier for Console Agent REPL (002-console-agent).

Classifies natural language input into one of 16 IntentType values
via LLM-based classification with rule-based fallback for offline mode.
"""

import json
import re
from pathlib import Path

from aicophilosopher.domain.entities.session import (
    AlternativeIntent,
    FocusContext,
    IntentType,
    UserIntent,
)
from aicophilosopher.ports.llm_port import LLMPort

# ── Rule-based fallback patterns ─────────────────────────────────────────

FALLBACK_PATTERNS: dict[IntentType, list[str]] = {
    IntentType.START_INQUIRY: [
        r"\bexplore\b",
        r"\binvestigate\b",
        r"\bunderstand\b",
        r"\bwhat is\b",
        r"とは",
        r"調べ",
    ],
    IntentType.STEER_WORKSTREAM: [
        r"\bfocus on\b",
        r"\binstead\b",
        r"\bactually\b",
        r"\bchange\b",
        r"\bredirect\b",
    ],
    IntentType.REQUEST_STATUS: [
        r"\bhow.*going\b",
        r"\bstatus\b",
        r"\bprogress\b",
        r"\bupdate\b",
    ],
    IntentType.REQUEST_EXPORT: [
        r"\bexport\b",
        r"\bsave as\b",
        r"\bdownload\b",
    ],
    IntentType.APPROVE_ACTION: [
        r"\byes\b",
        r"\bgo ahead\b",
        r"\bsure\b",
        r"\bapproved\b",
        r"はい",
        r"いい",
    ],
    IntentType.REJECT_ACTION: [
        r"\bno\b",
        r"\bstop\b",
        r"\bdon't\b",
        r"\bnot yet\b",
        r"いいえ",
        r"やめ",
    ],
    IntentType.PAUSE_SESSION: [
        r"\bexit\b",
        r"\bquit\b",
        r"\bgoodbye\b",
        r"\bbreak\b",
    ],
}


def fallback_classify(user_input: str) -> UserIntent:
    """Rule-based intent classification when LLM is unavailable.

    Returns confidence=0.80 (always below threshold → needs_clarification=True).
    Falls back to START_INQUIRY when no pattern matches.
    """
    lower = user_input.lower()
    for intent_type, patterns in FALLBACK_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                return UserIntent(
                    intent_type=intent_type,
                    confidence=0.80,
                    raw_input=user_input,
                    needs_clarification=True,
                )
    return UserIntent(
        intent_type=IntentType.START_INQUIRY,
        confidence=0.80,
        raw_input=user_input,
        needs_clarification=True,
    )


# ── LLM-based classification ────────────────────────────────────────────

_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent / "prompts" / "nlu" / "intent_classifier.md"
)

INTENT_VALUE_MAP: dict[str, IntentType] = {t.value: t for t in IntentType}


async def classify_intent(
    user_input: str,
    focus: FocusContext,
    llm_port: LLMPort,
) -> UserIntent:
    """Classify user input using LLM with fallback.

    Returns UserIntent with needs_clarification=True when:
    - Input is empty
    - LLM unavailable (triggers fallback_classify)
    - LLM response parsing fails
    - confidence < 0.85
    """
    if not user_input.strip():
        return UserIntent(
            intent_type=IntentType.START_INQUIRY,
            confidence=0.0,
            raw_input=user_input,
            needs_clarification=True,
        )

    # Build prompt from template
    try:
        prompt_template = _PROMPT_PATH.read_text()
    except (FileNotFoundError, OSError):
        prompt_template = "Classify: {user_input}"

    prompt = (
        prompt_template.replace("{project_title}", focus.active_topic or "(new)")
        .replace("{workstream_list}", str(focus.last_workstream_id or "none"))
        .replace("{active_topic}", focus.active_topic or "")
        .replace("{pending_count}", str(len(focus.pending_decisions)))
        .replace("{user_input}", user_input)
    )

    # Attempt LLM classification
    try:
        result = await llm_port.generate(prompt)
        return _parse_llm_response(result.text, user_input)
    except Exception:
        return fallback_classify(user_input)


def _parse_llm_response(text: str, raw_input: str) -> UserIntent:
    """Parse LLM JSON response into UserIntent. Falls back on any error."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return UserIntent(
            intent_type=IntentType.START_INQUIRY,
            confidence=0.0,
            raw_input=raw_input,
            needs_clarification=True,
        )

    intent_type_str = data.get("intent_type", "start_inquiry")
    intent_type = INTENT_VALUE_MAP.get(intent_type_str, IntentType.START_INQUIRY)

    confidence = float(data.get("confidence", 0.0))
    if not (0.0 <= confidence <= 1.0):
        confidence = 0.0

    extracted_entities: dict[str, object] = data.get("extracted_entities", {})
    if not isinstance(extracted_entities, dict):
        extracted_entities = {}

    alternatives_raw = data.get("alternative_intents", [])
    alternatives: list[AlternativeIntent] = []
    if isinstance(alternatives_raw, list):
        for alt in alternatives_raw[:3]:
            if isinstance(alt, dict):
                alt_type_str = alt.get("intent_type", "")
                alt_type = INTENT_VALUE_MAP.get(alt_type_str, IntentType.START_INQUIRY)
                alt_conf = float(alt.get("confidence", 0.0))
                if not (0.0 <= alt_conf <= 1.0):
                    alt_conf = 0.0
                alternatives.append(
                    AlternativeIntent(
                        intent_type=alt_type,
                        confidence=alt_conf,
                        rationale=str(alt.get("rationale", "")),
                    )
                )

    needs_clarification = confidence < 0.85 or bool(data.get("needs_clarification", False))

    return UserIntent(
        intent_type=intent_type,
        confidence=confidence,
        extracted_entities=extracted_entities,
        raw_input=raw_input,
        alternative_intents=alternatives,
        needs_clarification=needs_clarification,
    )
