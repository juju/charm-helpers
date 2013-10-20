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

import charmhelpers.contrib.saltstack


class InstallSaltSupportTestCase(unittest.TestCase):

    def setUp(self):
        super(InstallSaltSupportTestCase, self).setUp()

        patcher = mock.patch('charmhelpers.contrib.saltstack.subprocess')
        self.mock_subprocess = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('charmhelpers.fetch')
        self.mock_charmhelpers_fetch = patcher.start()
        self.addCleanup(patcher.stop)

    def test_adds_ppa_by_default(self):
        charmhelpers.contrib.saltstack.install_salt_support()

        expected_calls = [((cmd,), {}) for cmd in [
            ['/usr/bin/add-apt-repository', '--yes', 'ppa:saltstack/salt'],
            ['/usr/bin/apt-get', 'update'],
        ]]
        self.assertEqual(self.mock_subprocess.check_call.call_count, 2)
        self.assertEqual(
            expected_calls, self.mock_subprocess.check_call.call_args_list)
        self.mock_charmhelpers_fetch.apt_install.assert_called_once_with(
            'salt-common')

    def test_no_ppa(self):
        charmhelpers.contrib.saltstack.install_salt_support(
            from_ppa=False)

        self.assertEqual(self.mock_subprocess.check_call.call_count, 0)
        self.mock_charmhelpers_fetch.apt_install.assert_called_once_with(
            'salt-common')


class UpdateMachineStateTestCase(unittest.TestCase):

    def setUp(self):
        super(UpdateMachineStateTestCase, self).setUp()

        patcher = mock.patch('charmhelpers.contrib.saltstack.subprocess')
        self.mock_subprocess = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('charmhelpers.contrib.saltstack.'
                             'juju_state_to_yaml')
        self.mock_config_2_grains = patcher.start()
        self.addCleanup(patcher.stop)

    def test_calls_local_salt_template(self):
        charmhelpers.contrib.saltstack.update_machine_state(
            'states/install.yaml')

        self.mock_subprocess.check_call.assert_called_once_with([
            'salt-call',
            '--local',
            'state.template',
            'states/install.yaml',
        ])

    def test_updates_grains(self):
        charmhelpers.contrib.saltstack.update_machine_state(
            'states/install.yaml')

        self.mock_config_2_grains.assert_called_once_with('/etc/salt/grains')


class JujuConfig2GrainsTestCase(unittest.TestCase):
    def setUp(self):
        super(JujuConfig2GrainsTestCase, self).setUp()

        # Hookenv patches (a single patch to hookenv doesn't work):
        patcher = mock.patch('charmhelpers.core.hookenv.config')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)
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

        # patches specific to this test class.
        etc_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, etc_dir)
        self.grain_path = os.path.join(etc_dir, 'salt', 'grains')

        patcher = mock.patch.object(charmhelpers.contrib.saltstack,
                                    'charm_dir', '/tmp/charm_dir')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_output_with_empty_relation(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.saltstack.juju_state_to_yaml(self.grain_path)

        with open(self.grain_path, 'r') as grain_file:
            result = yaml.load(grain_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "local_unit": "click-index/3",
            }, result)

    def test_output_with_no_relation(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_local_unit.return_value = "click-index/3"
        self.mock_relation_get.return_value = None

        charmhelpers.contrib.saltstack.juju_state_to_yaml(self.grain_path)

        with open(self.grain_path, 'r') as grain_file:
            result = yaml.load(grain_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "local_unit": "click-index/3",
            }, result)

    def test_output_with_relation(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_relation_type.return_value = 'wsgi-file'
        self.mock_relation_get.return_value = {
            'relation_key1': 'relation_value1',
            'relation_key2': 'relation_value2',
        }
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.saltstack.juju_state_to_yaml(self.grain_path)

        with open(self.grain_path, 'r') as grain_file:
            result = yaml.load(grain_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "wsgi_file:relation_key1": "relation_value1",
                "wsgi_file:relation_key2": "relation_value2",
                "local_unit": "click-index/3",
            }, result)

    def test_relation_with_separator(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_relation_type.return_value = 'wsgi-file'
        self.mock_relation_get.return_value = {
            'relation_key1': 'relation_value1',
            'relation_key2': 'relation_value2',
        }
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.saltstack.juju_state_to_yaml(
            self.grain_path, namespace_separator='__')

        with open(self.grain_path, 'r') as grain_file:
            result = yaml.load(grain_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "wsgi_file__relation_key1": "relation_value1",
                "wsgi_file__relation_key2": "relation_value2",
                "local_unit": "click-index/3",
            }, result)

    def test_updates_existing_values(self):
        """Data stored in grains is retained.

        This may be helpful so that templates can access information
        from relations outside the current context.
        """
        os.makedirs(os.path.dirname(self.grain_path))
        with open(self.grain_path, 'w+') as grain_file:
            grain_file.write(yaml.dump({
                'solr:hostname': 'example.com',
                'user_code_runner': 'oldvalue',
            }))

        self.mock_config.return_value = charmhelpers.core.hookenv.Serializable({
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'newvalue',
        })
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.saltstack.juju_state_to_yaml(self.grain_path)

        with open(self.grain_path, 'r') as grain_file:
            result = yaml.load(grain_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "newvalue",
                "local_unit": "click-index/3",
                "solr:hostname": "example.com",
            }, result)
