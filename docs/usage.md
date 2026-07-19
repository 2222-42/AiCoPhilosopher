# Usage Guide — AI Co-Philosopher

A guided walkthrough for creating a philosophical research project from start to finish.

## Table of Contents

1. [Installation](#installation)
2. [Creating Your First Project](#creating-your-first-project)
3. [Clarifying Your Question](#clarifying-your-question)
4. [Running Workstreams](#running-workstreams)
5. [Reviewing and Steering](#reviewing-and-steering)
6. [Synthesizing Results](#synthesizing-results)
7. [Exporting Your Work](#exporting-your-work)

## Installation

See [QUICKSTART.md](QUICKSTART.md) for setup instructions.

## Creating Your First Project

Start with a philosophical question — it can be as vague as you like:

```bash
aicophilosopher new-project "What is abstraction?"
```

This creates a persistent workspace under
`~/.aicophilosopher/projects/<project_id>/`
(override with `AICOPH_WORKSPACE_DIR`) containing:
- `living_document.md` — your working paper
- `dialectical_history.jsonl` — complete argument history
- `hypotheses.jsonl` — all hypotheses with status
- `uncertainty_registry.json` — confidence scores
- `workstreams/` — per-workstream reports

## Clarifying Your Question

The Project Coordinator Agent will help refine your question through Socratic dialogue:

```bash
aicophilosopher refine-goal
```

The agent asks clarifying questions about:
- Which philosophical traditions are relevant?
- What methodology should be applied?
- What scope is appropriate?

Continue until the goal is approved. You can stop at any time.

## Running Workstreams

### Literature Search

```bash
aicophilosopher start-workstream literature_search
```

The agent searches PhilPapers, SEP, IEP, arXiv, and Semantic Scholar. Results include:
- Structured bibliography with BibTeX entries
- Tradition tags (analytic, continental, philosophy_of_technology, etc.)
- Cross-traditional bridge notes
- Relevance scores

### Concept Analysis

```bash
aicophilosopher start-workstream concept_analysis
```

Performs:
- Necessary vs sufficient condition analysis
- Distinction mapping (de re vs de dicto, a priori vs a posteriori)
- Thought experiment generation
- Conceptual genealogy

### Argumentation

```bash
aicophilosopher start-workstream argumentation
```

Reconstructs arguments in standard form:
- Premises + conclusion + inference rule
- Multiple competing positions across traditions
- Implicit assumptions identified
- Circularity detection

### Critical Review

```bash
aicophilosopher start-workstream critical_review
```

Evaluates arguments:
- Formal and informal fallacy detection with severity ratings
- Validity, soundness, and philosophical plausibility assessment
- Counter-argument generation
- Adversarial stress testing

### Cross-Traditional Comparison

```bash
aicophilosopher start-workstream cross_traditional
```

Or:

```bash
aicophilosopher compare-traditions "abstraction"
```

Compares concepts across traditions, identifies bridges and incommensurabilities.

## Reviewing and Steering

### Check Status

```bash
aicophilosopher status
```

Shows epistemic overview:
- Active workstreams and their progress
- Hypothesis counts by status
- Confidence score summary

### View Results

```bash
aicophilosopher show-document
aicophilosopher show-hypotheses
aicophilosopher show-dead-ends
```

### Steer Workstreams

```bash
aicophilosopher pause <workstream_id>
aicophilosopher resume <workstream_id>
aicophilosopher steer <workstream_id> "deepen analysis on abstraction layers"
```

### Add Notes

```bash
aicophilosopher add-note "Consider comparing with Husserl's eidetic reduction"
aicophilosopher add-note --attach-to hypothesis-3 "Needs more evidence"
```

## Synthesizing Results

```bash
aicophilosopher start-workstream synthesis
```

The Synthesis Agent merges all workstream outputs into the living document with:
- Consistent philosophical voice
- Margin annotations for every non-trivial claim
- Conflict flags for contradictory findings
- Synthesis confidence score

## Exporting Your Work

```bash
aicophilosopher export markdown   # Default
aicophilosopher export html       # For web publishing
aicophilosopher export latex      # For academic submission (deferred)
```

## Example Session

```bash
# Start a project
aicophilosopher new-project "Can machines think?"

# Refine the question
aicophilosopher refine-goal
# > Agent: Which traditions are most relevant? (analytic, continental, philosophy_of_technology)
# > You: analytic and philosophy_of_technology
# > Agent: Approved. Launching workstreams...

# Run workstreams
aicophilosopher start-workstream literature_search
aicophilosopher start-workstream concept_analysis
aicophilosopher start-workstream argumentation

# Review progress
aicophilosopher status
aicophilosopher show-hypotheses

# After review, synthesize
aicophilosopher start-workstream synthesis

# Export
aicophilosopher export markdown
```

## Offline Mode

All core features work without network access:

```bash
export AICOPH_ALLOW_EXTERNAL_SEARCH=false
aicophilosopher new-project "What is truth?"
```

Literature search will be limited to locally ingested PDFs (via `add note --attach`), but argumentation, concept analysis, critical review, and synthesis all function fully.

## Privacy

The AI Co-Philosopher is **local-first**. No project content, document text, notes, or uploaded files are transmitted to external services without your explicit consent. Literature search transmits only query terms (not project content) after your approval. See the [constitution](.specify/memory/constitution.md) for details.
