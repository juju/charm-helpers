PROJECT=charmhelpers
PYTHON := /usr/bin/env python
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

sdeb: source
	scripts/build source

deb: source
	scripts/build

source: setup.py
	scripts/update-revno
	python setup.py sdist

clean:
	python setup.py clean
	rm -rf build/ MANIFEST
	find . -name '*.pyc' -delete
	rm -rf dist/*
	dh_clean

userinstall:
	scripts/update-revno
	python setup.py install --user

test:
	@echo Starting tests...
	@$(PYTHON) /usr/bin/nosetests --nologcapture tests/

ftest:
	@echo Starting fast tests...
	@$(PYTHON) /usr/bin/nosetests --attr '!slow' --nologcapture tests/

lint:
	@echo Checking for Python syntax...
	@flake8 --ignore=E123,E501 $(PROJECT) $(TESTS) && echo OK

docs:
	- [ -z "`dpkg -l | grep python-sphinx`" ] && sudo apt-get install python-sphinx -y
	- [ -z "`dpkg -l | grep python-pip`" ] && sudo apt-get install python-pip -y
	- [ -z "`pip list | grep -i sphinx-pypi-upload`" ] && sudo pip install sphinx-pypi-upload
	cd docs && make html && cd -
.PHONY: docs

release: docs
	$(PYTHON) setup.py sdist upload upload_sphinx

build: test lint docs
