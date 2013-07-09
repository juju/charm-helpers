# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
import mock
import unittest


import charmhelpers.contrib.ansible


class InstallAnsibleSupportTestCase(unittest.TestCase):

    def setUp(self):
        super(InstallAnsibleSupportTestCase, self).setUp()

        patcher = mock.patch('charmhelpers.contrib.ansible.subprocess')
        self.mock_subprocess = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('charmhelpers.core')
        self.mock_charmhelpers_core = patcher.start()
        self.addCleanup(patcher.stop)

    def test_adds_ppa_by_default(self):
        charmhelpers.contrib.ansible.install_ansible_support()

        self.assertEqual(self.mock_subprocess.check_call.call_count, 2)
        self.assertEqual([(([
                '/usr/bin/add-apt-repository',
                '--yes',
                'ppa:rquillo/ansible',
            ],), {}),
            (([
                '/usr/bin/apt-get',
                'update',
            ],), {})
        ], self.mock_subprocess.check_call.call_args_list)
        self.mock_charmhelpers_core.host.apt_install.assert_called_once_with(
            'ansible')

    def test_no_ppa(self):
        charmhelpers.contrib.ansible.install_ansible_support(
            from_ppa=False)

        self.assertEqual(self.mock_subprocess.check_call.call_count, 0)
        self.mock_charmhelpers_core.host.apt_install.assert_called_once_with(
            'ansible')


