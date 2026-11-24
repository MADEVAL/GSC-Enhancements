.PHONY: check validate lint compile test smoke install-list dry-run

check: validate lint compile test smoke install-list dry-run

validate:
	python tests/validate_skill.py

lint:
	@command -v ruff >/dev/null 2>&1 && ruff check . || echo "ruff not installed; skipping"

compile:
	python -m compileall -q skills/gsc-enhancements install.py

test:
	python -m unittest discover -s tests -p "test_*.py"

smoke:
	python skills/gsc-enhancements/scripts/analyze_export.py analyze --input tests/fixtures/queries.csv --min-impressions 100 --json > /dev/null

install-list:
	python install.py --list

dry-run:
	python install.py --target project --dry-run
