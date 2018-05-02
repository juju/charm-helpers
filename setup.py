# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from setuptools import setup, find_packages


version_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'VERSION'))
with open(version_file) as v:
    VERSION = v.read().strip()


SETUP = {
    'name': "charmhelpers",
    'version': VERSION,
    'author': "Charmers",
    'author_email': "juju@lists.ubuntu.com",
    'url': "https://github.com/juju/charm-helpers",
    'install_requires': [
        'netaddr',
        'PyYAML',
        'Tempita',
        'Jinja2',
        'six',
    ],
    'packages': find_packages(exclude=('tests', 'tests.*', 'tools', 'tools.*')),
    'scripts': [
        "bin/chlp",
        "bin/contrib/charmsupport/charmsupport",
        "bin/contrib/saltstack/salt-call",
    ],
    'license': "Apache 2.0 (ASL)",
    'long_description': open('README.rst').read(),
    'description': 'Helpers for Juju Charm development',
}

try:
    from sphinx_pypi_upload import UploadDoc
    SETUP['cmdclass'] = {'upload_sphinx': UploadDoc}
except ImportError:
    pass

if __name__ == '__main__':
    setup(**SETUP)
