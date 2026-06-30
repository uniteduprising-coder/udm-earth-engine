.PHONY: test lint run verify
test: ; set PYTHONPATH=src&& py -3 -m pytest tests/ -q
lint: ; py -3 -m ruff check src tests 2>nul || echo ruff optional
run: ; set PYTHONPATH=src&& py -3 -m earth.main
verify: ; bash scripts/verify-harness.sh