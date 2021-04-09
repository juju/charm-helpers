# Copyright 2014-2015 Canonical Limited.
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

# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
"""
The ansible package enables you to easily use the configuration management
tool `Ansible`_ to setup and configure your charm. All of your charm
configuration options and relation-data are available as regular Ansible
variables which can be used in your playbooks and templates.

.. _Ansible: https://www.ansible.com/

Usage
=====

Here is an example directory structure for a charm to get you started::

    charm-ansible-example/
    |-- ansible
    |   |-- playbook.yaml
    |   `-- templates
    |       `-- example.j2
    |-- config.yaml
    |-- copyright
    |-- icon.svg
    |-- layer.yaml
    |-- metadata.yaml
    |-- reactive
    |   `-- example.py
    |-- README.md

Running a playbook called ``playbook.yaml`` when the ``install`` hook is run
can be as simple as::

    from charmhelpers.contrib import ansible
    from charms.reactive import hook

    @hook('install')
    def install():
        ansible.install_ansible_support()
        ansible.apply_playbook('ansible/playbook.yaml')

Here is an example playbook that uses the ``template`` module to template the
file ``example.j2`` to the charm host and then uses the ``debug`` module to
print out all the host and Juju variables that you can use in your playbooks.
Note that you must target ``localhost`` as the playbook is run locally on the
charm host::

    ---
    - hosts: localhost
      tasks:
        - name: Template a file
          template:
            src: templates/example.j2
            dest: /tmp/example.j2

        - name: Print all variables available to Ansible
          debug:
            var: vars

Read more online about `playbooks`_ and standard Ansible `modules`_.

.. _playbooks: https://docs.ansible.com/ansible/latest/user_guide/playbooks.html
.. _modules: https://docs.ansible.com/ansible/latest/user_guide/modules.html

A further feature of the Ansible hooks is to provide a light weight "action"
scripting tool. This is a decorator that you apply to a function, and that
function can now receive cli args, and can pass extra args to the playbook::

    @hooks.action()
    def some_action(amount, force="False"):
        "Usage: some-action AMOUNT [force=True]"  # <-- shown on error
        # process the arguments
        # do some calls
        # return extra-vars to be passed to ansible-playbook
        return {
            'amount': int(amount),
            'type': force,
        }

You can now create a symlink to hooks.py that can be invoked like a hook, but
with cli params::

    # link actions/some-action to hooks/hooks.py

    actions/some-action amount=10 force=true

Install Ansible via pip
=======================

If you want to install a specific version of Ansible via pip instead of
``install_ansible_support`` which uses APT, consider using the layer options
of `layer-basic`_ to install Ansible in a virtualenv::

    options:
      basic:
        python_packages: ['ansible==2.9.0']
        include_system_packages: true
        use_venv: true

.. _layer-basic: https://charmsreactive.readthedocs.io/en/latest/layer-basic.html#layer-configuration

"""
import os
import json
import stat
import subprocess
import functools

import charmhelpers.contrib.templating.contexts
import charmhelpers.core.host
import charmhelpers.core.hookenv
import charmhelpers.fetch


charm_dir = os.environ.get('CHARM_DIR', '')
ansible_hosts_path = '/etc/ansible/hosts'
# Ansible will automatically include any vars in the following
# file in its inventory when run locally.
ansible_vars_path = '/etc/ansible/host_vars/localhost'


def install_ansible_support(from_ppa=True, ppa_location='ppa:ansible/ansible'):
    """Installs Ansible via APT.

    By default this installs Ansible from the `PPA`_ linked from
    the Ansible `website`_ or from a PPA set in ``ppa_location``.

    .. _PPA: https://launchpad.net/~ansible/+archive/ubuntu/ansible
    .. _website: http://docs.ansible.com/intro_installation.html#latest-releases-via-apt-ubuntu

    If ``from_ppa`` is ``False``, then Ansible will be installed from
    Ubuntu's Universe repositories.
    """
    if from_ppa:
        charmhelpers.fetch.add_source(ppa_location)
        charmhelpers.fetch.apt_update(fatal=True)
    charmhelpers.fetch.apt_install('ansible')
    with open(ansible_hosts_path, 'w+') as hosts_file:
        hosts_file.write('localhost ansible_connection=local ansible_remote_tmp=/root/.ansible/tmp')


def apply_playbook(playbook, tags=None, extra_vars=None):
    """Run a playbook.

    This helper runs a playbook with juju state variables as context,
    therefore variables set in application config can be used directly.
    List of tags (--tags) and dictionary with extra_vars (--extra-vars)
    can be passed as additional parameters.

    Read more about playbook `_variables`_ online.

    .. _variables: https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html

    Example::

        # Run ansible/playbook.yaml with tag install and pass extra
        # variables var_a and var_b
        apply_playbook(
            playbook='ansible/playbook.yaml',
            tags=['install'],
            extra_vars={'var_a': 'val_a', 'var_b': 'val_b'}
        )

        # Run ansible/playbook.yaml with tag config and extra variable nested,
        # which is passed as json and can be used as dictionary in playbook
        apply_playbook(
            playbook='ansible/playbook.yaml',
            tags=['config'],
            extra_vars={'nested': {'a': 'value1', 'b': 'value2'}}
        )

        # Custom config file can be passed within extra_vars
        apply_playbook(
            playbook='ansible/playbook.yaml',
            extra_vars="@some_file.json"
        )

    """
    tags = tags or []
    tags = ",".join(tags)
    charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
        ansible_vars_path, namespace_separator='__',
        allow_hyphens_in_keys=False, mode=(stat.S_IRUSR | stat.S_IWUSR))

    # we want ansible's log output to be unbuffered
    env = os.environ.copy()
    proxy_settings = charmhelpers.core.hookenv.env_proxy_settings()
    if proxy_settings:
        env.update(proxy_settings)
    env['PYTHONUNBUFFERED'] = "1"
    call = [
        'ansible-playbook',
        '-c',
        'local',
        playbook,
    ]
    if tags:
        call.extend(['--tags', '{}'.format(tags)])
    if extra_vars:
        call.extend(['--extra-vars', json.dumps(extra_vars)])
    subprocess.check_call(call, env=env)


class AnsibleHooks(charmhelpers.core.hookenv.Hooks):
    """Run a playbook with the hook-name as the tag.

    This helper builds on the standard hookenv.Hooks helper,
    but additionally runs the playbook with the hook-name specified
    using --tags (ie. running all the tasks tagged with the hook-name).

    Example::

        hooks = AnsibleHooks(playbook_path='ansible/my_machine_state.yaml')

        # All the tasks within my_machine_state.yaml tagged with 'install'
        # will be run automatically after do_custom_work()
        @hooks.hook()
        def install():
            do_custom_work()

        # For most of your hooks, you won't need to do anything other
        # than run the tagged tasks for the hook:
        @hooks.hook('config-changed', 'start', 'stop')
        def just_use_playbook():
            pass

        # As a convenience, you can avoid the above noop function by specifying
        # the hooks which are handled by ansible-only and they'll be registered
        # for you:
        # hooks = AnsibleHooks(
        #     'ansible/my_machine_state.yaml',
        #     default_hooks=['config-changed', 'start', 'stop'])

        if __name__ == "__main__":
            # execute a hook based on the name the program is called by
            hooks.execute(sys.argv)
    """

    def __init__(self, playbook_path, default_hooks=None):
        """Register any hooks handled by ansible."""
        super(AnsibleHooks, self).__init__()

        self._actions = {}
        self.playbook_path = playbook_path

        default_hooks = default_hooks or []

        def noop(*args, **kwargs):
            pass

        for hook in default_hooks:
            self.register(hook, noop)

    def register_action(self, name, function):
        """Register a hook"""
        self._actions[name] = function

    def execute(self, args):
        """Execute the hook followed by the playbook using the hook as tag."""
        hook_name = os.path.basename(args[0])
        extra_vars = None
        if hook_name in self._actions:
            extra_vars = self._actions[hook_name](args[1:])
        else:
            super(AnsibleHooks, self).execute(args)

        charmhelpers.contrib.ansible.apply_playbook(
            self.playbook_path, tags=[hook_name], extra_vars=extra_vars)

    def action(self, *action_names):
        """Decorator, registering them as actions"""
        def action_wrapper(decorated):

            @functools.wraps(decorated)
            def wrapper(argv):
                kwargs = dict(arg.split('=') for arg in argv)
                try:
                    return decorated(**kwargs)
                except TypeError as e:
                    if decorated.__doc__:
                        e.args += (decorated.__doc__,)
                    raise

            self.register_action(decorated.__name__, wrapper)
            if '_' in decorated.__name__:
                self.register_action(
                    decorated.__name__.replace('_', '-'), wrapper)

            return wrapper

        return action_wrapper
