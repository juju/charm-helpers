# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
"""Charm Helpers ansible - declare the state of your machines.

This helper enables you to declare your machine state, rather than
program it procedurally (and have to test each change to your procedures).
Your install hook can be as simple as:

{{{
import charmhelpers.contrib.ansible


def install():
    charmhelpers.contrib.ansible.install_ansible_support()
    charmhelpers.contrib.ansible.apply_playbook('playbooks/install.yaml')
}}}

and won't need to change (nor will its tests) when you change the machine
state.

All of your juju config and relation-data are available as template
variables within your playbooks and templates. An install playbook looks
something like:

{{{
---
- hosts: localhost
  user: root

  tasks:
    - name: Add private repositories.
      template:
        src: ../templates/private-repositories.list.jinja2
        dest: /etc/apt/sources.list.d/private.list

    - name: Update the cache.
      apt: update_cache=yes

    - name: Install dependencies.
      apt: pkg={{ item }}
      with_items:
        - python-mimeparse
        - python-webob
        - sunburnt

    - name: Setup groups.
      group: name={{ item.name }} gid={{ item.gid }}
      with_items:
        - { name: 'deploy_user', gid: 1800 }
        - { name: 'service_user', gid: 1500 }

  ...
}}}

Read more online about playbooks[1] and standard ansible modules[2].

[1] http://www.ansibleworks.com/docs/playbooks.html
[2] http://www.ansibleworks.com/docs/modules.html
"""
import os
import subprocess

import charmhelpers.contrib.saltstack
import charmhelpers.core.host
import charmhelpers.core.hookenv
import charmhelpers.fetch


charm_dir = os.environ.get('CHARM_DIR', '')
ansible_hosts_path = '/etc/ansible/hosts'
# Ansible will automatically include any vars in the following
# file in its inventory when run locally.
ansible_vars_path = '/etc/ansible/host_vars/localhost'


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
        charmhelpers.fetch.apt_update(fatal=True)
    charmhelpers.fetch.apt_install('ansible')
    with open(ansible_hosts_path, 'w+') as hosts_file:
        hosts_file.write('localhost ansible_connection=local')


def apply_playbook(playbook):
    charmhelpers.contrib.saltstack.juju_state_to_yaml(
        ansible_vars_path, namespace_separator='__')
    subprocess.check_call(['ansible-playbook', '-c', 'local', playbook])
