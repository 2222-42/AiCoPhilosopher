"""SynthesisAgent (T-056) — US3 core.

Merges workstream outputs into a coherent living document, preserves
epistemic annotations, detects inter-workstream conflicts, and assigns
a synthesis confidence score.

Conforms to spec §4.9 and Clean Architecture (depends on domain/ + ports/).
"""

from __future__ import annotations

import hashlib
from typing import cast

from aicophilosopher.ports.llm_port import LLMPort


class SynthesisAgent:
    """Merges workstream outputs into a coherent philosophical document (spec §4.9).

    - Preserves epistemic status annotations (confidence, origin, review status).
    - Generates margin notes linking claims to source workstreams.
    - Flags conflicts between workstream outputs.
    - Supports multiple output formats (Markdown default).
    - Assigns synthesis confidence score.
    """

    def __init__(
        self,
        agent_id: str,
        llm: LLMPort | None = None,
        **kwargs: object,
    ) -> None:
        self.agent_id = agent_id
        self._llm = llm

    # ------------------------------------------------------------------
    # Core synthesis
    # ------------------------------------------------------------------
    async def run(
        self, workstream_outputs: list[dict[str, object]], **kwargs: object
    ) -> dict[str, object]:
        """Synthesize workstream outputs into a living document section.

        Args:
            workstream_outputs: List of output dicts from workstream agents.
            **kwargs: Optional overrides (title, use_llm, format).

        Returns:
            Dict with synthesized_document, annotations, conflicts,
            synthesis_confidence, workstream_count.
        """
        if not workstream_outputs:
            return {
                "synthesized_document": "## Synthesis\n\n_No workstream outputs to synthesize._\n",
                "annotations": [],
                "conflicts": [],
                "synthesis_confidence": 0.5,
                "workstream_count": 0,
            }

        title = str(kwargs.get("title", "Synthesis"))

        # 1. Group outputs by type
        grouped = self._group_by_type(workstream_outputs)

        # 2. Generate document sections
        sections = self._build_sections(grouped)

        # 3. Extract and generate annotations
        annotations = self._extract_annotations(workstream_outputs)

        # 4. Detect conflicts
        conflicts = self._detect_conflicts(workstream_outputs)

        # 5. Assemble document
        doc = self._assemble_document(title, sections, conflicts)

        # 6. Compute synthesis confidence
        confidence = self._compute_synthesis_confidence(workstream_outputs, conflicts)

        # 7. LLM augmentation (best-effort)
        llm_used = False
        if self._llm is not None and kwargs.get("use_llm", True):
            try:
                llm_doc = await self._llm_synthesize(doc, workstream_outputs, conflicts)
                if llm_doc:
                    doc = llm_doc
                    llm_used = True
            except (OSError, ConnectionError, RuntimeError):
                pass

        return {
            "synthesized_document": doc,
            "annotations": annotations,
            "conflicts": conflicts,
            "synthesis_confidence": confidence,
            "workstream_count": len(workstream_outputs),
            "llm_augmented": llm_used,
        }

    # ------------------------------------------------------------------
    # Section building
    # ------------------------------------------------------------------
    @staticmethod
    def _group_by_type(
        outputs: list[dict[str, object]],
    ) -> dict[str, list[dict[str, object]]]:
        grouped: dict[str, list[dict[str, object]]] = {}
        for o in outputs:
            ws_type = str(o.get("type", "unknown"))
            grouped.setdefault(ws_type, []).append(o)
        return grouped

    @staticmethod
    def _build_sections(
        grouped: dict[str, list[dict[str, object]]],
    ) -> list[dict[str, object]]:
        section_map = {
            "literature_search": "Literature Review",
            "concept_analysis": "Conceptual Analysis",
            "argumentation": "Arguments & Positions",
            "critical_review": "Critical Review & Fallacies",
            "cross_traditional": "Cross-Traditional Perspectives",
            "phenomenological": "Phenomenological Analysis",
            "ethical_analysis": "Ethical Analysis",
        }

        sections: list[dict[str, object]] = []
        for ws_type, outputs in grouped.items():
            heading = section_map.get(ws_type, ws_type.replace("_", " ").title())
            content_parts: list[str] = []
            for o in outputs:
                results = str(o.get("results", ""))
                if results.strip():
                    content_parts.append(results.strip())

            if content_parts:
                sections.append({
                    "heading": heading,
                    "content": "\n\n".join(content_parts),
                    "source_count": len(outputs),
                })

        return sections

    @staticmethod
    def _assemble_document(
        title: str,
        sections: list[dict[str, object]],
        conflicts: list[dict[str, object]],
    ) -> str:
        lines: list[str] = [f"# {title}\n"]
        lines.append(
            "_Synthesized from multiple philosophical workstreams. "
            "All claims carry epistemic status annotations._\n"
        )

        for sec in sections:
            heading = str(sec["heading"])
            content = str(sec["content"])
            lines.append(f"## {heading}\n")
            lines.append(content)
            lines.append("")

        if conflicts:
            lines.append("## ⚠️ Conflicts & Divergences\n")
            for i, c in enumerate(conflicts, 1):
                desc = str(c.get("description", "Unresolved conflict"))
                confidence = c.get("confidence", 0.5)
                lines.append(
                    f"{i}. **{desc}** "
                    f"[confidence: {float(cast('float', confidence)):.0%}]"
                )
            lines.append("")

        lines.append("---\n")
        lines.append(
            "_Synthesis generated by AI Co-Philosopher. "
            "All claims require human review before acceptance._\n"
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Annotation extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_annotations(
        outputs: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        annotations: list[dict[str, object]] = []
        for o in outputs:
            claims = cast("list[dict[str, object]]", o.get("claims", []))
            ws_id = str(o.get("workstream_id", "unknown"))
            ws_type = str(o.get("type", "unknown"))
            ws_confidence = float(cast("float", o.get("confidence", 0.5)))

            for claim in claims:
                text = str(claim.get("text", ""))
                if len(text) < 20:  # Skip trivial claims
                    continue
                ann_id = hashlib.sha256(
                    f"{ws_id}:{text}".encode()
                ).hexdigest()[:12]
                annotations.append({
                    "annotation_id": ann_id,
                    "claim": text,
                    "confidence": claim.get("confidence", ws_confidence),
                    "origin": claim.get("origin", ws_type),
                    "workstream_id": ws_id,
                    "workstream_type": ws_type,
                    "source_confidence": ws_confidence,
                })

        return annotations

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_conflicts(
        outputs: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        conflicts: list[dict[str, object]] = []

        # Extract all claims
        all_claims: list[tuple[str, str, str]] = []  # (text, ws_id, origin)
        for o in outputs:
            claims = cast("list[dict[str, object]]", o.get("claims", []))
            ws_id = str(o.get("workstream_id", "unknown"))
            for claim in claims:
                text = str(claim.get("text", "")).lower().strip()
                if len(text) > 20:
                    origin = str(claim.get("origin", "unknown"))
                    all_claims.append((text, ws_id, origin))

        # Simple conflict detection: claims with opposite sentiment
        negation_words = {"not", "no", "never", "illusion", "false", "invalid",
                          "refuted", "impossible", "reject"}
        affirmation_words = {"is", "are", "true", "valid", "real", "exists",
                             "support", "reconcile", "compatible"}

        for i in range(len(all_claims)):
            for j in range(i + 1, len(all_claims)):
                text_i, ws_i, origin_i = all_claims[i]
                text_j, ws_j, origin_j = all_claims[j]

                if ws_i == ws_j:
                    continue  # Same workstream; internal consistency not checked here

                # Check keyword overlap
                words_i = set(text_i.split())
                words_j = set(text_j.split())
                overlap = words_i & words_j
                if len(overlap) < 3:
                    continue  # Not about the same topic

                neg_i = bool(words_i & negation_words)
                neg_j = bool(words_j & negation_words)
                aff_i = bool(words_i & affirmation_words)
                aff_j = bool(words_j & affirmation_words)

                # Contradiction: one affirms, other negates on same topic
                if (aff_i and neg_j) or (neg_i and aff_j):
                    conflicts.append({
                        "claim_a": text_i,
                        "claim_b": text_j,
                        "workstream_a": ws_i,
                        "workstream_b": ws_j,
                        "description": (
                            f"Workstream {ws_i} ({origin_i}) claims '{text_i[:60]}...' "
                            f"while {ws_j} ({origin_j}) claims '{text_j[:60]}...'"
                        ),
                        "confidence": 0.7,
                        "resolution": "Requires human adjudication.",
                    })
                    if len(conflicts) >= 5:
                        return conflicts  # Cap at 5 for readability

        return conflicts

    # ------------------------------------------------------------------
    # Synthesis confidence
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_synthesis_confidence(
        outputs: list[dict[str, object]],
        conflicts: list[dict[str, object]],
    ) -> float:
        if not outputs:
            return 0.5

        # Average of workstream confidences
        ws_confidences = [
            float(cast("float", o.get("confidence", 0.5)))
            for o in outputs
        ]
        avg_ws = sum(ws_confidences) / len(ws_confidences)

        # Penalize for conflicts
        conflict_penalty = min(0.3, len(conflicts) * 0.1)

        # Bonus for multiple workstreams converging
        diversity_bonus = min(0.1, (len(outputs) - 1) * 0.03)

        return round(max(0.0, min(1.0, avg_ws - conflict_penalty + diversity_bonus)), 4)

    # ------------------------------------------------------------------
    # LLM augmentation
    # ------------------------------------------------------------------
    async def _llm_synthesize(
        self,
        heuristic_doc: str,
        outputs: list[dict[str, object]],
        conflicts: list[dict[str, object]],
    ) -> str | None:
        if self._llm is None:
            return None
        import json

        outputs_json = json.dumps([
            {"type": o.get("type"), "results": str(o.get("results", ""))[:500]}
            for o in outputs
        ], indent=2)

        prompt = (
            "You are a philosophical synthesis engine. Merge the following "
            "workstream outputs into a coherent, well-structured Markdown "
            "document with a consistent academic voice.\n\n"
            "Workstream outputs:\n" + outputs_json + "\n\n"
            "Heuristic synthesis already generated:\n" + heuristic_doc[:1000] + "\n\n"
            f"Detected conflicts: {len(conflicts)}\n\n"
            "Instructions:\n"
            "- Start with '# Synthesis' heading.\n"
            "- Merge related findings; do not simply concatenate.\n"
            "- Preserve all epistemic markers (confidence, origins).\n"
            "- Flag any contradictions you detect.\n"
            "- End with a synthesis confidence assessment.\n"
            "Return ONLY the Markdown document, no other text."
        )
        try:
            result = await self._llm.generate(prompt)
            text = result.text.strip()
            if len(text) > 50:
                return text
        except (OSError, ConnectionError, RuntimeError):
            pass
        return None
