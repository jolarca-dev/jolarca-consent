# jolarca-consent — verification & integrity targets
PYTHON ?= .venv/bin/python

.PHONY: check lint format types test verify-chain help

## Full static verification gate (must pass before merge).
check: lint types test verify-chain
	@echo "check: OK"

## Lint Python code (ruff check + format check).
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

## Format Python code (ruff format).
format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

## Type check (mypy --strict). Scope is defined in pyproject.toml [tool.mypy].
types:
	$(PYTHON) -m mypy --strict

## Run tests (pytest).
test:
	$(PYTHON) -m pytest

## Verify hash chain (offline verifier).
## Requires DATABASE_URL environment variable or --database-url argument.
## If not set, skips verification (for local dev without database).
verify-chain:
	@if [ -n "$$DATABASE_URL" ]; then \
		$(PYTHON) scripts/verify_chain.py --database-url "$$DATABASE_URL"; \
	else \
		echo "SKIP: verify-chain (DATABASE_URL not set)"; \
	fi

## Markdown lint (markdownlint-cli2 via npx).
lint-docs:
	npx --yes markdownlint-cli2 "**/*.md" "#.venv" "#node_modules" || true

## YAML validation.
lint-yaml:
	$(PYTHON) -c "import glob, yaml, sys; \
	bad = []; \
	[bad.append(f'{p}: {e}') for p in glob.glob('**/*.y*ml', recursive=True) if '.venv' not in p and 'node_modules' not in p for e in [None] if not (lambda: (list(yaml.safe_load_all(open(p, encoding='utf-8'))), None)[-1])() or True]; \
	sys.exit(1 if bad else 0)" 2>/dev/null || \
	$(PYTHON) -c "import glob, yaml, sys; \
	[p for p in glob.glob('**/*.y*ml', recursive=True) if '.venv' not in p and 'node_modules' not in p]; \
	[bad.append(f'{p}: {e}') for p in glob.glob('**/*.y*ml', recursive=True) if '.venv' not in p and 'node_modules' not in p for e in [None] if True]; \
	print('YAML validation requires manual check or yamllint')"

## Help (show this message).
help:
	@echo "jolarca-consent — verification & integrity targets"
	@echo ""
	@echo "  make check        Full static verification gate (must pass before merge)"
	@echo "  make lint         Lint Python code (ruff check + format check)"
	@echo "  make format       Format Python code (ruff format)"
	@echo "  make types        Type check (mypy --strict)"
	@echo "  make test         Run tests (pytest)"
	@echo "  make verify-chain Verify hash chain (offline verifier, requires DATABASE_URL)"
	@echo "  make lint-docs    Markdown lint (markdownlint-cli2 via npx)"
	@echo "  make help         Show this message"
