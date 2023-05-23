.DEFAULT_GOAL := help

.PHONY: help
help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install dependencies
	flit install --deps develop --symlink

.PHONY: lint
lint: ## Run code linters
	black --check ninja tests
	isort --check ninja tests
	flake8 ninja tests
	mypy ninja

.PHONY: fmt format
fmt format: ## Run code formatters
	black ninja tests
	isort ninja tests

.PHONY: test
test: ## Run tests
	pytest .

.PHONY: test-cov
test-cov: ## Run tests with coverage
	pytest --cov=ninja --cov-report term-missing tests

.PHONY: test-cov-server
test-cov-server: ## Run tests with coverage and open the server to see coverage details
	-pytest --cov=ninja --cov-fail-under=0 --cov-report html:htmlcov tests
	cd htmlcov && python -m http.server 8001 --bind 0.0.0.0

.PHONY: docs
docs: ## Serve documentation locally
	pip install -r docs/requirements.txt
	cd docs && mkdocs serve -a localhost:8090
