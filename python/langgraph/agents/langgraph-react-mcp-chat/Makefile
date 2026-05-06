.PHONY: all format lint test tests test_watch integration_tests docker_tests docker_unit_tests docker_integration_tests docker_build help extended_tests

# Default target executed when no arguments are given to make.
all: help

# Define a variable for the test file path.
TEST_FILE ?= tests/unit_tests/

test:
	python -m pytest $(TEST_FILE)

tests: test

integration_tests:
	python -m pytest tests/integration_tests/

test_watch:
	python -m ptw --snapshot-update --now . -- -vv tests/unit_tests

test_profile:
	python -m pytest -vv tests/unit_tests/ --profile-svg

extended_tests:
	python -m pytest --only-extended $(TEST_FILE)

######################
# DOCKER TESTS
######################

docker_build:
	docker compose -f docker-compose.test.yml build

docker_tests: docker_build
	docker compose -f docker-compose.test.yml run --rm test

docker_unit_tests: docker_build
	docker compose -f docker-compose.test.yml run --rm unit-test

docker_integration_tests: docker_build
	docker compose -f docker-compose.test.yml run --rm integration-test

######################
# LINTING AND FORMATTING
######################

# Define a variable for Python and notebook files.
PYTHON_FILES=src/
MYPY_CACHE=.mypy_cache
lint format: PYTHON_FILES=.
lint_diff format_diff: PYTHON_FILES=$(shell git diff --name-only --diff-filter=d main | grep -E '\.py$$|\.ipynb$$')
lint_package: PYTHON_FILES=src
lint_tests: PYTHON_FILES=tests
lint_tests: MYPY_CACHE=.mypy_cache_test

lint lint_diff lint_package lint_tests:
	python -m ruff check .
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff format $(PYTHON_FILES) --diff
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff check --select I $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || python -m mypy --strict $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || mkdir -p $(MYPY_CACHE) && python -m mypy --strict $(PYTHON_FILES) --cache-dir $(MYPY_CACHE)

format format_diff:
	ruff format $(PYTHON_FILES)
	ruff check --select I --fix $(PYTHON_FILES)

spell_check:
	codespell --toml pyproject.toml

spell_fix:
	codespell --toml pyproject.toml -w

######################
# HELP
######################

help:
	@echo '----'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo 'test                         - run unit tests'
	@echo 'tests                        - alias for test'
	@echo 'integration_tests            - run integration tests'
	@echo 'test TEST_FILE=<test_file>   - run all tests in file'
	@echo 'test_watch                   - run unit tests in watch mode'
	@echo 'spell_check                  - check spelling'
	@echo 'spell_fix                    - fix spelling issues'
	@echo 'docker_build                 - build the test Docker image'
	@echo 'docker_tests                 - run all tests in Docker'
	@echo 'docker_unit_tests            - run unit tests in Docker'
	@echo 'docker_integration_tests     - run integration tests in Docker'

