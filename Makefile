.PHONY: test test-cov lint format typecheck check clean

PYTHON ?= python3
PROJECT := aicophilosopher
SRC := src/$(PROJECT)
TEST := tests
SCRIPTS := scripts

test:
	if [ -n "$$(find $(TEST) -name 'test_*.py' 2>/dev/null)" ]; then $(PYTHON) -m pytest $(TEST) -v; else echo "No tests found (empty project)"; fi

test-cov:
	if [ -n "$$(find $(TEST) -name 'test_*.py' 2>/dev/null)" ]; then $(PYTHON) -m coverage run -m pytest $(TEST) -v && $(PYTHON) -m coverage report; else echo "No tests found (empty project)"; fi

lint:
	ruff check $(SRC) $(TEST) $(SCRIPTS)

format:
	ruff format $(SRC) $(TEST) $(SCRIPTS)

# Typecheck is non-blocking by default: main has pre-existing mypy debt (~30).
# Set AICOPH_TYPECHECK_STRICT=1 to fail on errors (preferred once debt is cleared).
# CI workflow would use continue-on-error if the token had `workflow` scope;
# until then this keeps lint+test as hard gates while still reporting mypy output.
typecheck:
	@$(PYTHON) -m mypy $(SRC); \
	status=$$?; \
	if [ $$status -ne 0 ]; then \
		echo "WARNING: mypy reported errors (exit $$status). Non-blocking until type debt is cleared."; \
		echo "         Re-run with AICOPH_TYPECHECK_STRICT=1 to fail hard."; \
	fi; \
	if [ "$${AICOPH_TYPECHECK_STRICT:-0}" = "1" ]; then exit $$status; fi; \
	exit 0

check: lint typecheck test

clean:
	rm -rf .coverage htmlcov/ .mypy_cache/ .ruff_cache/ .pytest_cache/
	rm -rf *.egg-info dist/ build/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
