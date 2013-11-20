# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
import mock
import os
import shutil
import tempfile
import unittest
import yaml


import charmhelpers.contrib.ansible


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
            'ppa:rquillo/ansible')
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
                             'localhost ansible_connection=local')


class ApplyPlaybookTestCases(unittest.TestCase):

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
        patcher = mock.patch('charmhelpers.core.hookenv.relation_type')
        self.mock_relation_type = patcher.start()
        self.mock_relation_type.return_value = None
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.local_unit')
        self.mock_local_unit = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_local_unit.return_value = {}

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

    def test_calls_ansible_playbook(self):
        charmhelpers.contrib.ansible.apply_playbook(
            'playbooks/dependencies.yaml')

        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'playbooks/dependencies.yaml'])

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
        with open(self.vars_path, 'r') as vars_file:
            result = yaml.load(vars_file.read())
            self.assertEqual({
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "private_address": "10.10.10.10",
                "charm_dir": "",
                "local_unit": {},
                "wsgi_file__relation_key1": "relation_value1",
                "wsgi_file__relation_key2": "relation_value2",
            }, result)

    def test_calls_with_tags(self):
        charmhelpers.contrib.ansible.apply_playbook(
            'playbooks/complete-state.yaml', tags=['install', 'somethingelse'])

        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'playbooks/complete-state.yaml',
            '--tags', 'install,somethingelse'])

    def test_hooks_executes_playbook_with_tag(self):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks('my/playbook.yaml')
        foo = mock.MagicMock()
        hooks.register('foo', foo)

        hooks.execute(['foo'])

        self.assertEqual(foo.call_count, 1)
        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'my/playbook.yaml',
            '--tags', 'foo'])

    def test_specifying_ansible_handled_hooks(self):
        hooks = charmhelpers.contrib.ansible.AnsibleHooks(
            'my/playbook.yaml', default_hooks=['start', 'stop'])

        hooks.execute(['start'])

        self.mock_subprocess.check_call.assert_called_once_with([
            'ansible-playbook', '-c', 'local', 'my/playbook.yaml',
            '--tags', 'start'])
