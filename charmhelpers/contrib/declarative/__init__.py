import os
import subprocess
import yaml

import charmhelpers.core.host
import charmhelpers.core.hookenv


charm_dir = os.environ.get('CHARM_DIR', '')
salt_grains_path = '/etc/salt/grains'


def install_declarative_support():
    """Installs the salt-minion helper for machine state."""
    subprocess.check_call([
        '/usr/bin/add-apt-repository',
        '--yes',
        'ppa:saltstack/salt',
    ])
    subprocess.check_call(['/usr/bin/apt-get', 'update'])
    charmhelpers.core.host.apt_install('salt-minion')


def update_machine_state(state_path):
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
