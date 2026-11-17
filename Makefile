.PHONY: test lint

# Tests are plain unittest classes, so `python -m unittest discover -s tests -t .` also works.
test:
	uv run pytest -q

lint:
	uv run ruff check .
