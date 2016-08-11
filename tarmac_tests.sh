#!/bin/sh
# How the tests are run in Jenkins by Tarmac

set -e

pkgs='python-flake8 python-shelltoolbox python-tempita python-nose python-mock python-testtools python-jinja2 python-coverage python-git python-netifaces python-netaddr python-pip zip'
if ! dpkg -s $pkgs 2>/dev/null >/dev/null ; then
    echo "Required packages are missing. Please ensure that the missing packages are installed."
    echo "Run: sudo apt-get install $pkgs"
    exit 1
fi

make build
