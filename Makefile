PROJECT=charmhelpers
PYTHON := /usr/bin/env python3
SUITE=unstable
TESTS=tests/

all:
	@echo "make source - Create source package"
	@echo "make sdeb - Create debian source package"
	@echo "make deb - Create debian package"
	@echo "make clean"
	@echo "make userinstall - Install locally"
	@echo "make docs - Build html documentation"
	@echo "make release - Build and upload package and docs to PyPI"
	@echo "make test"

sdeb: source
	scripts/build source

deb: source
	scripts/build

source: setup.py
	scripts/update-revno
	python3 setup.py sdist

clean:
	-python3 setup.py clean
	rm -rf build/ MANIFEST
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	rm -rf dist/*
	rm -rf .venv3
	(which dh_clean && dh_clean) || true

userinstall:
	scripts/update-revno
	python3 setup.py install --user


.venv3:
	dpkg-query -W -f='$${status}' gcc python3-dev python-virtualenv python3-apt 2>/dev/null | grep --invert-match "not-installed" || sudo apt-get install -y python3-dev python-virtualenv python3-apt
	virtualenv .venv3 --python=python3 --system-site-packages
	.venv3/bin/pip install -U pip
	.venv3/bin/pip install -I -r test-requirements.txt

# Note we don't even attempt to run tests if lint isn't passing.
test: lint test3
	@echo OK

test3:
	@echo Starting Py3 tests...
	.venv3/bin/nosetests -s --nologcapture tests/

ftest: lint
	@echo Starting fast tests...
	.venv3/bin/nosetests --attr '!slow' --nologcapture tests/

lint: .venv3
	@echo Checking for Python syntax...
	@.venv3/bin/flake8 --ignore=E402,E501,W504 $(PROJECT) $(TESTS) tools/ \
	    && echo Py3 OK

docs:
	- [ -z "`dpkg -l | grep python3-sphinx`" ] && sudo apt-get install python-sphinx -y
	- [ -z "`dpkg -l | grep python3-pip`" ] && sudo apt-get install python-pip -y
	- [ -z "`pip list | grep -i sphinx-pypi-upload`" ] && sudo pip install sphinx-pypi-upload
	- [ -z "`pip list | grep -i sphinx_rtd_theme`" ] && sudo pip install sphinx_rtd_theme
	cd docs && make html && cd -
.PHONY: docs

release: docs
	$(PYTHON) setup.py sdist upload upload_sphinx

build: test lint docs
