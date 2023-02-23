# list all available commands
default:
  just --list

# clean all build, python, and lint files
clean:
	rm -fr build
	rm -fr docs/_build
	rm -fr dist
	rm -fr .eggs
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	rm -fr .coverage*
	rm -fr coverage.xml
	rm -fr htmlcov
	rm -fr .pytest_cache
	rm -fr .mypy_cache
	rm -fr index
	rm -fr abc123-cdp_*-transcript.json
	rm -fr test.err
	rm -fr test.out
	rm -fr *-thumbnail.*
	rm -fr test-clipped.*

# install with all deps
install:
	pip install --no-cache-dir -e '.[pipeline,functions,lint,test,docs,dev]'
	pip install --no-cache-dir --force-reinstall --upgrade \
		'faster-whisper @ git+https://github.com/guillaumekln/faster-whisper.git'

# lint, format, and check all files
lint:
	pre-commit run --all-files

# run library tests
test-library:
	pytest --cov-report xml --cov-report html --cov=cdp_backend cdp_backend/tests

# run functions tests
test-functions:
	pytest cdp_backend/infrastructure/gcloud-functions/

# run lint and then run tests
build:
	just lint
	just test-library
	just test-functions

# generate Sphinx HTML documentation
generate-docs:
	rm -f docs/cdp_backend*.rst
	rm -f docs/modules.rst
	rm -f docs/_static/cdp_database_diagram.*
	create_cdp_database_uml \
		-o docs/_static/cdp_database_diagram.dot
	dot \
		-T jpg \
		-o docs/_static/cdp_database_diagram.jpg docs/_static/cdp_database_diagram.dot
	create_cdp_ingestion_models_doc \
		-t docs/ingestion_models.template \
		-o docs/ingestion_models.md
	create_cdp_transcript_model_doc \
		-t docs/transcript_model.template \
		-o docs/transcript_model.md
	sphinx-apidoc -o docs cdp_backend **/tests
	python -msphinx "docs" "docs/_build"


# Generate project URI for browser opening
# We replace here to handle windows paths
# Windows paths are normally `\` separated but even in the browser they use `/`
# https://stackoverflow.com/a/61991869
project_uri := if "os_family()" == "unix" {
	justfile_directory()
} else {
	replace(justfile_directory(), "\\", "/")
}

# generate Sphinx HTML documentation and serve to browser
serve-docs:
	just generate-docs
	python -mwebbrowser -t "file://{{project_uri}}/docs/_build/index.html"

# tag a new version
tag-for-release version:
	git tag -a "{{version}}" -m "{{version}}"
	echo "Tagged: $(git tag --sort=-version:refname| head -n 1)"

# release a new version
release:
	git push --follow-tags

# update this repo using latest cookiecutter-py-package
update-from-cookiecutter:
	pip install cookiecutter
	cookiecutter gh:evamaxfield/cookiecutter-py-package --config-file .cookiecutter.yaml --no-input --overwrite-if-exists --output-dir ..