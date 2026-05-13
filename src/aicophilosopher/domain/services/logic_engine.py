import re
from typing import Any


class ValidityResult:
    def __init__(self, is_valid: bool, counter_model: str | None = None, confidence: float = 0.0) -> None:
        self.is_valid = is_valid
        self.counter_model = counter_model
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "counter_model": self.counter_model,
            "confidence": self.confidence,
        }


class LogicEngine:
    def _parse_syllogism_form(self, text: str) -> tuple[str, str, str] | None:
        match = re.match(r"All\s+(\w+)\s+are\s+(\w+)", text.strip())
        if match:
            return ("all", match.group(1), match.group(2))
        match = re.match(r"No\s+(\w+)\s+are\s+(\w+)", text.strip())
        if match:
            return ("no", match.group(1), match.group(2))
        match = re.match(r"Some\s+(\w+)\s+are\s+(\w+)", text.strip())
        if match:
            return ("some", match.group(1), match.group(2))
        return None

    def _check_syllogism(self, premises: list[str], conclusion: str) -> ValidityResult | None:
        parsed_premises = []
        for premise in premises:
            parsed = self._parse_syllogism_form(premise)
            if parsed is None:
                return None
            parsed_premises.append(parsed)

        concl_match = re.match(r"(All|No|Some)\s+(\w+)\s+are\s+(\w+)", conclusion.strip())
        if not concl_match:
            return None

        concl_type = concl_match.group(1).lower()
        concl_s = concl_match.group(2)
        concl_p = concl_match.group(3)

        # Barbara: All M are P; All S are M => All S are P
        if (
            len(parsed_premises) == 2
            and parsed_premises[0][0] == "all"
            and parsed_premises[1][0] == "all"
            and parsed_premises[0][1] == parsed_premises[1][2]
            and parsed_premises[1][1] == concl_s
            and parsed_premises[0][2] == concl_p
            and concl_type == "all"
        ):
            return ValidityResult(is_valid=True, confidence=0.95)

        return ValidityResult(is_valid=False, counter_model="Syllogism does not match known valid patterns", confidence=0.3)

    def check_validity(self, premises: list[str], conclusion: str) -> dict[str, Any]:
        if not premises:
            return ValidityResult(is_valid=False, counter_model="No premises provided", confidence=0.0).to_dict()

        syllogism_result = self._check_syllogism(premises, conclusion)
        if syllogism_result is not None:
            return syllogism_result.to_dict()

        return ValidityResult(
            is_valid=False,
            counter_model="Non-syllogism validity checking requires Z3 formula parsing (not yet implemented for natural language)",
            confidence=0.0,
        ).to_dict()

    def detect_contradiction(self, formulas: list[str]) -> dict[str, Any]:
        if len(formulas) < 2:
            return {"has_contradiction": False, "confidence": 0.0}

        if self._has_syllogistic_contradiction(formulas):
            return {"has_contradiction": True, "confidence": 0.95}

        if self._has_negation_pair(formulas):
            return {"has_contradiction": True, "confidence": 0.95}

        return self._check_z3_contradiction(formulas)

    def _has_syllogistic_contradiction(self, formulas: list[str]) -> bool:
        parsed = [pf for f in formulas if (pf := self._parse_syllogism_form(f))]
        for i in range(len(parsed)):
            for j in range(i + 1, len(parsed)):
                a, b = parsed[i], parsed[j]
                if (a[0], b[0]) in {("all", "no"), ("no", "all")} and a[1] == b[1] and a[2] == b[2]:
                    return True
        return False

    def _has_negation_pair(self, formulas: list[str]) -> bool:
        normalized: set[str] = set()
        for formula in formulas:
            f = formula.strip().lower()
            if f.startswith("not "):
                body = f[4:]
                if body in normalized:
                    return True
                normalized.add(f)
            else:
                if f"not {f}" in normalized:
                    return True
                normalized.add(f)
        return False

    @staticmethod
    def _check_z3_contradiction(formulas: list[str]) -> dict[str, Any]:
        try:
            from z3 import Bool, Not, Solver, unsat
        except ImportError:
            return {"has_contradiction": False, "confidence": 0.0}

        try:
            solver = Solver()
            seen: dict[str, int] = {}
            for formula in formulas:
                f = formula.strip().lower()
                if f.startswith("not "):
                    body = f[4:]
                    if body in seen:
                        solver.add(Bool(f"f{seen[body]}"))
                        solver.add(Not(Bool(f"f{seen[body]}")))
                        break
                    idx = len(seen)
                    seen[f] = idx
                    solver.add(Not(Bool(f"f{idx}")))
                else:
                    if f in seen:
                        continue
                    idx = len(seen)
                    seen[f] = idx
                    solver.add(Bool(f"f{idx}"))

            result = solver.check()
            if result == unsat:
                return {"has_contradiction": True, "confidence": 0.95}
            return {"has_contradiction": False, "confidence": 0.7}
        except Exception:
            return {"has_contradiction": False, "confidence": 0.0}
