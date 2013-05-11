from distutils.core import setup
import os


version_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'VERSION'))
with open(version_file) as v:
    VERSION = v.read().strip()


SETUP = {
    'name': "charmsupport",
    'version': VERSION,
    'author': "Matthew Wedgwood",
    'author_email': "matthew.wedgwood@ubuntu.com",
    'url': "https://code.launchpad.net/charmsupport",
    'packages': ["charmsupport"],
    'scripts': ["bin/charmsupport"],
    'license': "Lesser GNU Public License v3",
    'long_description': open('README.txt').read(),
}


if __name__ == '__main__':
    setup(**SETUP)
