import re
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from aicophilosopher.domain.services.config import Config

CROSS_TRADITIONAL_MAP: dict[str, dict[str, list[str]]] = {
    "mind": {
        "analytic": ["mind", "consciousness", "qualia"],
        "continental": ["geist", "dasein", "subjectivity"],
        "philosophy_of_technology": ["computational cognition", "technological mediation", "extended mind"],
        "philosophy_of_mathematics": ["computability", "formal system", "undecidability"],
        "software_architecture": ["computational model", "state machine", "agent"],
        "model_theory": ["interpretation", "satisfaction", "model"],
    },
    "computation": {
        "analytic": ["computation", "Turing", "functionalism", "algorithm"],
        "continental": ["technics", "enframing", "technological rationality"],
        "philosophy_of_technology": ["computational turn", "digital ontology", "algorithmic governance"],
        "philosophy_of_mathematics": ["Church-Turing", "recursive function", "computability theory"],
        "software_architecture": ["software design", "architectural pattern", "abstraction layer"],
        "model_theory": ["finite model", "descriptive complexity", "logical framework"],
    },
    "abstraction": {
        "analytic": ["abstraction", "universal", "concept", "nominalism"],
        "continental": ["idealisation", "reduction", "essence"],
        "philosophy_of_technology": ["abstraction layer", "interface", "black box"],
        "philosophy_of_mathematics": ["abstract structure", "category theory", "isomorphism"],
        "software_architecture": ["information hiding", "modularity", "separation of concerns"],
        "model_theory": ["abstract model", "elementary equivalence", "categoricity"],
    },
    "model": {
        "analytic": ["model", "representation", "simulation", "idealisation"],
        "continental": ["model", "paradigm", "episteme"],
        "philosophy_of_science": ["scientific model", "theoretical model", "idealisation"],
        "philosophy_of_technology": ["computational model", "software model", "simulation"],
        "software_architecture": ["domain model", "reference architecture", "design pattern"],
        "model_theory": ["model-theoretic", "semantics", "satisfaction relation"],
    },
    "truth": {
        "analytic": ["truth", "correspondence", "coherence", "pragmatism"],
        "continental": ["aletheia", "unconcealment", "truth-event"],
        "philosophy_of_mathematics": ["logical truth", "formal proof", "Gödel"],
        "philosophy_of_science": ["scientific truth", "verisimilitude", "empirical adequacy"],
        "model_theory": ["Tarski", "semantic truth", "validity"],
    },
    "correctness": {
        "analytic": ["correctness", "rightness", "normativity"],
        "software_architecture": ["formal verification", "type safety", "Hoare logic", "model checking"],
        "philosophy_of_mathematics": ["proof", "validity", "soundness"],
        "philosophy_of_science": ["falsification", "confirmation", "testing"],
    },
    "proof": {
        "analytic": ["proof", "argument", "demonstration", "justification"],
        "continental": ["phenomenological description", "hermeneutic evidence", "genealogy"],
        "philosophy_of_mathematics": ["formal proof", "derivation", "incompleteness", "consistency"],
        "software_architecture": ["formal verification", "type checking", "static analysis"],
        "model_theory": ["completeness", "compactness", "Löwenheim-Skolem"],
    },
    "design": {
        "analytic": ["design", "teleology", "function", "purpose"],
        "continental": ["design", "enframing", "technological intentionality"],
        "philosophy_of_technology": ["design ethics", "value-sensitive design", "technological mediation"],
        "software_architecture": ["architectural design", "design pattern", "architectural decision"],
        "philosophy_of_science": ["experimental design", "methodology", "research programme"],
    },
}


def _generate_expanded_queries(query: str, traditions: list[str] | None) -> list[str]:
    queries: list[str] = [query]
    if not traditions:
        return queries
    lower_q = query.lower().strip()
    for term, mapping in CROSS_TRADITIONAL_MAP.items():
        if re.search(rf"\b{re.escape(term)}\b", lower_q):
            for t in traditions:
                expanded_terms = mapping.get(t, [])
                for et in expanded_terms:
                    expanded = re.sub(rf"\b{re.escape(term)}\b", et, query, count=1)
                    if expanded != query and expanded not in queries:
                        queries.append(expanded)
            break
    for t in traditions:
        trad_terms = CROSS_TRADITIONAL_MAP.get(lower_q, {}).get(t, [])
        for tt in trad_terms:
            if tt not in queries:
                queries.append(tt)
    return queries


SHORT_TRADITION_KEYWORDS: dict[str, list[str]] = {}

LONG_TRADITION_KEYWORDS: dict[str, list[str]] = {
    "analytic": ["quine", "kripke", "possible world", "counterfactual", "proposition", "truth condition", "logical form"],
    "continental": ["phenomenolog", "existential", "hermeneutic", "deconstruction", "foucault", "deleuze", "derrida", "heidegger"],
    "philosophy_of_technology": ["technological mediation", "technological determinism", "human-computer interaction", "digital ethics", "postphenomenology"],
    "philosophy_of_science": ["scientific realism", "paradigm", "falsification", "theory-laden", "underdetermination", "research programme"],
    "philosophy_of_mathematics": ["foundations of mathematics", "Gödel", "incompleteness", "category theory", "structuralism", "formalism", "intuitionism"],
    "software_architecture": ["software design", "design pattern", "modularity", "refactoring", "technical debt", "separation of concerns"],
    "model_theory": ["model-theoretic", "Tarski", "formal semantics", "completeness theorem", "compactness", "Löwenheim-Skolem"],
}


def _assign_tradition_tag(result: dict[str, Any], traditions_hint: list[str] | None) -> str:
    if traditions_hint and len(traditions_hint) == 1:
        return traditions_hint[0]
    text = (result.get("title", "") + " " + result.get("abstract", "")).lower()

    for tradition, keywords in LONG_TRADITION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return tradition

    for tradition, keywords in SHORT_TRADITION_KEYWORDS.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", text):
                return tradition

    return traditions_hint[0] if traditions_hint else "analytic"


# Source availability labels exposed to CLI / agent results.
# live          — real external API is wired and may return results
# stub          — known placeholder; returns no live literature
# offline       — external search disabled (consent / config)
# unimplemented — not wired at all (no results, no fabricated URLs)
SOURCE_STATUS_LIVE = "live"
SOURCE_STATUS_STUB = "stub"
SOURCE_STATUS_OFFLINE = "offline"
SOURCE_STATUS_UNIMPLEMENTED = "unimplemented"

# Capability map independent of consent. Consent only flips live → offline.
SOURCE_CAPABILITIES: dict[str, str] = {
    "semantic_scholar": SOURCE_STATUS_LIVE,
    "arxiv": SOURCE_STATUS_LIVE,
    "philpapers": SOURCE_STATUS_STUB,
    "sep": SOURCE_STATUS_STUB,
    "iep": SOURCE_STATUS_UNIMPLEMENTED,
}


class ConsentGate:
    def __init__(self, config: Config | None = None, allow_external: bool = False) -> None:
        self.config = config or Config()
        self._consent_given = allow_external

    def grant(self) -> None:
        self._consent_given = True

    def revoke(self) -> None:
        self._consent_given = False

    def require(self) -> bool:
        if self.config.allow_external_search:
            return True
        return self._consent_given


class SearchTool:
    def __init__(self, allow_external: bool = False, config: Config | None = None) -> None:
        self.config = config or Config()
        self.consent = ConsentGate(self.config, allow_external=allow_external)
        self._timeout = 15.0

    def get_source_statuses(self) -> dict[str, str]:
        """Return per-source availability for UX honesty (live/stub/offline/unimplemented)."""
        external_allowed = self.consent.require()
        statuses: dict[str, str] = {}
        for name, capability in SOURCE_CAPABILITIES.items():
            if capability == SOURCE_STATUS_LIVE and not external_allowed:
                statuses[name] = SOURCE_STATUS_OFFLINE
            else:
                statuses[name] = capability
        return statuses

    async def _try_semantic_scholar(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={"query": query, "limit": min(limit, 100), "fields": "title,url,year,authors,externalIds,abstract"},
                )
                resp.raise_for_status()
                data = resp.json()
                papers = []
                for p in data.get("data", []):
                    authors = [a.get("name", "") for a in p.get("authors", []) if a.get("name")]
                    papers.append({
                        "title": p.get("title", ""),
                        "authors": authors,
                        "year": p.get("year"),
                        "url": p.get("url", ""),
                        "abstract": p.get("abstract", ""),
                        "source": "semantic_scholar",
                        "source_status": SOURCE_STATUS_LIVE,
                        "relevance_score": 0.0,
                    })
                return papers
            except Exception:
                return []

    async def _try_arxiv(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        terms = query.strip().split()
        search_query = "all:" + " AND all:".join(terms)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.get(
                    "https://export.arxiv.org/api/query",
                    params={"search_query": search_query, "start": 0, "max_results": min(limit, 50)},
                    headers={"Accept": "application/xml"},
                )
                resp.raise_for_status()
                root = ET.fromstring(resp.text)
                ns = {"a": "http://www.w3.org/2005/Atom"}
                papers = []
                for entry in root.findall("a:entry", ns):
                    title_el = entry.find("a:title", ns)
                    summary_el = entry.find("a:summary", ns)
                    published_el = entry.find("a:published", ns)
                    link_el = entry.find("a:link", ns)
                    authors: list[str] = []
                    for author_el in entry.findall("a:author", ns):
                        name_el = author_el.find("a:name", ns)
                        if name_el is not None and name_el.text:
                            authors.append(name_el.text)
                    title_text = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""
                    pub_text = published_el.text if published_el is not None and published_el.text else None
                    summary_text = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""
                    papers.append({
                        "title": title_text,
                        "authors": authors,
                        "year": pub_text[:4] if pub_text else None,
                        "url": link_el.attrib.get("href", "") if link_el is not None else "",
                        "abstract": summary_text,
                        "source": "arxiv",
                        "source_status": SOURCE_STATUS_LIVE,
                        "relevance_score": 0.0,
                    })
                return papers
            except Exception:
                return []

    async def search(
        self,
        query: str,
        traditions: list[str] | None = None,
        **kwargs: object,
    ) -> list[dict[str, Any]]:
        if not self.consent.require():
            return self._offline_results(query, traditions)

        expanded = _generate_expanded_queries(query, traditions)
        seen_titles: set[str] = set()
        results: list[dict[str, Any]] = []

        for eq in expanded[:5]:
            papers = await self._try_semantic_scholar(eq, limit=5)
            for p in papers:
                title = p.get("title", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    p["tradition_tag"] = _assign_tradition_tag(p, traditions)
                    abstract_len = len(p.get("abstract", ""))
                    score = min(round(0.5 + (abstract_len / 1000) * 0.3, 2), 1.0) if p.get("abstract") else 0.3
                    p["relevance_score"] = score
                    p.setdefault("source_status", SOURCE_STATUS_LIVE)
                    results.append(p)

        for eq in expanded[:3]:
            papers = await self._try_arxiv(eq, limit=5)
            for p in papers:
                title = p.get("title", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    p["tradition_tag"] = _assign_tradition_tag(p, traditions)
                    abstract_len = len(p.get("abstract", ""))
                    score = min(round(0.5 + (abstract_len / 1000) * 0.3, 2), 1.0) if p.get("abstract") else 0.3
                    p["relevance_score"] = score
                    p.setdefault("source_status", SOURCE_STATUS_LIVE)
                    results.append(p)

        return results[:20]

    async def query_semantic_scholar(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        if not self.consent.require():
            return []
        papers = await self._try_semantic_scholar(query)
        return [dict(p) for p in papers]

    async def query_arxiv(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        if not self.consent.require():
            return []
        papers = await self._try_arxiv(query)
        return [dict(p) for p in papers]

    async def query_philpapers(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        """PhilPapers is a stub: no live API is wired. Returns no results.

        Callers should consult ``get_source_statuses()`` (status: stub) rather
        than treating an empty list as a successful empty search.
        """
        _ = query, kwargs
        return []

    async def query_sep(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        """SEP has no public search API; do not fabricate plato.stanford.edu URLs.

        Returns an empty list. Status is disclosed via ``get_source_statuses()``
        as stub so UX can show that SEP is not connected.
        """
        _ = query, kwargs
        return []

    def _offline_results(self, query: str, traditions: list[str] | None = None) -> list[dict[str, Any]]:
        return [
            {
                "title": f"[Offline] {query} — philosophical analysis",
                "authors": ["Local Philosopher"],
                "year": 2024,
                "abstract": f"An analysis of {query} across multiple philosophical traditions.",
                "source": "offline",
                "source_status": SOURCE_STATUS_OFFLINE,
                "tradition_tag": traditions[0] if traditions else "analytic",
                "relevance_score": 0.7,
            },
            {
                "title": f"[Offline] The concept of {query} in cross-traditional perspective",
                "authors": ["Local Philosopher"],
                "year": 2025,
                "abstract": f"Examining {query} through analytic and continental frameworks.",
                "source": "offline",
                "source_status": SOURCE_STATUS_OFFLINE,
                "tradition_tag": traditions[1] if traditions and len(traditions) > 1 else "continental",
                "relevance_score": 0.6,
            },
        ]

    def set_consent(self, granted: bool) -> None:
        if granted:
            self.consent.grant()
        else:
            self.consent.revoke()
