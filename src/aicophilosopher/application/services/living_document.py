import re
from typing import Any

ANNOTATION_PATTERN = re.compile(r"<!--\s*Source:\s*(.*?)\s*\|\s*Confidence:\s*(.*?)\s*\|\s*Origin:\s*(.*?)\s*\|\s*Counter-argument strength:\s*(.*?)\s*\|\s*Tradition:\s*(.*?)\s*\|\s*Review status:\s*(.*?)\s*(?:\|\s*Phenomenological grounding:\s*(.*?))?\s*-->")


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
            if isinstance(v, list):
                frontmatter_yaml += f"{k}: [{','.join(v)}]\n" if v else f"{k}: []\n"
            else:
                frontmatter_yaml += f"{k}: {v}\n"
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

    async def embed_annotations(self) -> str:
        return self.content

    async def parse_annotations(self) -> list[dict[str, Any]]:
        annotations: list[dict[str, Any]] = []
        for match in ANNOTATION_PATTERN.finditer(self.content):
            annotation = {
                "Source": match.group(1).strip(),
                "Confidence": float(match.group(2).strip()) if match.group(2) else None,
                "Origin": match.group(3).strip(),
                "Counter-argument strength": float(match.group(4).strip()) if match.group(4) else None,
                "Tradition": match.group(5).strip(),
                "Review status": match.group(6).strip(),
            }
            if match.group(7):
                annotation["Phenomenological grounding"] = match.group(7).strip()
            annotations.append(annotation)
        return annotations

    def get_section(self, name: str) -> str | None:
        pattern = rf"^## {re.escape(name)}\s*$(.*?)(?=^##\s|\Z)"
        match = re.search(pattern, self.content, re.MULTILINE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
