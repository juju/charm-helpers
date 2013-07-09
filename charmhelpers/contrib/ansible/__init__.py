# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
"""Charm Helpers ansible - declare the state of your machines."""
import os
import subprocess
import yaml

import charmhelpers.core.host
import charmhelpers.core.hookenv


charm_dir = os.environ.get('CHARM_DIR', '')


def install_ansible_support(from_ppa=True):
    """Installs the ansible package.

    By default it is installed from the PPA [1] linked from
    the ansible website [2].

    [1] https://launchpad.net/~rquillo/+archive/ansible
    [2] http://www.ansibleworks.com/docs/gettingstarted.html#ubuntu-and-debian

    If from_ppa is false, you must ensure that the package is available
    from a configured repository.
    """
    if from_ppa:
        subprocess.check_call([
            '/usr/bin/add-apt-repository',
            '--yes',
            'ppa:rquillo/ansible',
        ])
        subprocess.check_call(['/usr/bin/apt-get', 'update'])
    charmhelpers.core.host.apt_install('ansible')
