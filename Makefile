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

.PHONY: build
build:
	uv build

.PHONY: publish
publish:
	uv publish

.PHONY: install
install:
	uv add python-sanity

.PHONE: pre-release
pre-release:
	uv version --bump $(BUMP)
	git add pyproject.toml
	git commit -m "Bump version to $(version) (pre-release)"

.PHONY: release
release:
	uv version --bump patch
	git add pyproject.toml
	git commit -m "Bump version to $(version) (release)"
	uv publish

.PHONY: clean
clean:
	ruff clean
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete -o -type d -name .mypy_cache -delete
	rm -rf build
