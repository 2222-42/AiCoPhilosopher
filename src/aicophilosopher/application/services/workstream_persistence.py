"""Persist workstream agent results into project metadata and living document.

CLI path: after `start-workstream` completes, extract hypotheses / findings
from the agent result and write them to:

- ``metadata.json`` (``hypotheses`` list + ``workstreams`` map)
- ``hypotheses.jsonl`` (append-only history)
- ``living_document.md`` (new section for the workstream)
- ``workstreams/<id>_report.md`` (raw structured report)

This keeps the CLI pathway self-contained (Issue #63) without requiring
the Coordinator → Agent wiring from Issue #60.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _strength_from_confidence(confidence: float) -> str:
    if confidence >= 0.8:
        return "strong"
    if confidence >= 0.55:
        return "moderate"
    return "weak"


def _hypothesis(
    statement: str,
    *,
    confidence: float = 0.5,
    tradition: str | None = None,
    workstream_id: str,
    workstream_type: str,
    origin: str = "ai",
    status: str = "active",
) -> dict[str, Any]:
    return {
        "hypothesis_id": _new_id("hyp"),
        "statement": statement.strip(),
        "strength": _strength_from_confidence(confidence),
        "origin": origin,
        "status": status,
        "epistemic_tradition": tradition,
        "confidence_score": float(confidence),
        "created_at": _now(),
        "source_workstream": workstream_id,
        "workstream_type": workstream_type,
    }


def _hyp_kwargs(workstream_id: str, workstream_type: str) -> dict[str, str]:
    return {"workstream_id": workstream_id, "workstream_type": workstream_type}


def _from_argumentation(
    result: dict[str, Any], workstream_id: str, workstream_type: str
) -> list[dict[str, Any]]:
    hyps: list[dict[str, Any]] = []
    args = list(result.get("arguments") or []) + list(
        result.get("competing_positions") or []
    )
    base = _hyp_kwargs(workstream_id, workstream_type)
    for arg in args:
        if not isinstance(arg, dict):
            continue
        conclusion = arg.get("conclusion")
        if not conclusion:
            continue
        conf = float(arg.get("confidence", 0.5) or 0.5)
        hyps.append(
            _hypothesis(
                str(conclusion),
                confidence=conf,
                tradition=arg.get("tradition"),
                **base,
            )
        )
    return hyps


def _from_literature(
    result: dict[str, Any], workstream_id: str, workstream_type: str
) -> list[dict[str, Any]]:
    hyps: list[dict[str, Any]] = []
    base = _hyp_kwargs(workstream_id, workstream_type)
    for note in result.get("bridge_notes") or []:
        if not isinstance(note, dict):
            continue
        text = note.get("note") or ""
        if not text:
            continue
        conf = float(note.get("confidence_score", 0.5) or 0.5)
        trad = None
        if note.get("from_tradition") and note.get("to_tradition"):
            trad = f"{note['from_tradition']}→{note['to_tradition']}"
        hyps.append(_hypothesis(str(text), confidence=conf, tradition=trad, **base))
    if hyps:
        return hyps
    # Fallback: surface top bibliography items when no bridge notes.
    for item in (result.get("bibliography") or [])[:3]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if not title:
            continue
        abstract = (item.get("abstract") or "").strip()
        statement = f"Literature: {title}"
        if abstract:
            statement = f"{statement} — {abstract[:200]}"
        hyps.append(
            _hypothesis(
                statement,
                confidence=float(item.get("relevance_score", 0.5) or 0.5),
                tradition=item.get("tradition_tag"),
                **base,
            )
        )
    return hyps


def _from_concept_analysis(
    result: dict[str, Any], workstream_id: str, workstream_type: str
) -> list[dict[str, Any]]:
    hyps: list[dict[str, Any]] = []
    base = _hyp_kwargs(workstream_id, workstream_type)
    conf = float(result.get("confidence", 0.75) or 0.75)
    for node in (result.get("concept_map") or [])[:5]:
        if not isinstance(node, dict):
            continue
        name = node.get("name") or node.get("concept_id") or ""
        definition = node.get("definition") or ""
        if not name and not definition:
            continue
        statement = f"{name}: {definition}".strip(": ")
        hyps.append(
            _hypothesis(
                statement,
                confidence=conf,
                tradition=node.get("tradition"),
                **base,
            )
        )
    for te in (result.get("thought_experiments") or [])[:2]:
        if not isinstance(te, dict):
            continue
        name = te.get("name") or "thought experiment"
        desc = te.get("description") or ""
        hyps.append(
            _hypothesis(
                f"Thought experiment ({name}): {desc}"[:500],
                confidence=0.6,
                tradition=te.get("tradition"),
                **base,
            )
        )
    return hyps


def _from_cross_traditional(
    result: dict[str, Any], workstream_id: str, workstream_type: str
) -> list[dict[str, Any]]:
    hyps: list[dict[str, Any]] = []
    base = _hyp_kwargs(workstream_id, workstream_type)
    for bridge in result.get("bridge_map") or []:
        if not isinstance(bridge, dict):
            continue
        note = bridge.get("note") or ""
        concept = bridge.get("concept") or ""
        src = bridge.get("source_tradition") or "?"
        tgt = bridge.get("target_tradition") or "?"
        statement = note or f"Bridge {src}→{tgt} on '{concept}'"
        hyps.append(
            _hypothesis(
                str(statement),
                confidence=float(bridge.get("confidence", 0.5) or 0.5),
                tradition=f"{src}→{tgt}",
                **base,
            )
        )
    overall = float(result.get("overall_confidence", 0.5) or 0.5)
    for item in result.get("incommensurability_register") or []:
        if not isinstance(item, dict):
            continue
        text = item.get("description") or item.get("note") or str(item)
        hyps.append(
            _hypothesis(f"Incommensurability: {text}"[:500], confidence=overall, **base)
        )
    return hyps


def _from_critical_review(
    result: dict[str, Any], workstream_id: str, workstream_type: str
) -> list[dict[str, Any]]:
    hyps: list[dict[str, Any]] = []
    base = _hyp_kwargs(workstream_id, workstream_type)
    overall = float(result.get("overall_confidence", 0.5) or 0.5)
    for ca in result.get("counter_arguments") or []:
        if isinstance(ca, dict):
            text = ca.get("claim") or ca.get("argument") or ca.get("text") or str(ca)
        else:
            text = str(ca)
        if not text:
            continue
        hyps.append(
            _hypothesis(f"Counter-argument: {text}"[:500], confidence=overall, **base)
        )
    for f in result.get("fallacies") or []:
        if not isinstance(f, dict):
            continue
        name = f.get("name") or "fallacy"
        desc = f" — {f['description']}" if f.get("description") else ""
        hyps.append(
            _hypothesis(f"Fallacy flagged: {name}{desc}", confidence=0.6, **base)
        )
    return hyps


def _from_synthesis(
    result: dict[str, Any], workstream_id: str, workstream_type: str
) -> list[dict[str, Any]]:
    hyps: list[dict[str, Any]] = []
    base = _hyp_kwargs(workstream_id, workstream_type)
    for ann in result.get("annotations") or []:
        if not isinstance(ann, dict):
            continue
        claim = ann.get("claim") or ann.get("claim_text") or ""
        if not claim:
            continue
        hyps.append(
            _hypothesis(
                str(claim),
                confidence=float(ann.get("confidence", 0.5) or 0.5),
                tradition=ann.get("tradition"),
                **base,
            )
        )
    if hyps:
        return hyps
    doc = str(result.get("synthesized_document") or "").strip()
    if not doc:
        return hyps
    conf = float(result.get("synthesis_confidence", 0.5) or 0.5)
    for line in doc.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("_"):
            hyps.append(_hypothesis(line[:500], confidence=conf, **base))
            break
    return hyps


_EXTRACTORS: dict[
    str, Callable[[dict[str, Any], str, str], list[dict[str, Any]]]
] = {
    "argumentation": _from_argumentation,
    "literature_search": _from_literature,
    "concept_analysis": _from_concept_analysis,
    "cross_traditional_comparison": _from_cross_traditional,
    "critical_review": _from_critical_review,
    "synthesis": _from_synthesis,
}


def extract_hypotheses(
    workstream_type: str,
    result: dict[str, Any],
    workstream_id: str,
) -> list[dict[str, Any]]:
    """Extract hypothesis records from a workstream agent result dict."""
    extractor = _EXTRACTORS.get(workstream_type)
    hyps = extractor(result, workstream_id, workstream_type) if extractor else []

    # Deduplicate by statement (case-insensitive), keep first.
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for h in hyps:
        key = h["statement"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(h)
    return unique


def _section_argumentation(result: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for i, arg in enumerate(result.get("arguments") or [], 1):
        if not isinstance(arg, dict):
            continue
        lines.append(f"### Position {i}")
        lines.append(f"**Conclusion:** {arg.get('conclusion', '')}")
        tradition = arg.get("tradition", "?")
        conf = arg.get("confidence", "?")
        lines.append(f"**Tradition:** {tradition} | **Confidence:** {conf}")
        premises = arg.get("premises") or []
        if premises:
            lines.append("**Premises:**")
            for p in premises:
                lines.append(f"- {p}")
        lines.append("")
    competing = result.get("competing_positions") or []
    if competing:
        lines.append("### Competing Positions")
        for pos in competing:
            if isinstance(pos, dict):
                lines.append(
                    f"- [{pos.get('tradition', '?')}] {pos.get('conclusion', '')}"
                )
        lines.append("")
    return lines


def _section_literature(result: dict[str, Any]) -> list[str]:
    lines = [
        f"**Query:** {result.get('query', '')}",
        f"**Results:** {result.get('result_count', 0)}",
        "",
    ]
    for item in (result.get("bibliography") or [])[:10]:
        if not isinstance(item, dict):
            continue
        authors = ", ".join(item.get("authors") or []) or "Unknown"
        year = item.get("year") or "n.d."
        lines.append(f"- {item.get('title', '')} ({authors}, {year})")
    if result.get("bridge_notes"):
        lines.append("")
        lines.append("### Bridge Notes")
        for note in result["bridge_notes"]:
            if isinstance(note, dict):
                lines.append(
                    f"- [{note.get('from_tradition', '?')}→"
                    f"{note.get('to_tradition', '?')}] {note.get('note', '')}"
                )
    lines.append("")
    return lines


def _section_concept(result: dict[str, Any]) -> list[str]:
    lines = [f"**Concept:** {result.get('concept', '')}", ""]
    for node in (result.get("concept_map") or [])[:8]:
        if isinstance(node, dict):
            lines.append(
                f"- **{node.get('name', '')}** "
                f"[{node.get('tradition', '?')}]: {node.get('definition', '')}"
            )
    lines.append("")
    return lines


def _section_cross(result: dict[str, Any]) -> list[str]:
    lines = [
        f"**Topic:** {result.get('topic', '')}",
        f"**Bridges:** {len(result.get('bridge_map') or [])}",
        f"**Incommensurabilities:** "
        f"{len(result.get('incommensurability_register') or [])}",
        "",
    ]
    for bridge in result.get("bridge_map") or []:
        if isinstance(bridge, dict):
            lines.append(
                f"- {bridge.get('source_tradition', '?')} → "
                f"{bridge.get('target_tradition', '?')}: "
                f"{bridge.get('note', '')}"
            )
    lines.append("")
    return lines


def _section_critical(result: dict[str, Any]) -> list[str]:
    lines = [f"**Fallacies:** {len(result.get('fallacies') or [])}"]
    for f in result.get("fallacies") or []:
        if isinstance(f, dict):
            lines.append(f"- [{f.get('severity', '?')}] {f.get('name', '?')}")
    lines.append(
        f"**Counter-arguments:** {len(result.get('counter_arguments') or [])}"
    )
    lines.append("")
    return lines


def _section_synthesis(result: dict[str, Any]) -> list[str]:
    doc = str(result.get("synthesized_document") or "")
    excerpt = doc if len(doc) <= 2000 else doc[:2000] + "\n\n_…(truncated)_"
    return [excerpt, ""]


_SECTION_BUILDERS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "argumentation": _section_argumentation,
    "literature_search": _section_literature,
    "concept_analysis": _section_concept,
    "cross_traditional_comparison": _section_cross,
    "critical_review": _section_critical,
    "synthesis": _section_synthesis,
}


def format_document_section(
    workstream_type: str,
    result: dict[str, Any],
    workstream_id: str,
    hypotheses: list[dict[str, Any]],
) -> str:
    """Build a markdown section summarizing the workstream for the living document."""
    lines = [
        f"## Workstream: {workstream_type} ({workstream_id})",
        "",
        f"_Completed: {_now()}_",
        "",
    ]
    builder = _SECTION_BUILDERS.get(workstream_type)
    if builder:
        lines.extend(builder(result))

    if hypotheses:
        lines.append("### Extracted Hypotheses")
        for h in hypotheses:
            conf = h.get("confidence_score", "?")
            status = h.get("status", "active")
            lines.append(
                f"- **[{h.get('hypothesis_id')}]** ({status}, conf={conf}) "
                f"{h.get('statement', '')}"
            )
        lines.append("")

    return "\n".join(lines)


def format_workstream_report(
    workstream_type: str,
    result: dict[str, Any],
    workstream_id: str,
) -> str:
    """Serialize the full agent result as a markdown + JSON report."""
    header = (
        f"# Workstream Report: {workstream_type}\n\n"
        f"- **ID:** {workstream_id}\n"
        f"- **Completed:** {_now()}\n\n"
        f"## Raw Result (JSON)\n\n```json\n"
    )
    body = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    return header + body + "\n```\n"


_RESULT_SUMMARY_KEYS = (
    "result_count",
    "argument_count",
    "overall_confidence",
    "synthesis_confidence",
    "confidence",
    "query",
    "concept",
    "topic",
)


def persist_workstream_results(
    project_dir: Path,
    workstream_type: str,
    result: dict[str, Any],
    *,
    workstream_id: str | None = None,
) -> dict[str, Any]:
    """Write workstream results into project files. Returns persistence summary.

    Parameters
    ----------
    project_dir:
        Absolute or relative path to the project directory (contains
        ``metadata.json`` and ``living_document.md``).
    workstream_type:
        One of the CLI workstream type strings.
    result:
        Agent ``run()`` return value.
    workstream_id:
        Optional explicit id; generated if omitted.

    Returns
    -------
    dict with keys: workstream_id, hypotheses_added, document_updated, report_path
    """
    project_dir = Path(project_dir)
    ws_id = workstream_id or _new_id("ws")
    meta_path = project_dir / "metadata.json"
    doc_path = project_dir / "living_document.md"
    hyp_jsonl = project_dir / "hypotheses.jsonl"
    ws_dir = project_dir / "workstreams"
    ws_dir.mkdir(parents=True, exist_ok=True)

    hypotheses = extract_hypotheses(workstream_type, result, ws_id)
    section = format_document_section(workstream_type, result, ws_id, hypotheses)
    report = format_workstream_report(workstream_type, result, ws_id)

    # ── metadata.json ────────────────────────────────────────────────
    # Fail fast on corrupt metadata rather than wiping the project with {}.
    meta: dict[str, Any]
    if meta_path.exists():
        try:
            raw_meta = meta_path.read_text(encoding="utf-8")
            loaded = json.loads(raw_meta)
        except json.JSONDecodeError as exc:
            backup = meta_path.with_suffix(".json.corrupt")
            try:
                backup.write_text(raw_meta, encoding="utf-8")
            except OSError:
                backup = meta_path
            raise ValueError(
                f"Project metadata is invalid JSON ({meta_path}). "
                f"Corrupt file preserved at {backup}. Fix or restore before persisting."
            ) from exc
        except OSError as exc:
            raise ValueError(
                f"Could not read project metadata ({meta_path}): {exc}"
            ) from exc
        if not isinstance(loaded, dict):
            raise ValueError(
                f"Project metadata must be a JSON object ({meta_path}), "
                f"got {type(loaded).__name__}."
            )
        meta = loaded
    else:
        meta = {}

    if not isinstance(meta.get("hypotheses"), list):
        meta["hypotheses"] = []
    if not isinstance(meta.get("workstreams"), dict):
        meta["workstreams"] = {}

    meta["hypotheses"].extend(hypotheses)
    meta["workstreams"][ws_id] = {
        "workstream_id": ws_id,
        "type": workstream_type,
        "status": "completed",
        "completed_at": _now(),
        "hypothesis_ids": [h["hypothesis_id"] for h in hypotheses],
        "result_summary": {k: result[k] for k in _RESULT_SUMMARY_KEYS if k in result},
    }
    if meta.get("status") in (None, "created", "clarifying"):
        meta["status"] = "active"
    meta["updated_at"] = _now()
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── hypotheses.jsonl ─────────────────────────────────────────────
    if hypotheses:
        with hyp_jsonl.open("a", encoding="utf-8") as f:
            for h in hypotheses:
                f.write(json.dumps(h, ensure_ascii=False) + "\n")

    # ── living_document.md ───────────────────────────────────────────
    if doc_path.exists():
        existing = doc_path.read_text(encoding="utf-8")
        if existing and not existing.endswith("\n"):
            existing += "\n"
        doc_path.write_text(existing + "\n" + section + "\n", encoding="utf-8")
    else:
        title = meta.get("title", "Living Document")
        doc_path.write_text(f"# {title}\n\n" + section + "\n", encoding="utf-8")

    # ── workstream report ────────────────────────────────────────────
    report_path = ws_dir / f"{ws_id}_report.md"
    report_path.write_text(report, encoding="utf-8")

    return {
        "workstream_id": ws_id,
        "hypotheses_added": len(hypotheses),
        "hypotheses": hypotheses,
        "document_updated": True,
        "report_path": str(report_path),
    }


def load_hypotheses(
    project_dir: Path,
    filter_status: str | None = None,
) -> list[dict[str, Any]]:
    """Load hypotheses from metadata.json, optionally filtering by status."""
    meta_path = Path(project_dir) / "metadata.json"
    if not meta_path.exists():
        return []
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    hyps = meta.get("hypotheses") or []
    if not isinstance(hyps, list):
        return []
    if filter_status:
        return [
            h
            for h in hyps
            if isinstance(h, dict) and h.get("status") == filter_status
        ]
    return [h for h in hyps if isinstance(h, dict)]
