.PHONY: clean build gen-docs docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean:  ## Clean all build, python, and testing files
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	rm -fr .tox/
	rm -fr .coverage
	rm -fr coverage.xml
	rm -fr htmlcov/
	rm -fr .pytest_cache
	rm -fr .mypy_cache

build: ## Run tox / run tests and lint
	tox

gen-docs: ## Generate Sphinx HTML documentation, including API docs
	rm -f docs/cdp_backend*.rst
	rm -f docs/modules.rst
	rm -f docs/_static/cdp_database_diagram.*
	create_cdp_database_uml \
		-o docs/_static/cdp_database_diagram.dot
	dot \
		-T png \
		-o docs/_static/cdp_database_diagram.png docs/_static/cdp_database_diagram.dot
	create_cdp_ingestion_models_doc \
		-t docs/ingestion_models.template \
		-o docs/ingestion_models.md
	create_cdp_transcript_model_doc \
		-t docs/transcript_model.template \
		-o docs/transcript_model.md
	create_cdp_event_gather_flow_viz \
		-o docs/_static/cdp_event_gather_flow_{ftype}.png
	sphinx-apidoc -o docs/ cdp_backend **/tests/
	$(MAKE) -C docs html

docs: ## Generate Sphinx HTML documentation, including API docs, and serve to browser
	make gen-docs
	$(BROWSER) docs/_build/html/index.html

run-rand-event-pipeline: ## Run event pipeline using random event gen
	run_cdp_event_gather \
		example-configs/random-event.json \
		--parallel

run-min-event-pipeline: ## Run event pipeline using minimal event def
	run_cdp_event_gather \
		example-configs/min-event.json

run-filled-event-pipeline: ## Run event pipeline using the filled event
	run_cdp_event_gather \
		example-configs/filled-event.json \
		--parallel