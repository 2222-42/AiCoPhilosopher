"""NLU intent classifier for Console Agent REPL (002-console-agent)."""

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

FALLBACK_PATTERNS: dict[IntentType, list[str]] = {
    IntentType.START_INQUIRY: [
        r"\bexplore\b", r"\binvestigate\b", r"\bunderstand\b",
        r"\bwhat is\b", r"とは", r"調べ",
    ],
    IntentType.CLARIFY_QUESTION: [
        r"\bi mean\b", r"\bmore (specifically|interested|about)\b",
        r"\brephrase\b", r"\bnot exactly\b", r"\bi was thinking\b",
        r"\bnarrow\b.*\b(down|this|to)\b", r"\bmore specific\b",
        r"\breally.*\b(want|mean|asking)\b",
        r"\blet me\b.*\b(clarify|rephrase|reframe)\b",
    ],
    IntentType.PROPOSE_WORKSTREAM: [
        r"\bsearch\b", r"\bstart\b.*\b(workstream|search|analy|review|compar|synthes)",
        r"\blaunch\b", r"\bdo\b.*\b(literature|concept|argu|review|search)",
        r"\brun\b.*\b(workstream|analysis|search)",
        r"\bliterature\b", r"\b概念分析\b", r"\b文献\b", r"\b調査\b",
        r"\bargument\b", r"\banaly(sis|ze)\b.*\b(concept|this|that)\b",
        r"\bcompar", r"\breview\b.*\b(argument|workstream|this)",
    ],
    IntentType.STEER_WORKSTREAM: [
        r"\bfocus on\b", r"\bredirect\b", r"\bchange direction\b",
        r"\binstead of\b.*\blet'?s\b", r"\bswitch to\b",
    ],
    IntentType.REQUEST_STATUS: [
        r"\bhow.*going\b", r"\bstatus\b", r"\bprogress\b", r"\bupdate\b",
    ],
    IntentType.REQUEST_EXPORT: [
        r"\bexport\b", r"\bsave as\b", r"\bdownload\b",
    ],
    IntentType.ASK_QUESTION: [
        r"\bwhat (would|does|do|is|are)\b", r"\bhow (do|does|would|can)\b",
        r"\bcan you\b.*\b(explain|clarify|tell|elaborate)\b",
        r"\bwhat'?s the\b", r"\bis there\b",
    ],
    IntentType.APPROVE_ACTION: [
        r"\byes\b", r"\bgo ahead\b", r"\bsure\b", r"\bapproved\b", r"はい", r"いい",
    ],
    IntentType.REJECT_ACTION: [
        r"\bno\b", r"\bstop\b", r"\bdon't\b", r"\bnot yet\b", r"いいえ", r"やめ",
    ],
    IntentType.PAUSE_SESSION: [
        r"\bexit\b", r"\bquit\b", r"\bgoodbye\b", r"\bbreak\b",
    ],
}

_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent / "prompts" / "nlu" / "intent_classifier.md"
)
INTENT_VALUE_MAP: dict[str, IntentType] = {t.value: t for t in IntentType}
_DEFAULT_CONFIDENCE_THRESHOLD = 0.85


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert value to float, returning default on any error."""
    try:
        f = float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return default
    if not (0.0 <= f <= 1.0):
        return default
    return f


# ── Rule-based fallback ──────────────────────────────────────────────────


def fallback_classify(user_input: str) -> UserIntent:
    """Rule-based intent classification when LLM is unavailable.

    Returns the matched intent as the primary type when a pattern matches,
    with confidence=0.80.  When no pattern matches, returns START_INQUIRY
    as a generic fallback.
    """
    lower = user_input.lower()
    matched: IntentType | None = None
    for intent_type, patterns in FALLBACK_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                matched = intent_type
                break
        if matched:
            break

    alternatives: list[AlternativeIntent] = []
    primary = IntentType.START_INQUIRY
    if matched is not None:
        primary = matched
        alternatives = [
            AlternativeIntent(
                intent_type=matched, confidence=0.80, rationale="Pattern-matched fallback"
            )
        ]

    return UserIntent(
        intent_type=primary,
        confidence=0.80,
        raw_input=user_input,
        alternative_intents=alternatives,
        needs_clarification=True,
    )


# ── LLM-based classification ────────────────────────────────────────────


async def classify_intent(
    user_input: str,
    focus: FocusContext,
    llm_port: LLMPort,
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
) -> UserIntent:
    """Classify user input via LLM, falling back to regex on failure."""
    if not user_input.strip():
        return UserIntent(
            intent_type=IntentType.START_INQUIRY,
            confidence=0.0,
            raw_input=user_input,
            needs_clarification=True,
        )

    try:
        prompt_template = _PROMPT_PATH.read_text()
    except (FileNotFoundError, OSError):
        prompt_template = "Classify: {user_input}"

    prompt = (
        prompt_template.replace("{project_title}", focus.active_topic or "(new)")
        .replace("{workstream_list}", focus.active_topic or "(none)")
        .replace("{active_topic}", focus.active_topic or "")
        .replace("{pending_count}", str(len(focus.pending_decisions)))
        .replace("{user_input}", user_input)
    )

    try:
        result = await llm_port.generate(prompt)
        return _parse_llm_response(result.text, user_input, confidence_threshold)
    except Exception:
        return fallback_classify(user_input)


def _parse_llm_response(
    text: str, raw_input: str, threshold: float
) -> UserIntent:
    """Parse LLM JSON into UserIntent; return clarification on any error."""
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

    confidence = _safe_float(data.get("confidence", 0.0))

    extracted_entities: dict[str, object] = data.get("extracted_entities", {})
    if not isinstance(extracted_entities, dict):
        extracted_entities = {}

    alternatives_raw = data.get("alternative_intents", [])
    alternatives: list[AlternativeIntent] = []
    if isinstance(alternatives_raw, list):
        for alt in alternatives_raw:
            if isinstance(alt, dict):
                alt_type_str = alt.get("intent_type", "")
                alt_type = INTENT_VALUE_MAP.get(alt_type_str, IntentType.START_INQUIRY)
                alt_conf = _safe_float(alt.get("confidence", 0.0))
                alternatives.append(
                    AlternativeIntent(
                        intent_type=alt_type,
                        confidence=alt_conf,
                        rationale=str(alt.get("rationale", "")),
                    )
                )
        # Sort by confidence descending, take top 3
        alternatives.sort(key=lambda a: a.confidence, reverse=True)
        alternatives = alternatives[:3]

    needs_clarification = confidence < threshold or bool(
        data.get("needs_clarification", False)
    )

    return UserIntent(
        intent_type=intent_type,
        confidence=confidence,
        extracted_entities=extracted_entities,
        raw_input=raw_input,
        alternative_intents=alternatives,
        needs_clarification=needs_clarification,
    )
