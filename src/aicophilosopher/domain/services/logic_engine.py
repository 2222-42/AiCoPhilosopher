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


SYLLOGISM_PATTERNS = [
    {
        "pattern": r"All\s+(\w+)\s+are\s+(\w+)",
        "conclusion_pattern": r"All\s+(\w+)\s+are\s+(\w+)",
        "check": lambda matches: (
            len(matches) == 3
            and matches[0][1] == matches[2][1]
            and matches[0][0] == matches[1][0]
            and matches[1][1] == matches[2][0]
        ),
    },
]


class LogicEngine:
    def _check_syllogism(self, premises: list[str], conclusion: str) -> ValidityResult | None:
        parsed_premises = []
        for premise in premises:
            match = re.match(r"All\s+(\w+)\s+are\s+(\w+)", premise.strip())
            if match:
                parsed_premises.append(("all", match.group(1), match.group(2)))
                continue
            match = re.match(r"No\s+(\w+)\s+are\s+(\w+)", premise.strip())
            if match:
                parsed_premises.append(("no", match.group(1), match.group(2)))
                continue
            match = re.match(r"Some\s+(\w+)\s+are\s+(\w+)", premise.strip())
            if match:
                parsed_premises.append(("some", match.group(1), match.group(2)))
                continue
            return None

        concl_match = re.match(r"(All|No|Some)\s+(\w+)\s+are\s+(\w+)", conclusion.strip())
        if not concl_match:
            return None

        concl_type = concl_match.group(1).lower()
        concl_s = concl_match.group(2)
        concl_p = concl_match.group(3)

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

        try:
            from z3 import And, Bool, Implies, Not, Solver, sat
        except ImportError:
            return ValidityResult(is_valid=False, counter_model="Z3 not available for non-syllogism check", confidence=0.0).to_dict()

        try:
            solver = Solver()
            p_vars = {}
            for i, premise in enumerate(premises):
                var = Bool(f"p{i}")
                p_vars[f"p{i}"] = var
                solver.add(var)

            c_var = Bool("c")
            implication = Implies(And(*p_vars.values()), c_var)
            solver.add(Not(implication))

            result = solver.check()
            if result == sat:
                model = solver.model()
                return ValidityResult(
                    is_valid=False,
                    counter_model=str(model),
                    confidence=0.3,
                ).to_dict()
            else:
                return ValidityResult(
                    is_valid=True,
                    confidence=0.9,
                ).to_dict()
        except Exception as e:
            return ValidityResult(is_valid=False, counter_model=str(e), confidence=0.0).to_dict()

    def detect_contradiction(self, formulas: list[str]) -> dict[str, Any]:
        try:
            from z3 import Bool, Solver, unsat
        except ImportError:
            return {"has_contradiction": False, "confidence": 0.0}

        if len(formulas) < 2:
            return {"has_contradiction": False, "confidence": 0.0}

        try:
            solver = Solver()
            for i in range(len(formulas)):
                var = Bool(f"f{i}")
                solver.add(var)

            result = solver.check()
            if result == unsat:
                return {"has_contradiction": True, "confidence": 0.95}
            return {"has_contradiction": False, "confidence": 0.7}
        except Exception:
            return {"has_contradiction": False, "confidence": 0.0}
