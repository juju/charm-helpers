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
        "charmhelpers.contrib.openstack.ha",
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
    'license': "Apache 2.0 (ASL)",
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
