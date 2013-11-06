# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
import mock
import unittest

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

        patcher = mock.patch('charmhelpers.contrib.templating.contexts.'
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
