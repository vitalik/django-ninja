.DEFAULT_GOAL := help

.PHONY: help
help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install dependencies
	uv sync

.PHONY: lint
lint: ## Run code linters
	uv run ruff format --check ninja tests
	uv run ruff check ninja tests
	uv run mypy ninja

.PHONY: fmt format
fmt format: ## Run code formatters
	uv run ruff format ninja tests
	uv run ruff check --fix ninja tests

.PHONY: test
test: ## Run tests
	uv run pytest .

.PHONY: test-cov
test-cov: ## Run tests with coverage
	uv run pytest --cov=ninja --cov-report term-missing tests

.PHONY: docs
docs: ## Serve documentation locally
	cd docs && uv run --with-requirements requirements.txt mkdocs serve -a localhost:8090
