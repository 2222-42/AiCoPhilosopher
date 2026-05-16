"""Cross-traditional bridge notes (domain data).

Mapping of philosophical concepts to cross-tradition bridge descriptions.
Shared by LiteratureSearchAgent and CrossTraditionalComparisonAgent.
Domain-pure: no infrastructure or application imports.
"""

BRIDGE_NOTES: dict[str, dict[str, str]] = {
    "abstraction": {
        "analytic→philosophy_of_technology": "Analytic philosophy analyses abstraction as a formal operation; philosophy of technology examines how abstraction layers in software mediate human activity and embed normative commitments.",
        "analytic→philosophy_of_mathematics": "Analytic philosophy treats mathematical abstraction as removing properties to expose structure; software architecture treats abstraction as hiding implementation behind interfaces. These serve different epistemic purposes.",
        "philosophy_of_mathematics→software_architecture": "Mathematical abstraction discovers formal structure; software abstraction designs interfaces. Conflating the two risks treating design choices as mathematical necessities.",
        "philosophy_of_technology→software_architecture": "Technological mediation theory (Ihde, Verbeek) reveals how software abstraction is not neutral: each layer reshapes what users can perceive and do.",
    },
    "model": {
        "analytic→model_theory": "Analytic philosophy of science treats models as representations of target systems; model theory treats models as interpretations of formal languages. Both senses converge in scientific modelling but with different validity criteria.",
        "philosophy_of_science→software_architecture": "Scientific models aim at isomorphism with reality; software models aim at executable specification. The normative standards differ: empirical adequacy vs behavioural correctness.",
        "model_theory→software_architecture": "Model-theoretic semantics (Tarski) provides a formal framework applicable to software specification languages (algebraic specification, abstract state machines), but the engineering constraints add pragmatic criteria beyond formal satisfiability.",
    },
    "computation": {
        "analytic→philosophy_of_mathematics": "Turing's analysis of computation bridges analytic philosophy of mind (functionalism) and philosophy of mathematics (computability theory). The Church-Turing thesis has implications for both domains.",
        "philosophy_of_technology→software_architecture": "Computational thinking transforms how we understand cognition, social organisation, and agency. Software architecture embodies assumptions about what computation is and what it can formalise.",
    },
    "proof": {
        "analytic→philosophy_of_mathematics": "Mathematical proof is a social-epistemic practice involving understanding; formal proof is a syntactic derivation. Both are relevant to philosophical argumentation with different epistemic standards.",
        "philosophy_of_mathematics→software_architecture": "Formal verification in software (model checking, theorem proving) draws on proof theory but applies it to systems with state, time, and concurrency—extending classical proof concepts.",
    },
    "correctness": {
        "analytic→software_architecture": "Analytic philosophy distinguishes necessary and sufficient conditions; software correctness requires formal specification of both. The gap between specification and implementation mirrors the gap between concept and object in analytic epistemology.",
        "philosophy_of_science→software_architecture": "Scientific falsification (Popper) and software testing (falsifying hypotheses about program behaviour) share structural parallels, but the normative aims differ: scientific truth vs operational reliability.",
    },
    "truth": {
        "analytic→model_theory": "Tarski's semantic conception of truth (truth in a model) provides a formal framework for understanding correspondence and its limits. Model-theoretic truth is relative to interpretation—a lesson relevant to philosophical pluralism.",
        "continental→philosophy_of_technology": "Heideggerian aletheia (unconcealment) and technological enframing (Gestell) offer a non-correspondence account of truth-as-disclosure relevant to understanding how software systems shape what is intelligible.",
    },
    "design": {
        "analytic→philosophy_of_technology": "Analytic aesthetics and philosophy of technology converge on the concept of design: both treat artefacts as embodying intentions and values that merit philosophical analysis.",
        "philosophy_of_technology→software_architecture": "Software design embeds ontological assumptions (what entities exist in the system, how they relate) and normative commitments (what counts as good structure). These deserve philosophical scrutiny.",
    },
}
