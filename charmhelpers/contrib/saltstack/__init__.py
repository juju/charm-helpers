"""Charm Helpers saltstack - declare the state of your machines.

This helper enables you to declare your machine state, rather than
program it procedurally (and have to test each change to your procedures).
Your install hook can be as simple as:

{{{
from charmhelpers.contrib.saltstack import (
    install_salt_support,
    update_machine_state,
)


def install():
    install_salt_support()
    update_machine_state('machine_states/dependencies.yaml')
    update_machine_state('machine_states/installed.yaml')
}}}

and won't need to change (nor will its tests) when you change the machine
state.

It's using a python package called salt-minion which allows various formats for
specifying resources, such as:

{{{
/srv/{{ basedir }}:
    file.directory:
        - group: ubunet
        - user: ubunet
        - require:
            - user: ubunet
        - recurse:
            - user
            - group

ubunet:
    group.present:
        - gid: 1500
    user.present:
        - uid: 1500
        - gid: 1500
        - createhome: False
        - require:
            - group: ubunet
}}}

The docs for all the different state definitions are at:
    http://docs.saltstack.com/ref/states/all/


TODO:
  * Add test helpers which will ensure that machine state definitions
    are functionally (but not necessarily logically) correct (ie. getting
    salt to parse all state defs.
  * Add a link to a public bootstrap charm example / blogpost.
  * Find a way to obviate the need to use the grains['charm_dir'] syntax
    in templates.
"""
# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
import os
import subprocess
import yaml

import charmhelpers.core.host
import charmhelpers.core.hookenv


charm_dir = os.environ.get('CHARM_DIR', '')
salt_grains_path = '/etc/salt/grains'


def install_salt_support(from_ppa=True):
    """Installs the salt-minion helper for machine state.

    By default the salt-minion package is installed from
    the saltstack PPA. If from_ppa is False you must ensure
    that the salt-minion package is available in the apt cache.
    """
    if from_ppa:
        subprocess.check_call([
            '/usr/bin/add-apt-repository',
            '--yes',
            'ppa:saltstack/salt',
        ])
        subprocess.check_call(['/usr/bin/apt-get', 'update'])
    # We install salt-common as salt-minion would run the salt-minion
    # daemon.
    charmhelpers.core.host.apt_install('salt-common')


def update_machine_state(state_path):
    """Update the machine state using the provided state declaration."""
    juju_config_2_grains()
    subprocess.check_call([
        'salt-call',
        '--local',
        'state.template',
        state_path,
    ])


def juju_config_2_grains():
    """Insert the juju config as salt grains for use in state templates.

    This includes any current relation-get data, and the charm
    directory.
    """
    config = charmhelpers.core.hookenv.config()

    # Add the charm_dir which we will need to refer to charm
    # file resources etc.
    config['charm_dir'] = charm_dir
    config['local_unit'] = charmhelpers.core.hookenv.local_unit()
    config.update(charmhelpers.core.hookenv.relation_get())

    # Don't use non-standard tags for unicode which will not
    # work when salt uses yaml.load_safe.
    yaml.add_representer(unicode, lambda dumper,
                         value: dumper.represent_scalar(
                             u'tag:yaml.org,2002:str', value))
    with open(salt_grains_path, "w+") as fp:
        fp.write(config.yaml())
