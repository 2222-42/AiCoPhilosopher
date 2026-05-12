---
agent: speckit.constitution
---

## Constitution Principles for AI Co-Philosopher

## 1. Code Quality

- All code MUST be clear, readable, and maintainable, following PEP8 (for Python) or the idiomatic style of the chosen language.
- Use descriptive names for variables, functions, classes, and modules.
- Avoid code duplication; prefer modular, reusable components.
- All public functions and classes MUST have docstrings or documentation comments.
- Use type annotations wherever possible.
- Handle errors gracefully and log failures for debugging and auditability.

## 2. Testing Standards

- All core logic MUST be covered by automated tests (unit and integration).
- Tests MUST be deterministic and reproducible.
- Use mocks/stubs for external services in tests; do not require network access for core test suite.
- All bug fixes MUST include a regression test.
- Test coverage MUST be measured and reported for every release.

## 3. MVP Focus

- Prioritize delivery of a working MVP that meets the minimum requirements: Project Coordinator, Literature Search, Synthesis Agent, persistent workspace, and terminal interface.
- Defer non-essential features and optimizations until after MVP is stable.
- MVP MUST be fully functional without any external orchestration layers.
- All MVP features MUST be documented with clear usage instructions.

## 4. Continuous Improvement

- Encourage regular code reviews and refactoring.
- Solicit user feedback early and often to guide improvements.
- Maintain a changelog and versioning for all releases.
