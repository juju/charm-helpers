# Hacking on charmhelpers


## Run testsuite

    make test

Run `make` without arguments for more options.

## Use it in a charm

Use following instructions to build a charm that uses your own branch of
charmhelpers.

Create an override file `override-wheelhouse.txt` that points to your own
charmhelpers branch.

    -e git+https://github.com/<myuser>/charm-helpers#egg=charmhelpers

Build the charm specifying the override file. *You might need to install the
candidate channel of the charm snap*

    charm build <mycharm> -w wheelhouse-overrides.txt

Now when you deploy your charm, it will use your own branch of charmhelpers.

*Note: If you want to verify this or change the charmhelpers code on a built
charm, get the path of the installed charmhelpers by running following command.*

    python3 -c "import charmhelpers; print(charmhelpers.__file__)"


# Hacking on Docs

Install html doc dependencies:

```bash
sudo apt install python-netifaces
```

To build the html documentation:

```bash
make docs
```

To browse the html documentation locally:

```bash
make docs
cd docs/_build/html
python -m SimpleHTTPServer 8765
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
