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

lint:
	@echo Checking for Python syntax...
	@flake8 --ignore=E123,E501 $(PROJECT) $(TESTS) && echo OK

build: test lint
