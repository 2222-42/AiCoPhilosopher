from typing import Any

import httpx

from aicophilosopher.domain.services.config import Config

CROSS_TRADITIONAL_MAP: dict[str, dict[str, list[str]]] = {
    "mind": {
        "analytic": ["mind", "consciousness", "qualia"],
        "continental": ["geist", "dasein", "subjectivity"],
        "buddhist": ["citta", "manas", "vijnana", "mind"],
        "confucian": ["xin", "heart-mind"],
        "daoist": ["xin", "heart-mind"],
    },
    "self": {
        "analytic": ["self", "personal identity", "ego"],
        "continental": ["ipseity", "selfhood", "subject"],
        "buddhist": ["anatta", "anatman", "no-self", "skandha"],
        "confucian": ["self-cultivation", "junzi"],
        "daoist": ["wu-wei", "ziran"],
    },
    "knowledge": {
        "analytic": ["knowledge", "epistemology", "justification"],
        "continental": ["savoir", "connaissance", "episteme"],
        "buddhist": ["pramana", "jnana", "prajna"],
        "confucian": ["zhi", "learning", "rectification of names"],
        "daoist": ["zhi", "knowing", "mysterious knowledge"],
    },
    "ethics": {
        "analytic": ["ethics", "morality", "metaethics"],
        "continental": ["ethos", "ethics of existence", "responsibility"],
        "buddhist": ["sila", "karuna", "upaya"],
        "confucian": ["ren", "yi", "li", "xiao"],
        "daoist": ["de", "wu-wei ethics", "naturalness"],
    },
    "reality": {
        "analytic": ["metaphysics", "ontology", "reality"],
        "continental": ["being", "ontology", "difference"],
        "buddhist": ["sunyata", "dharma", "tathata"],
        "confucian": ["li", "qi", "taiji"],
        "daoist": ["dao", "qi", "wu", "you"],
    },
    "free will": {
        "analytic": ["free will", "determinism", "compatibilism", "libertarianism"],
        "continental": ["freedom", "autonomy", "choice", "existentialism"],
        "buddhist": ["karma", "pratityasamutpada", "volition", "cetana"],
        "confucian": ["ming", "tian", "self-determination"],
        "daoist": ["ziran", "wu-wei", "spontaneity"],
    },
    "truth": {
        "analytic": ["truth", "correspondence", "coherence", "pragmatism"],
        "continental": ["aletheia", "unconcealment", "truth-event"],
        "buddhist": ["satya", "dharma", "two truths"],
        "confucian": ["cheng", "sincerity"],
        "daoist": ["dao", "naturalness"],
    },
}


def _generate_expanded_queries(query: str, traditions: list[str] | None) -> list[str]:
    queries: list[str] = [query]
    if not traditions:
        return queries
    lower_q = query.lower().strip()
    for term, mapping in CROSS_TRADITIONAL_MAP.items():
        if term in lower_q:
            for t in traditions:
                expanded_terms = mapping.get(t, [])
                for et in expanded_terms:
                    expanded = query.lower().replace(term, et)
                    if expanded != lower_q and expanded not in queries:
                        queries.append(expanded)
            break
    for t in traditions:
        trad_terms = CROSS_TRADITIONAL_MAP.get(lower_q, {}).get(t, [])
        for tt in trad_terms:
            if tt not in queries:
                queries.append(tt)
    return queries


def _assign_tradition_tag(result: dict[str, Any], traditions_hint: list[str] | None) -> str:
    if traditions_hint and len(traditions_hint) == 1:
        return traditions_hint[0]
    text = (result.get("title", "") + " " + result.get("abstract", "")).lower()
    tradition_keywords = {
        "analytic": ["quine", "kripke", "possible world", "counterfactual", "proposition", "truth condition", "logical form"],
        "continental": ["phenomenolog", "existential", "hermeneutic", "deconstruction", "foucault", "deleuze", "derrida", "heidegger"],
        "buddhist": ["buddha", "sutra", "karma", "nirvana", "sunyata", "dependent origination", "vipassana"],
        "confucian": ["confucius", "mencius", "ren", "li", "junzi", "filial"],
        "daoist": ["dao", "wu wei", "zhuangzi", "laozi", "qi", "naturalness"],
    }
    for tradition, keywords in tradition_keywords.items():
        for kw in keywords:
            if kw in text:
                return tradition
    return traditions_hint[0] if traditions_hint else "analytic"


class ConsentGate:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self._consent_given = False

    def check(self) -> bool:
        if not self.config.allow_external_search:
            return False
        return True

    def grant(self) -> None:
        self._consent_given = True

    def require(self) -> bool:
        if self.check():
            return True
        return self._consent_given


class SearchTool:
    def __init__(self, allow_external: bool = False, config: Config | None = None) -> None:
        self.allow_external = allow_external
        self.config = config or Config()
        self.consent = ConsentGate(self.config)
        self._timeout = 15.0

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
                        "relevance_score": 0.0,
                    })
                return papers
            except Exception:
                return []

    async def _try_arxiv(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        search_query = "+AND+".join(query.strip().split())
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.get(
                    "http://export.arxiv.org/api/query",
                    params={"search_query": f"all:{search_query}", "start": 0, "max_results": min(limit, 50)},
                    headers={"Accept": "application/xml"},
                )
                resp.raise_for_status()
                import xml.etree.ElementTree as ET
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

        for eq in expanded[:3]:
            papers = await self._try_semantic_scholar(eq, limit=5)
            for p in papers:
                title = p.get("title", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    p["tradition_tag"] = _assign_tradition_tag(p, traditions)
                    p["relevance_score"] = round(0.5 + (len(p.get("abstract", "")) / 1000) * 0.3, 2) if p.get("abstract") else 0.3
                    results.append(p)

        if not results:
            for eq in expanded[:2]:
                papers = await self._try_arxiv(eq, limit=5)
                for p in papers:
                    title = p.get("title", "")
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        p["tradition_tag"] = _assign_tradition_tag(p, traditions)
                        p["relevance_score"] = round(0.5, 2)
                        results.append(p)

        return results[:20]

    async def query_semantic_scholar(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        if not self.consent.require():
            return []
        papers = await self._try_semantic_scholar(query)
        result_list: list[dict[str, object]] = [dict(p) for p in papers]
        return result_list

    async def query_arxiv(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        if not self.consent.require():
            return []
        papers = await self._try_arxiv(query)
        result_list: list[dict[str, object]] = [dict(p) for p in papers]
        return result_list

    async def query_philpapers(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        return [
            {"title": f"PhilPapers result: {query}", "source": "philpapers", "relevance_score": 0.5},
        ]

    async def query_sep(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        encoded = query.replace(" ", "+")
        return [
            {"title": f"SEP entry: {query}", "url": f"https://plato.stanford.edu/entries/{encoded}/", "source": "sep", "relevance_score": 0.8},
        ]

    def _offline_results(self, query: str, traditions: list[str] | None = None) -> list[dict[str, Any]]:
        return [
            {
                "title": f"[Offline] {query} — philosophical analysis",
                "authors": ["Local Philosopher"],
                "year": 2024,
                "abstract": f"An analysis of {query} across multiple philosophical traditions.",
                "source": "offline",
                "tradition_tag": traditions[0] if traditions else "analytic",
                "relevance_score": 0.7,
            },
            {
                "title": f"[Offline] The concept of {query} in cross-traditional perspective",
                "authors": ["Local Philosopher"],
                "year": 2025,
                "abstract": f"Examining {query} through analytic and continental frameworks.",
                "source": "offline",
                "tradition_tag": traditions[1] if traditions and len(traditions) > 1 else "continental",
                "relevance_score": 0.6,
            },
        ]

    def set_consent(self, granted: bool) -> None:
        if granted:
            self.consent.grant()
        self.allow_external = granted
