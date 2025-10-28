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


.PHONY: build
build:
	uv build

.PHONY: publish
publish:
	uv publish

.PHONY: format
format:
	$(ruff-format)
	if ! git diff --quiet; then \
		git add $(projectpath); \
		git commit -m "style: format code via make format-commit"; \
	fi

.PHONY: install
install:
	uv add python-sanity

.PHONY: version-bump
version-bump:
	uv version --bump $(BUMP)
	git add pyproject.toml
	git commit -m "Bump version to $(version) ($(BUMP))"

.PHONY: release
release: clean format version-bump build publish

