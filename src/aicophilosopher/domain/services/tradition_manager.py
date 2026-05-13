import json
from pathlib import Path
from typing import Any


class TraditionManager:
    def __init__(self, traditions_dir: str | Path | None = None) -> None:
        self.traditions_dir = Path(traditions_dir) if traditions_dir else Path("data/traditions")
        self._profiles: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.traditions_dir.exists():
            return
        for filepath in sorted(self.traditions_dir.glob("*.json")):
            tradition_name = filepath.stem
            with open(filepath) as f:
                self._profiles[tradition_name] = json.load(f)

    def load_traditions(self) -> dict[str, dict[str, Any]]:
        self._ensure_loaded()
        return self._profiles

    def validate_argument(self, argument: str, tradition: str) -> list[str]:
        self._ensure_loaded()
        profile = self._profiles.get(tradition)
        if not profile:
            return [f"Unknown tradition: {tradition}"]
        norms = profile.get("norms", [])
        violations = []
        for norm in norms:
            if norm.get("keyword") and norm["keyword"] not in argument:
                violations.append(norm.get("message", f"Missing {norm.get('keyword')}"))
        return violations

    def check_incommensurability(self, concept_a: str, concept_b: str) -> tuple[bool, str]:
        self._ensure_loaded()
        for profile in self._profiles.values():
            bridge_warnings = profile.get("bridge_warnings", [])
            for warning in bridge_warnings:
                if concept_a in warning.get("concepts", []) and concept_b in warning.get("incompatible_with", []):
                    return True, warning.get("explanation", f"Incommensurability between {concept_a} and {concept_b}")
        return False, ""

    def get_tradition_profile(self, tradition: str) -> dict[str, Any] | None:
        self._ensure_loaded()
        return self._profiles.get(tradition)
