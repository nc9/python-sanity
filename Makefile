.DEFAULT_GOAL := all
.SHELLFLAGS = -e
UPGRADE_ARGS ?= --upgrade
projectname = sanity-python
projectpath = sanity

# tools
ruff-check = uv run ruff check $(projectpath)
ruff-format = uv run ruff format $(projectpath)
ruff-lint = uv run ruff lint $(projectpath)
pyright = uv run pyright -v .venv $(projectpath)
BUMP ?= dev

.PHONY: clean
clean:
	ruff clean
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete -o -type d -name .mypy_cache -delete
	rm -rf build
