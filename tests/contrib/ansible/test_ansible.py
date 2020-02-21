# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
import mock
import os
import shutil
import stat
import tempfile
import unittest
import yaml


import charmhelpers.contrib.ansible
from charmhelpers.core import hookenv


class InstallAnsibleSupportTestCase(unittest.TestCase):

    def setUp(self):
        super(InstallAnsibleSupportTestCase, self).setUp()

        patcher = mock.patch('charmhelpers.fetch')
        self.mock_fetch = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('charmhelpers.core')
        self.mock_core = patcher.start()
        self.addCleanup(patcher.stop)

        hosts_file = tempfile.NamedTemporaryFile()
        self.ansible_hosts_path = hosts_file.name
        self.addCleanup(hosts_file.close)
        patcher = mock.patch.object(charmhelpers.contrib.ansible,
                                    'ansible_hosts_path',
                                    self.ansible_hosts_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_adds_ppa_by_default(self):
        charmhelpers.contrib.ansible.install_ansible_support()

        self.mock_fetch.add_source.assert_called_once_with(
            'ppa:ansible/ansible')
        self.mock_fetch.apt_update.assert_called_once_with(fatal=True)
        self.mock_fetch.apt_install.assert_called_once_with(
            'ansible')

    def test_no_ppa(self):
        charmhelpers.contrib.ansible.install_ansible_support(
            from_ppa=False)

        self.assertEqual(self.mock_fetch.add_source.call_count, 0)
        self.mock_fetch.apt_install.assert_called_once_with(
            'ansible')

    def test_writes_ansible_hosts(self):
        with open(self.ansible_hosts_path) as hosts_file:
            self.assertEqual(hosts_file.read(), '')

        charmhelpers.contrib.ansible.install_ansible_support()

        with open(self.ansible_hosts_path) as hosts_file:
            self.assertEqual(hosts_file.read(),
                             'localhost ansible_connection=local '
                             'ansible_remote_tmp=/root/.ansible/tmp')


class ApplyPlaybookTestCases(unittest.TestCase):

    unit_data = {
        'private-address': '10.0.3.2',
        'public-address': '123.123.123.123',
    }

    def setUp(self):
        super(ApplyPlaybookTestCases, self).setUp()

        # Hookenv patches (a single patch to hookenv doesn't work):
        patcher = mock.patch('charmhelpers.core.hookenv.config')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)
        Serializable = charmhelpers.core.hookenv.Serializable
        self.mock_config.return_value = Serializable({})
        patcher = mock.patch('charmhelpers.core.hookenv.relation_get')
        self.mock_relation_get = patcher.start()
        self.mock_relation_get.return_value = {}
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.relations')
        self.mock_relations = patcher.start()
        self.mock_relations.return_value = {
            'wsgi-file': {},
            'website': {},
            'nrpe-external-master': {},
        }
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.relations_of_type')
        self.mock_relations_of_type = patcher.start()
        self.mock_relations_of_type.return_value = []
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.relation_type')
        self.mock_relation_type = patcher.start()
        self.mock_relation_type.return_value = None
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.local_unit')
        self.mock_local_unit = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_local_unit.return_value = {}

        def unit_get_data(argument):
            "dummy unit_get that accesses dummy unit data"
            return self.unit_data[argument]

        patcher = mock.patch(
            'charmhelpers.core.hookenv.unit_get', unit_get_data)
        self.mock_unit_get = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('charmhelpers.contrib.ansible.subprocess')
        self.mock_subprocess = patcher.start()
        self.addCleanup(patcher.stop)

        etc_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, etc_dir)
        self.vars_path = os.path.join(etc_dir, 'ansible', 'vars.yaml')
        patcher = mock.patch.object(charmhelpers.contrib.ansible,
                                    'ansible_vars_path', self.vars_path)
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch.object(charmhelpers.contrib.ansible.os,
                                    'environ', {})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_calls_ansible_playbook(self):
        charmhelpers.contrib.ansible.apply_playbook(
            'playbooks/dependencies.yaml')

        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'playbooks/dependencies.yaml'],
            env={'PYTHONUNBUFFERED': '1'})

    def test_writes_vars_file(self):
        self.assertFalse(os.path.exists(self.vars_path))
        self.mock_config.return_value = charmhelpers.core.hookenv.Serializable({
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
            'private-address': '10.10.10.10',
        })
        self.mock_relation_type.return_value = 'wsgi-file'
        self.mock_relation_get.return_value = {
            'relation_key1': 'relation_value1',
            'relation-key2': 'relation_value2',
        }

        charmhelpers.contrib.ansible.apply_playbook(
            'playbooks/dependencies.yaml')

        self.assertTrue(os.path.exists(self.vars_path))
        stats = os.stat(self.vars_path)
        self.assertEqual(
            stats.st_mode & stat.S_IRWXU,
            stat.S_IRUSR | stat.S_IWUSR)
        self.assertEqual(stats.st_mode & stat.S_IRWXG, 0)
        self.assertEqual(stats.st_mode & stat.S_IRWXO, 0)
        with open(self.vars_path, 'r') as vars_file:
            result = yaml.safe_load(vars_file.read())
            self.assertEqual({
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "private_address": "10.10.10.10",
                "charm_dir": "",
                "local_unit": {},
                'current_relation': {
                    'relation_key1': 'relation_value1',
                    'relation-key2': 'relation_value2',
                },
                'relations_full': {
                    'nrpe-external-master': {},
                    'website': {},
                    'wsgi-file': {},
                },
                'relations': {
                    'nrpe-external-master': [],
                    'website': [],
                    'wsgi-file': [],
                },
                "wsgi_file__relation_key1": "relation_value1",
                "wsgi_file__relation_key2": "relation_value2",
                "unit_private_address": "10.0.3.2",
                "unit_public_address": "123.123.123.123",
            }, result)

    def test_calls_with_tags(self):
        charmhelpers.contrib.ansible.apply_playbook(
            'playbooks/complete-state.yaml', tags=['install', 'somethingelse'])

        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'playbooks/complete-state.yaml',
            '--tags', 'install,somethingelse'], env={'PYTHONUNBUFFERED': '1'})

    @mock.patch.object(hookenv, 'config')
    def test_calls_with_extra_vars(self, config):
        charmhelpers.contrib.ansible.apply_playbook(
            'playbooks/complete-state.yaml', tags=['install', 'somethingelse'],
            extra_vars={'a': 'b'})

        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'playbooks/complete-state.yaml',
            '--tags', 'install,somethingelse', '--extra-vars', '{"a": "b"}'],
            env={'PYTHONUNBUFFERED': '1'})

    @mock.patch.object(hookenv, 'config')
    def test_calls_with_extra_vars_path(self, config):
        charmhelpers.contrib.ansible.apply_playbook(
            'playbooks/complete-state.yaml', tags=['install', 'somethingelse'],
            extra_vars='@myvars.json')

        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'playbooks/complete-state.yaml',
            '--tags', 'install,somethingelse', '--extra-vars', '"@myvars.json"'],
            env={'PYTHONUNBUFFERED': '1'})

    @mock.patch.object(hookenv, 'config')
    def test_calls_with_extra_vars_dict(self, config):
        charmhelpers.contrib.ansible.apply_playbook(
            'playbooks/complete-state.yaml', tags=['install', 'somethingelse'],
            extra_vars={'pkg': {'a': 'present', 'b': 'absent'}})

        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'playbooks/complete-state.yaml',
            '--tags', 'install,somethingelse', '--extra-vars',
            '{"pkg": {"a": "present", "b": "absent"}}'],
            env={'PYTHONUNBUFFERED': '1'})

    @mock.patch.object(hookenv, 'config')
    def test_hooks_executes_playbook_with_tag(self, config):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks('my/playbook.yaml')
        foo = mock.MagicMock()
        hooks.register('foo', foo)

        hooks.execute(['foo'])

        self.assertEqual(foo.call_count, 1)
        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'my/playbook.yaml',
            '--tags', 'foo'], env={'PYTHONUNBUFFERED': '1'})

    @mock.patch.object(hookenv, 'config')
    def test_specifying_ansible_handled_hooks(self, config):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks(
            'my/playbook.yaml', default_hooks=['start', 'stop'])

        hooks.execute(['start'])

        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'my/playbook.yaml',
            '--tags', 'start'], env={'PYTHONUNBUFFERED': '1'})


class TestActionDecorator(unittest.TestCase):

    def setUp(self):
        p = mock.patch('charmhelpers.contrib.ansible.apply_playbook')
        self.apply_playbook = p.start()
        self.addCleanup(p.stop)

    def test_action_no_args(self):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks('playbook.yaml')

        @hooks.action()
        def test():
            return {}

        hooks.execute(['test'])
        self.apply_playbook.assert_called_once_with(
            'playbook.yaml', tags=['test'], extra_vars={})

    def test_action_required_arg_keyword(self):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks('playbook.yaml')

        @hooks.action()
        def test(x):
            return locals()

        hooks.execute(['test', 'x=a'])
        self.apply_playbook.assert_called_once_with(
            'playbook.yaml', tags=['test'], extra_vars={'x': 'a'})

    def test_action_required_arg_missing(self):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks('playbook.yaml')

        @hooks.action()
        def test(x):
            """Requires x"""
            return locals()

        try:
            hooks.execute(['test'])
            self.fail("should have thrown TypeError")
        except TypeError as e:
            self.assertEqual(e.args[1], "Requires x")

    def test_action_required_unknown_arg(self):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks('playbook.yaml')

        @hooks.action()
        def test(x='a'):
            """Requires x"""
            return locals()

        try:
            hooks.execute(['test', 'z=c'])
            self.fail("should have thrown TypeError")
        except TypeError as e:
            self.assertEqual(e.args[1], "Requires x")

    def test_action_default_arg(self):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks('playbook.yaml')

        @hooks.action()
        def test(x='b'):
            return locals()

        hooks.execute(['test'])
        self.apply_playbook.assert_called_once_with(
            'playbook.yaml', tags=['test'], extra_vars={'x': 'b'})

    def test_action_mutliple(self):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks('playbook.yaml')

        @hooks.action()
        def test(x, y='b'):
            return locals()

        hooks.execute(['test', 'x=a', 'y=b'])
        self.apply_playbook.assert_called_once_with(
            'playbook.yaml', tags=['test'], extra_vars={'x': 'a', 'y': 'b'})
