# Hacking on charmhelpers

## Run testsuite (tox method)

CAUTION:  the charm-helpers library has some unit tests which do unsavory things
such as making real, unmocked calls out to sudo foo, juju binaries, and perhaps
other things.  This is not ideal for a number of reasons.  One of those reasons
is that it pollutes the test runner (your) system.

The current recommendation for testing locally is to do so in a fresh bionic
(18.04) lxc container.  This is because charmhelpers supports at least bionic
and later Ubuntu distros.

The fresh Bionic lxc system container will need to have the following packages
installed in order to satisfy test runner dependencies:

    sudo apt install git bzr tox libapt-pkg-dev python3-dev build-essential juju -y

The tests can be executed as follows:

    tox -e pep8
    tox -e py3

## Test it in a charm

Use following instructions to build a charm that uses your own development branch of
charmhelpers.

Step 1: Make sure your version of charmhelpers is recognised as the latest version by
by appending `dev0` to the version number in the `VERSION` file.

Step 2: Create an override file `override-wheelhouse.txt` that points to your own
charmhelpers branch. *The format of this file is the same as pip's
[`requirements.txt`](https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format)
file.

    # Override charmhelpers by the version found in folder
    -e /path/to/charmhelpers
    # Or point it to a github repo with
    -e git+https://github.com/<myuser>/charm-helpers#egg=charmhelpers

Step 3: Build the charm specifying the override file. *You might need to install the
candidate channel of the charm snap*

    charm build <mycharm> -w wheelhouse-overrides.txt

Now when you deploy your charm, it will use your own branch of charmhelpers.

*Note: If you want to verify this or change the charmhelpers code on a built
charm, get the path of the installed charmhelpers by running following command.*

    python3 -c "import charmhelpers; print(charmhelpers.__file__)"


# Hacking on Docs

Install html doc dependencies:

```bash
sudo apt-get install python3-flake8 python3-shelltoolbox python3-tempita \
python3-nose python3-mock python3-testtools python3-jinja2 python3-coverage \
python3-git python3-netifaces python3-netaddr python3-pip zip
```

To build the html documentation:

```bash
make docs
```

To browse the html documentation locally:

```bash
make docs
cd docs/_build/html
python3 -m SimpleHTTPServer 8765
# point web browser to http://localhost:8765
```

To build and upload package and doc updates to PyPI:

```bash
make release
# note: if the package version already exists on PyPI
# this command will upload doc updates only
```

# PyPI Package and Docs

The published package and docs currently live at:

    https://pypi.python.org/pypi/charmhelpers
    http://pythonhosted.org/charmhelpers/
