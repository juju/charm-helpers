# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
import mock
import tempfile
import unittest
import yaml

import charmhelpers.core.hookenv
import charmhelpers.contrib.saltstack


class InstallSaltSupportTestCase(unittest.TestCase):

    def setUp(self):
        super(InstallSaltSupportTestCase, self).setUp()

        patcher = mock.patch('charmhelpers.contrib.saltstack.subprocess')
        self.mock_subprocess = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('charmhelpers.core')
        self.mock_charmhelpers_core = patcher.start()
        self.addCleanup(patcher.stop)

    def test_adds_ppa_by_default(self):
        charmhelpers.contrib.saltstack.install_salt_support()

        self.assertEqual(self.mock_subprocess.check_call.call_count, 2)
        self.assertEqual([(([
                '/usr/bin/add-apt-repository',
                '--yes',
                'ppa:saltstack/salt',
            ],), {}),
            (([
                '/usr/bin/apt-get',
                'update',
            ],), {})
        ], self.mock_subprocess.check_call.call_args_list)
        self.mock_charmhelpers_core.host.apt_install.assert_called_once_with(
            'salt-common')

    def test_no_ppa(self):
        charmhelpers.contrib.saltstack.install_salt_support(
            from_ppa=False)

        self.assertEqual(self.mock_subprocess.check_call.call_count, 0)
        self.mock_charmhelpers_core.host.apt_install.assert_called_once_with(
            'salt-common')


class UpdateMachineStateTestCase(unittest.TestCase):

    def setUp(self):
        super(UpdateMachineStateTestCase, self).setUp()

        patcher = mock.patch('charmhelpers.contrib.saltstack.subprocess')
        self.mock_subprocess = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('charmhelpers.contrib.saltstack.'
                             'juju_config_2_grains')
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

        self.mock_config_2_grains.assert_called_once_with()


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
        patcher = mock.patch('charmhelpers.core.hookenv.local_unit')
        self.mock_local_unit = patcher.start()
        self.addCleanup(patcher.stop)

        # patches specific to this test class.
        grain_file = tempfile.NamedTemporaryFile()
        self.grain_path = grain_file.name
        self.addCleanup(grain_file.close)

        patcher = mock.patch.object(charmhelpers.contrib.saltstack,
                                    'salt_grains_path', self.grain_path)
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch.object(charmhelpers.contrib.saltstack,
                                    'charm_dir', '/tmp/charm_dir')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_output_without_relation(self):
        self.mock_config.return_value = charmhelpers.core.hookenv.Serializable({
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        })
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.saltstack.juju_config_2_grains()

        with open(self.grain_path, 'r') as grain_file:
            result = yaml.load(grain_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "local_unit": "click-index/3",
            }, result)

    def test_output_with_relation(self):
        self.mock_config.return_value = charmhelpers.core.hookenv.Serializable({
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        })
        self.mock_relation_get.return_value = {
            'relation_key1': 'relation_value1',
            'relation_key2': 'relation_value2',
        }
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.saltstack.juju_config_2_grains()

        with open(self.grain_path, 'r') as grain_file:
            result = yaml.load(grain_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "relation_key1": "relation_value1",
                "relation_key2": "relation_value2",
                "local_unit": "click-index/3",
            }, result)
