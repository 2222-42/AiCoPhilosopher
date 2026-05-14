"""Domain-aware philosophical query strategy (§3.6).

Staged pipeline:
  1. Keyword-based Core Domain detection (fast, offline-safe)
  2. LLM-based semantic query expansion (cheap model)
  3. Tradition-aware query routing for deep analysis (expensive model)
"""

from aicophilosopher.domain.services.core_domains import CoreDomains
from aicophilosopher.ports.llm_port import LLMPort

_EXPANSION_PROMPT = """You are a philosophical query expansion engine. Given a user question,
generate 3-5 philosophically scoped sub-queries that explore different dimensions.

User question: {query}

Relevant philosophical domains: {domains}

Instructions:
1. Generate sub-queries that connect the user's question to each relevant domain
2. Include ontological, epistemological, and methodological perspectives
3. Consider how different philosophical traditions would approach the question
4. Bridge between traditions where possible (e.g., analytic rigor + continental context)

Return ONLY the sub-queries, one per line, each prefixed with "- ". No other text."""


class PhilosophicalQueryStrategy:
    """Domain-aware query strategy with staged LLM pipeline.

    Detects core philosophical domains via keyword matching, then uses
    a cheap LLM for semantic expansion. The resulting queries are routed
    to tradition-aware deep analysis through the expensive-model path.
    """

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def detect_domains(self, query: str) -> list[dict[str, object]]:
        """Detect core philosophical domains relevant to the query.

        Uses CoreDomains keyword-based detection (fast, no LLM call).
        Returns domains sorted by match strength descending.
        """
        return CoreDomains.detect(query)

    def classify_traditions(self, query: str) -> list[str]:
        """Classify which traditions are relevant for this query.

        Maps detected domains to their tradition keys, ensuring
        tradition-aware routing downstream.
        """
        domains = self.detect_domains(query)
        traditions: list[str] = []
        seen: set[str] = set()
        for d in domains:
            key = str(d["key"])
            if key not in seen:
                seen.add(key)
                traditions.append(key)
            sub_traditions = CoreDomains.get_sub_traditions(key)
            for st in sub_traditions:
                if st not in seen:
                    seen.add(st)
                    traditions.append(st)
        return traditions

    async def expand(self, query: str, max_queries: int = 5) -> list[str]:
        """Semantically expand a user query into philosophically scoped sub-queries.

        Uses LLM (cheap model path) for semantic expansion. Falls back to
        domain-based keyword expansion if LLM is unavailable.

        Args:
            query: The user's original question or topic.
            max_queries: Maximum number of expanded queries to return.

        Returns:
            List of philosophically scoped query strings.
        """
        domains = self.detect_domains(query)
        if not domains:
            return [query]

        domain_names = ", ".join(str(d["display_name"]) for d in domains[:3])
        prompt = _EXPANSION_PROMPT.format(query=query, domains=domain_names)

        try:
            result = await self._llm.generate(prompt, temperature=0.3)
            expanded = self._parse_expanded_queries(result.text, max_queries)
            if expanded:
                return expanded
        except (OSError, ConnectionError, RuntimeError):
            pass

        return self._fallback_expand(query, domains, max_queries)

    def _parse_expanded_queries(self, text: str, max_queries: int) -> list[str]:
        queries: list[str] = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                q = stripped[2:].strip()
                if q and q not in queries:
                    queries.append(q)
                    if len(queries) >= max_queries:
                        break
        return queries

    def _fallback_expand(
        self,
        query: str,
        domains: list[dict[str, object]],
        max_queries: int,
    ) -> list[str]:
        expanded: list[str] = [query]
        for d in domains[: max_queries - 1]:
            display_name = str(d["display_name"])
            expanded.append(f"{display_name} perspective on: {query}")
        return expanded[:max_queries]

    async def plan_pipeline(self, query: str) -> dict[str, object]:
        """Plan a staged pipeline for the query.

        Returns a pipeline plan dict with stages:
          - stage1 (cheap): domain detection + query expansion
          - stage2 (expensive): tradition-aware deep queries
        """
        domains = self.detect_domains(query)
        traditions = self.classify_traditions(query)
        expanded = await self.expand(query)

        return {
            "original_query": query,
            "detected_domains": domains,
            "relevant_traditions": traditions,
            "expanded_queries": expanded,
            "stages": {
                "stage1_cheap": {
                    "action": "semantic_expansion",
                    "queries": [query],
                    "model_tier": "cheap",
                },
                "stage2_expensive": {
                    "action": "deep_analysis",
                    "queries": expanded,
                    "model_tier": "expensive",
                    "traditions": traditions,
                },
            },
        }
