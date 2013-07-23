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
import charmhelpers.fetch


charm_dir = os.environ.get('CHARM_DIR', '')
ansible_hosts_path = '/etc/ansible/hosts'


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
        charmhelpers.fetch.add_source('ppa:rquillo/ansible')
        charmhelpers.core.host.apt_update(fatal=True)
    charmhelpers.core.host.apt_install('ansible')
    with open(ansible_hosts_path, 'w+') as hosts_file:
        hosts_file.write('localhost ansible_connection=local')


def apply_playbook(playbook):
    subprocess.check(['ansible-playbook', '-c', 'local', playbook])
