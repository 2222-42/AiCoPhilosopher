import re
from typing import Any

from aicophilosopher.domain.exceptions import ValidationError

ANNOTATION_PATTERN = re.compile(r"""
    <!--\s*
    Source:\s*(.*?)\s*\|\s*
    Confidence:\s*(.*?)\s*\|\s*
    Origin:\s*(.*?)\s*\|\s*
    Counter-argument\ strength:\s*(.*?)\s*\|\s*
    Tradition:\s*(.*?)\s*\|\s*
    Review\ status:\s*(.*?)
    (?:\|\s*Phenomenological\ grounding:\s*(.*?))?
    \s*-->
""", re.VERBOSE)


FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


class DocumentParser:
    async def parse(self, file_path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise ValidationError(f"File not found: {file_path}")
        except Exception as e:
            raise ValidationError(f"Cannot read file: {e}")

        fm_match = FRONTMATTER_PATTERN.match(content)
        frontmatter: dict[str, Any] = {}
        if fm_match:
            for line in fm_match.group(1).strip().split("\n"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    frontmatter[key.strip()] = value.strip()

        annotations = []
        for match in ANNOTATION_PATTERN.finditer(content):
            ann: dict[str, Any] = {
                "Source": match.group(1).strip(),
                "origin": match.group(3).strip(),
                "tradition": match.group(5).strip(),
                "review_status": match.group(6).strip(),
            }
            raw_conf = match.group(2).strip() if match.group(2) else None
            try:
                ann["confidence"] = float(raw_conf) if raw_conf else None
            except (ValueError, TypeError):
                ann["confidence"] = None

            raw_cas = match.group(4).strip() if match.group(4) else None
            try:
                ann["counter_argument_strength"] = float(raw_cas) if raw_cas else None
            except (ValueError, TypeError):
                ann["counter_argument_strength"] = None

            if match.group(7):
                ann["phenomenological_grounding"] = match.group(7).strip()
            annotations.append(ann)

        return frontmatter, annotations

    async def validate_annotations(self, annotations: list[dict[str, Any]]) -> bool:
        required_fields = {"Source", "confidence", "origin", "counter_argument_strength",
                          "tradition", "review_status"}
        for i, ann in enumerate(annotations):
            missing = required_fields - set(ann.keys())
            if missing:
                raise ValidationError(f"Annotation {i}: missing required fields: {missing}")
            conf = ann.get("confidence")
            if conf is not None and not isinstance(conf, (int, float)):
                raise ValidationError(f"Annotation {i}: confidence must be numeric, got {type(conf).__name__}")
            cas = ann.get("counter_argument_strength")
            if cas is not None and not isinstance(cas, (int, float)):
                raise ValidationError(f"Annotation {i}: counter_argument_strength must be numeric, got {type(cas).__name__}")
        return True
