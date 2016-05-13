# Makefile for packaging and testing this app. Should follow make contract
# at https://github.counsyl.com/techops/lambda-ci#make-build

PACKAGE_NAME=pedant
TEST_OUTPUT?=nosetests.xml

ifdef TOX_ENV
	TOX_ENV_FLAG := -e $(TOX_ENV)
else
	TOX_ENV_FLAG :=
endif

.PHONY: default
default:
	python setup.py check build

VENV_DIR?=.venv
VENV_ACTIVATE=$(VENV_DIR)/bin/activate
WITH_VENV=. $(VENV_ACTIVATE);

.PHONY: venv
venv: $(VENV_ACTIVATE)

$(VENV_ACTIVATE): requirements*.txt
	test -f $@ || virtualenv --python=python2.7 $(VENV_DIR)
	$(WITH_VENV) pip install -r requirements-setup.txt --index-url=${PIP_INDEX_URL}
	$(WITH_VENV) pip install -e . --index-url=${PIP_INDEX_URL}
	$(WITH_VENV) pip install -r requirements-dev.txt  --index-url=${PIP_INDEX_URL}
	touch $@

develop: venv
	$(WITH_VENV) python setup.py develop
	

.PHONY: setup
setup: ##[setup] Run an arbitrary setup.py command
setup: venv
ifdef ARGS
 	$(WITH_VENV) python setup.py ${ARGS}
else
	@echo "Won't run 'python setup.py ${ARGS}' without ARGS set."
endif

.PHONY: clean
clean:
	python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg*/
	rm -rf __pycache__/
	rm -f MANIFEST
	rm -f $(TEST_OUTPUT)
	find $(PACKAGE_NAME) -type f -name '*.pyc' -delete
	rm -rf nosetests* "${TEST_OUTPUT}" coverage .coverage .coverage*


.PHONY: teardown
teardown:
	rm -rf $(VENV_DIR)

.PHONY: lint
lint: venv
	$(WITH_VENV) flake8 -v $(PACKAGE_NAME)/

.PHONY: unit-test
unit-test: venv
	$(WITH_VENV) \
	coverage erase; \
	tox -v $(TOX_ENV_FLAG); \
	status=$$?; \
	exit $$status;

.PHONY: test
test: venv unit-test

# Distribution

VERSION=$(shell $(WITH_VENV) python setup.py --version | sed 's/\([0-9]*\.[0-9]*\.[0-9]*\).*$$/\1/')

.PHONY: tag
tag: ##[distribution] Tag the release.
tag: venv
	echo "Tagging version as ${VERSION}"
	git tag -a ${VERSION} -m "Version ${VERSION}"
	# We won't push changes or tags here allowing the pipeline to do that, so we don't accidentally do that locally.

# Note that the dist target depends on fullname in order to cache the full name of the package.
# This prevents log messages from appearing when calling setup.py --fullname later in the
# gocd python-package-template
.PHONY: dist
dist: venv fullname
	$(WITH_VENV) python setup.py sdist

.PHONY: sdist
sdist: dist
	@echo "runs dist"

.PHONY: version
version:
	@echo ${VERSION}
	
.PHONY: fullname
fullname:
	python setup.py --fullname
