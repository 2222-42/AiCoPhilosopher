
class CoreDomain:
    def __init__(
        self,
        key: str,
        display_name: str,
        priority: float,
        sub_traditions: list[str],
        expansion_terms: list[str],
        keywords: list[str],
        description: str = "",
    ) -> None:
        self.key = key
        self.display_name = display_name
        self.priority = priority
        self.sub_traditions = sub_traditions
        self.expansion_terms = expansion_terms
        self.keywords = keywords
        self.description = description

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "display_name": self.display_name,
            "priority": self.priority,
            "sub_traditions": self.sub_traditions,
            "expansion_terms": self.expansion_terms,
            "keywords": self.keywords,
            "description": self.description,
        }


class CoreDomains:
    _domains: dict[str, CoreDomain] = {}

    @classmethod
    def _ensure_initialized(cls) -> None:
        if cls._domains:
            return
        cls._domains = {
            "philosophy_of_mathematics": CoreDomain(
                key="philosophy_of_mathematics",
                display_name="Philosophy of Mathematics",
                priority=1.0,
                sub_traditions=[
                    "logicism",
                    "formalism",
                    "intuitionism",
                    "structuralism",
                    "fictionalism",
                    "platonism",
                ],
                expansion_terms=[
                    "mathematical objects",
                    "proof",
                    "foundations",
                    "set theory",
                    "category theory",
                    "abstraction",
                    "mathematical truth",
                    "ontology of numbers",
                ],
                keywords=[
                    "mathematics",
                    "math",
                    "number",
                    "proof",
                    "theorem",
                    "axiom",
                    "set",
                    "category",
                    "calculus",
                    "geometry",
                    "algebra",
                    "topology",
                    "problem",
                    "conjecture",
                    "unsolved",
                ],
                description="Ontology and epistemology of mathematical objects, truth, and practice",
            ),
            "logic": CoreDomain(
                key="logic",
                display_name="Logic",
                priority=0.95,
                sub_traditions=[
                    "classical_logic",
                    "modal_logic",
                    "many_valued_logic",
                    "relevance_logic",
                    "paraconsistent_logic",
                    "intuitionistic_logic",
                ],
                expansion_terms=[
                    "validity",
                    "soundness",
                    "logical consequence",
                    "formal system",
                    "inference",
                    "paradox",
                    "consistency",
                    "completeness",
                ],
                keywords=[
                    "logic",
                    "valid",
                    "sound",
                    "inference",
                    "paradox",
                    "contradiction",
                    "syllogism",
                    "proposition",
                    "predicate",
                    "modal",
                ],
                description="Formal reasoning, validity, logical systems, and paradoxes",
            ),
            "pragmatism": CoreDomain(
                key="pragmatism",
                display_name="Pragmatism",
                priority=0.85,
                sub_traditions=[
                    "classical_pragmatism",
                    "neo_pragmatism",
                    "linguistic_pragmatism",
                    "pragmatic_method",
                ],
                expansion_terms=[
                    "practical consequences",
                    "inquiry",
                    "truth as usefulness",
                    "community of inquiry",
                    "fallibilism",
                    "abduction",
                ],
                keywords=[
                    "pragmatic",
                    "practical",
                    "utility",
                    "inquiry",
                    "experimental",
                    "consequence",
                    "action",
                    "habit",
                    "belief",
                    "problem solving",
                ],
                description="Philosophical tradition emphasizing practical consequences and inquiry-based truth",
            ),
            "philosophy_of_science": CoreDomain(
                key="philosophy_of_science",
                display_name="Philosophy of Science",
                priority=0.95,
                sub_traditions=[
                    "logical_empiricism",
                    "scientific_realism",
                    "instrumentalism",
                    "constructive_empiricism",
                    "structural_realism",
                ],
                expansion_terms=[
                    "scientific method",
                    "theory",
                    "observation",
                    "experiment",
                    "causation",
                    "explanation",
                    "laws of nature",
                    "paradigm",
                ],
                keywords=[
                    "science",
                    "scientific",
                    "experiment",
                    "theory",
                    "observation",
                    "empirical",
                    "hypothesis",
                    "falsification",
                    "paradigm",
                    "model",
                ],
                description="Nature of scientific knowledge, method, explanation, and theory",
            ),
            "philosophy_of_technology": CoreDomain(
                key="philosophy_of_technology",
                display_name="Philosophy of Technology",
                priority=0.90,
                sub_traditions=[
                    "technological_determinism",
                    "social_construction_of_technology",
                    "postphenomenology",
                    "critical_theory_of_technology",
                ],
                expansion_terms=[
                    "technological mediation",
                    "artifact",
                    "design",
                    "agency",
                    "software",
                    "computation",
                    "algorithm",
                    "interface",
                ],
                keywords=[
                    "technology",
                    "tech",
                    "software",
                    "hardware",
                    "algorithm",
                    "digital",
                    "computation",
                    "design",
                    "artifact",
                    "tool",
                    "interface",
                    "AI",
                ],
                description="Philosophical analysis of technology, design, and mediation",
            ),
            "model_theory": CoreDomain(
                key="model_theory",
                display_name="Model Theory",
                priority=0.80,
                sub_traditions=[
                    "classical_model_theory",
                    "finite_model_theory",
                    "categorical_model_theory",
                    "applications_of_model_theory",
                ],
                expansion_terms=[
                    "interpretation",
                    "satisfaction",
                    "structure",
                    "embedding",
                    "elementary equivalence",
                    "definability",
                    "type",
                ],
                keywords=[
                    "model",
                    "structure",
                    "interpretation",
                    "satisfaction",
                    "definability",
                    "categoricity",
                    "Löwenheim",
                    "Skolem",
                    "compactness",
                ],
                description="Mathematical study of interpretation between formal languages and structures",
            ),
        }

    @classmethod
    def get(cls, key: str) -> dict[str, object] | None:
        cls._ensure_initialized()
        domain = cls._domains.get(key)
        if domain is None:
            return None
        return domain.to_dict()

    @classmethod
    def detect(cls, query: str) -> list[dict[str, object]]:
        cls._ensure_initialized()
        query_lower = query.lower()
        results: list[tuple[float, dict[str, object]]] = []
        for domain in cls._domains.values():
            score = 0.0
            matched: list[str] = []
            for keyword in domain.keywords:
                if keyword.lower() in query_lower:
                    score += 1.0 / len(domain.keywords)
                    matched.append(keyword)
            if matched:
                match_strength = round(min(score * domain.priority, 1.0), 4)
                results.append(
                    (
                        match_strength,
                        {
                            "key": domain.key,
                            "display_name": domain.display_name,
                            "match_strength": match_strength,
                            "matched_keywords": matched,
                        },
                    )
                )
        results.sort(key=lambda r: r[0], reverse=True)
        return [r[1] for r in results]

    @classmethod
    def list_all(cls) -> list[dict[str, object]]:
        cls._ensure_initialized()
        domains = sorted(cls._domains.values(), key=lambda d: d.priority, reverse=True)
        return [d.to_dict() for d in domains]

    @classmethod
    def get_expansion_terms(cls, key: str) -> list[str]:
        cls._ensure_initialized()
        domain = cls._domains.get(key)
        if domain is None:
            return []
        return list(domain.expansion_terms)

    @classmethod
    def get_sub_traditions(cls, key: str) -> list[str]:
        cls._ensure_initialized()
        domain = cls._domains.get(key)
        if domain is None:
            return []
        return list(domain.sub_traditions)

    @classmethod
    def get_all_keywords(cls) -> set[str]:
        cls._ensure_initialized()
        all_kw: set[str] = set()
        for domain in cls._domains.values():
            all_kw.update(domain.keywords)
        return all_kw
