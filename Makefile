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

typecheck:
	$(PYTHON) -m mypy $(SRC)

check: lint typecheck test

clean:
	rm -rf .coverage htmlcov/ .mypy_cache/ .ruff_cache/ .pytest_cache/
	rm -rf *.egg-info dist/ build/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
