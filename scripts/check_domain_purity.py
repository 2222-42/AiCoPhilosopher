#!/usr/bin/env python3
"""Verify domain/ imports only stdlib + pydantic."""

import ast
import sys
from pathlib import Path

ALLOWED_IMPORTS = {
    "abc",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "functools",
    "json",
    "math",
    "operator",
    "os",
    "pathlib",
    "re",
    "string",
    "textwrap",
    "typing",
    "uuid",
    "collections",
    "itertools",
    "pydantic",
    "pydantic.functional_validators",
    "pydantic.functional_serializers",
    "typing_extensions",
    "pydantic_settings",
    "aicophilosopher",
}

ALLOWED_TOP_LEVELS = {imp.split(".")[0] for imp in ALLOWED_IMPORTS}

ROOT = Path(__file__).resolve().parent.parent
DOMAIN_DIR = ROOT / "src" / "aicophilosopher" / "domain"


def check_file(filepath: Path) -> list[str]:
    errors = []
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read())
    except SyntaxError as e:
        return [f"  Syntax error in {filepath}: {e}"]

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split(".")[0]
                full_import = alias.name
                if full_import not in ALLOWED_IMPORTS and top_level not in ALLOWED_TOP_LEVELS:
                    errors.append(f"  {filepath.relative_to(ROOT)}: import '{alias.name}' not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] not in ALLOWED_TOP_LEVELS:
                if node.module not in ALLOWED_IMPORTS:
                    errors.append(f"  {filepath.relative_to(ROOT)}: import from '{node.module}' not allowed")

    return errors


def main() -> int:
    if not DOMAIN_DIR.exists():
        print(f"Domain directory not found: {DOMAIN_DIR}")
        return 1

    all_errors = []
    for pyfile in sorted(DOMAIN_DIR.rglob("*.py")):
        errors = check_file(pyfile)
        all_errors.extend(errors)

    if all_errors:
        print("Domain purity violations found:")
        for err in all_errors:
            print(err)
        return 1
    else:
        print("All domain files are pure (stdlib + pydantic only).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
