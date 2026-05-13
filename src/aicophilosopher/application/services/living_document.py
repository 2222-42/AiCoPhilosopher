import re
from typing import Any

ANNOTATION_PATTERN = re.compile(r"<!--\s*Source:\s*(.*?)\s*\|\s*Confidence:\s*(.*?)\s*\|\s*Origin:\s*(.*?)\s*\|\s*Counter-argument strength:\s*(.*?)\s*\|\s*Tradition:\s*(.*?)\s*\|\s*Review status:\s*(.*?)\s*(?:\|\s*Phenomenological grounding:\s*(.*?))?\s*-->")


def _yaml_safe(value: Any) -> str:
    if isinstance(value, list):
        items = ",".join(_yaml_safe(v) for v in value)
        return f"[{items}]"
    s = str(value)
    if any(ch in s for ch in ":[]{}#&*!|>'\"%@`"):
        return f"'{s.replace(chr(39), chr(39)*2)}'"
    return s


def _format_annotation(source: str, confidence: float, origin: str,
                       counter_arg_strength: float, tradition: str,
                       review_status: str, grounding: str | None = None) -> str:
    parts = [
        f"Source: {source}",
        f"Confidence: {confidence}",
        f"Origin: {origin}",
        f"Counter-argument strength: {counter_arg_strength}",
        f"Tradition: {tradition}",
        f"Review status: {review_status}",
    ]
    if grounding:
        parts.append(f"Phenomenological grounding: {grounding}")
    return "<!-- " + " | ".join(parts) + " -->"


class LivingDocument:
    def __init__(self, project_id: str, title: str = "") -> None:
        self.project_id = project_id
        self.title = title
        self.content: str = ""
        self.frontmatter: dict[str, Any] = {}

    async def create(self, title: str, project_id: str) -> str:
        self.title = title
        self.project_id = project_id
        self.frontmatter = {
            "title": title,
            "project_id": project_id,
            "version": 1,
            "epistemic_status": "Draft",
            "traditions_referenced": [],
        }
        frontmatter_yaml = "---\n"
        for k, v in self.frontmatter.items():
            frontmatter_yaml += f"{k}: {_yaml_safe(v)}\n"
        frontmatter_yaml += "---\n\n"

        self.content = frontmatter_yaml + f"# {title}\n\n## Introduction\n\n\n## Key Concepts\n\n\n## Cross-Traditional Perspectives\n\n\n## Arguments\n\n\n## Objections and Replies\n\n\n## Conclusion\n\n\n## References\n\n\n## Dialectical Appendix\n\n"
        return self.content

    async def add_section(self, name: str, content: str) -> None:
        heading_match = re.search(rf"^## {re.escape(name)}\s*$", self.content, re.MULTILINE)
        if heading_match:
            section_end = self._find_next_section_end(heading_match.end())
            before = self.content[:heading_match.end()]
            after = self.content[section_end:] if section_end else ""
            self.content = f"{before}\n\n{content}\n\n{after}"
        else:
            self.content += f"\n## {name}\n\n{content}\n\n"

    def _find_next_section_end(self, start: int) -> int | None:
        rest = self.content[start:]
        next_heading = re.search(r"^##\s", rest, re.MULTILINE)
        if next_heading:
            return start + next_heading.start()
        return None

    async def embed_annotations(self, annotations: list[dict[str, Any]] | None = None) -> str:
        if not annotations:
            return self.content
        result = self.content
        for ann in annotations:
            annotation_str = _format_annotation(
                source=ann.get("source", ann.get("Source", "")),
                confidence=float(ann.get("confidence", ann.get("Confidence", 0.5))),
                origin=ann.get("origin", ann.get("Origin", "ai")),
                counter_arg_strength=float(ann.get("counter_argument_strength", ann.get("Counter-argument strength", 0.0))),
                tradition=ann.get("tradition", ann.get("Tradition", "")),
                review_status=ann.get("review_status", ann.get("Review status", "unreviewed")),
                grounding=ann.get("phenomenological_grounding", ann.get("Phenomenological grounding")),
            )
            claim = ann.get("claim", ann.get("claim_text", ""))
            if claim and claim in result:
                result = result.replace(claim, f"{claim} {annotation_str}")
        self.content = result
        return self.content

    async def parse_annotations(self) -> list[dict[str, Any]]:
        annotations: list[dict[str, Any]] = []
        for match in ANNOTATION_PATTERN.finditer(self.content):
            annotation = {
                "source": match.group(1).strip(),
                "confidence": float(match.group(2).strip()) if match.group(2) else None,
                "origin": match.group(3).strip(),
                "counter_argument_strength": float(match.group(4).strip()) if match.group(4) else None,
                "tradition": match.group(5).strip(),
                "review_status": match.group(6).strip(),
            }
            if match.group(7):
                annotation["phenomenological_grounding"] = match.group(7).strip()
            annotations.append(annotation)
        return annotations

    def get_section(self, name: str) -> str | None:
        pattern = rf"^## {re.escape(name)}\s*$(.*?)(?=^##\s|\Z)"
        match = re.search(pattern, self.content, re.MULTILINE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
