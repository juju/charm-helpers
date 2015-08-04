from distutils.core import setup
import os


version_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'VERSION'))
with open(version_file) as v:
    VERSION = v.read().strip()


SETUP = {
    'name': "charmhelpers",
    'version': VERSION,
    'author': "Ubuntu Developers",
    'author_email': "ubuntu-devel-discuss@lists.ubuntu.com",
    'url': "https://code.launchpad.net/charm-helpers",
    'install_requires': [
        'netaddr',
        'PyYAML',
        'Tempita',
        'Jinja2',
        'six',
    ],
    'packages': [
        "charmhelpers",
        "charmhelpers.cli",
        "charmhelpers.core",
        "charmhelpers.core.services",
        "charmhelpers.fetch",
        "charmhelpers.payload",
        "charmhelpers.contrib",
        "charmhelpers.contrib.amulet",
        "charmhelpers.contrib.ansible",
        "charmhelpers.contrib.benchmark",
        "charmhelpers.contrib.charmhelpers",
        "charmhelpers.contrib.charmsupport",
        "charmhelpers.contrib.database",
        "charmhelpers.contrib.hahelpers",
        "charmhelpers.contrib.network",
        "charmhelpers.contrib.network.ovs",
        "charmhelpers.contrib.openstack",
        "charmhelpers.contrib.openstack.amulet",
        "charmhelpers.contrib.openstack.files",
        "charmhelpers.contrib.openstack.templates",
        "charmhelpers.contrib.peerstorage",
        "charmhelpers.contrib.python",
        "charmhelpers.contrib.saltstack",
        "charmhelpers.contrib.ssl",
        "charmhelpers.contrib.storage",
        "charmhelpers.contrib.storage.linux",
        "charmhelpers.contrib.templating",
        "charmhelpers.contrib.unison",
    ],
    'scripts': [
        "bin/chlp",
        "bin/contrib/charmsupport/charmsupport",
        "bin/contrib/saltstack/salt-call",
    ],
    'license': "Affero GNU Public License v3",
    'long_description': open('README.txt').read(),
    'description': 'Helpers for Juju Charm development',
}

try:
    from sphinx_pypi_upload import UploadDoc
    SETUP['cmdclass'] = {'upload_sphinx': UploadDoc}
except ImportError:
    pass

if __name__ == '__main__':
    setup(**SETUP)
