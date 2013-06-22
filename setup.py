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
    'packages': [
        "charmhelpers",
        "charmhelpers.core",
        "charmhelpers.fetch",
        "charmhelpers.payload",
        "charmhelpers.contrib",
        "charmhelpers.contrib.charmhelpers",
        "charmhelpers.contrib.charmsupport",
        "charmhelpers.contrib.saltstack",
        "charmhelpers.contrib.hahelpers",
        "charmhelpers.contrib.jujugui",
    ],
    'scripts': [
        "bin/contrib/charmsupport/charmsupport",
        "bin/contrib/saltstack/salt-call",
    ],
    'license': "Affero GNU Public License v3",
    'long_description': open('README.txt').read(),
}


if __name__ == '__main__':
    setup(**SETUP)
