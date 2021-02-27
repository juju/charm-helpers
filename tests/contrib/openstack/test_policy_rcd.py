import tempfile
import copy
import mock
import unittest
import shutil
import yaml

from charmhelpers.contrib.openstack import policy_rcd

TEST_POLICY = {
    'blocked_actions': {
        'neutron-dhcp-agent': ['restart', 'stop', 'try-restart'],
        'neutron-l3-agent': ['restart', 'stop', 'try-restart'],
        'neutron-metadata-agent': ['restart', 'stop', 'try-restart'],
        'neutron-openvswitch-agent': ['restart', 'stop', 'try-restart'],
        'openvswitch-switch': ['restart', 'stop', 'try-restart'],
        'ovs-vswitchd': ['restart', 'stop', 'try-restart'],
        'ovs-vswitchd-dpdk': ['restart', 'stop', 'try-restart'],
        'ovsdb-server': ['restart', 'stop', 'try-restart']},
    'policy_requestor_name': 'neutron-openvswitch',
    'policy_requestor_type': 'charm'}


class PolicyRCDTests(unittest.TestCase):

    def setUp(self):
        super(PolicyRCDTests, self).setUp()
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tmp_dir))

    def test_policy_config_dir(self):
        self.assertEqual(
            policy_rcd.policy_config_dir(),
            '/etc/policy-rc.d')

    def test_policy_deferred_events_dir(self):
        self.assertEqual(
            policy_rcd.policy_deferred_events_dir(),
            '/var/lib/policy-rc.d')

    @mock.patch.object(policy_rcd.glob, "glob")
    @mock.patch.object(policy_rcd, "policy_deferred_events_dir")
    def test_policy_deferred_events_files(self, policy_deferred_events_dir,
                                          glob):
        policy_deferred_events_dir.return_value = ('/var/lib/policy-rc.d/'
                                                   'charm-myapp')
        defer_files = [
            '/var/lib/policy-rc.d/charm-myapp/1612346300.deferred',
            '/var/lib/policy-rc.d/charm-myapp/1612346322.deferred',
            '/var/lib/policy-rc.d/charm-myapp/1612346360.deferred']

        glob.return_value = defer_files
        self.assertEqual(
            policy_rcd.policy_deferred_events_files(),
            defer_files)

    def test_read_yaml_file(self):
        deferred_event = {
            'action': 'restart',
            'policy_requestor_name': 'neutron-openvswitch',
            'policy_requestor_type': 'charm',
            'service': 'openvswitch-switch',
            'time': 1612346300}
        with tempfile.NamedTemporaryFile('w') as ftmp:
            yaml.dump(deferred_event, ftmp)
            ftmp.flush()
            self.assertEqual(
                policy_rcd.read_yaml_file(ftmp.name),
                deferred_event)

    @mock.patch.object(policy_rcd, "policy_deferred_events_files")
    def test_policy_deferred_events(self, policy_deferred_events_files):
        deferred_events = [
            {
                'action': 'restart',
                'policy_requestor_name': 'neutron-openvswitch',
                'policy_requestor_type': 'charm',
                'service': 'openvswitch-switch',
                'time': 1612346300},
            {
                'action': 'restart',
                'policy_requestor_name': 'neutron-openvswitch',
                'policy_requestor_type': 'charm',
                'service': 'openvswitch-switch',
                'time': 1612346300},
            {
                'action': 'restart',
                'policy_requestor_name': 'neutron-openvswitch',
                'policy_requestor_type': 'charm',
                'service': 'openvswitch-switch',
                'time': 1612346300}]
        temp_dir = tempfile.mkdtemp()
        policy_files = []
        for index, policy in enumerate(deferred_events):
            policy_file = '{}/{}.deferred'.format(temp_dir, str(index))
            with open(policy_file, 'w') as f:
                yaml.dump(policy, f)
            policy_files.append(policy_file)
        policy_deferred_events_files.return_value = policy_files
        self.assertEqual(policy_rcd.policy_deferred_events(), deferred_events)

    @mock.patch.object(policy_rcd.os, "remove")
    @mock.patch.object(policy_rcd, "read_yaml_file")
    @mock.patch.object(policy_rcd, "policy_deferred_events_files")
    def test_clear_deferred_pkg_events(self, policy_deferred_events_files,
                                       read_yaml_file, remove):
        policy_deferred_events_files.return_value = ['/tmp/file1']
        read_yaml_file.return_value = {'service': 'openvswitch-switch'}
        policy_rcd.clear_deferred_pkg_events('apache2', 'restart')
        self.assertFalse(remove.called)
        policy_rcd.clear_deferred_pkg_events('openvswitch-switch', 'restart')
        remove.assert_called_once_with('/tmp/file1')

    @mock.patch.object(policy_rcd.os.path, "exists")
    @mock.patch.object(policy_rcd.shutil, "copy2")
    @mock.patch.object(policy_rcd.host, "mkdir")
    @mock.patch.object(policy_rcd.alternatives, "install_alternative")
    @mock.patch.object(policy_rcd.hookenv, "service_name")
    @mock.patch.object(policy_rcd.os.path, "dirname")
    def test_install_policy_rcd(self, dirname, service_name,
                                install_alternative, mkdir, copy2, exists):
        dirs = ['/dir1', '/dir2']
        service_name.return_value = 'mysvc'
        dirname.side_effect = lambda x: dirs.pop()
        exists.return_value = False
        policy_rcd.install_policy_rcd()
        install_alternative.assert_called_once_with(
            'policy-rc.d',
            '/usr/sbin/policy-rc.d',
            '/var/lib/charm/mysvc/policy-rc.d')
        mkdir.assert_has_calls([
            mock.call('/dir1'),
            mock.call('/etc/policy-rc.d')
        ])
        copy2.assert_called_once_with(
            '/dir2/policy_rc_d_script.py',
            '/var/lib/charm/mysvc/policy-rc.d')

    @mock.patch.object(policy_rcd.hookenv, "service_name")
    def test_get_policy_file_name(self, service_name):
        service_name.return_value = 'mysvc'
        self.assertEqual(
            policy_rcd.get_policy_file_name(),
            '/etc/policy-rc.d/charm-mysvc.policy')

    @mock.patch.object(policy_rcd, "read_yaml_file")
    @mock.patch.object(policy_rcd.os.path, "exists")
    @mock.patch.object(policy_rcd.hookenv, "service_name")
    def test_read_default_policy_file(self, service_name, exists,
                                      read_yaml_file):
        service_name.return_value = 'mysvc'
        exists.return_value = False
        self.assertEqual(policy_rcd.read_default_policy_file(), {})
        exists.return_value = True
        read_yaml_file.return_value = TEST_POLICY
        self.assertEqual(policy_rcd.read_default_policy_file(), TEST_POLICY)

    def test_write_policy_file(self):
        with tempfile.NamedTemporaryFile('w') as ftmp:
            policy_rcd.write_policy_file(ftmp.name, TEST_POLICY)
            with open(ftmp.name, 'r') as f:
                policy = yaml.load(f)
            self.assertEqual(policy, TEST_POLICY)

    @mock.patch.object(policy_rcd.os, "remove")
    @mock.patch.object(policy_rcd.hookenv, "service_name")
    def test_remove_policy_file(self, service_name, remove):
        service_name.return_value = 'mysvc'
        policy_rcd.remove_policy_file()
        remove.assert_called_once_with('/etc/policy-rc.d/charm-mysvc.policy')

    @mock.patch.object(policy_rcd.hookenv, "service_name")
    def test_get_default_policy(self, service_name):
        service_name.return_value = 'mysvc'
        self.assertEqual(
            policy_rcd.get_default_policy(),
            {
                'policy_requestor_name': 'mysvc',
                'policy_requestor_type': 'charm',
                'blocked_actions': {}})

    @mock.patch.object(policy_rcd, "write_policy_file")
    @mock.patch.object(policy_rcd.hookenv, "service_name")
    @mock.patch.object(policy_rcd, "read_default_policy_file")
    def test_add_policy_block(self, read_default_policy_file, service_name,
                              write_policy_file):
        service_name.return_value = 'mysvc'
        old_policy = copy.deepcopy(TEST_POLICY)
        read_default_policy_file.return_value = old_policy
        policy_rcd.add_policy_block('apache2', ['restart'])
        expect_policy = copy.deepcopy(TEST_POLICY)
        expect_policy['blocked_actions']['apache2'] = ['restart']
        write_policy_file.assert_called_once_with(
            '/etc/policy-rc.d/charm-mysvc.policy',
            expect_policy)

    @mock.patch.object(policy_rcd, "write_policy_file")
    @mock.patch.object(policy_rcd.hookenv, "service_name")
    @mock.patch.object(policy_rcd, "read_default_policy_file")
    def test_remove_policy_block(self, read_default_policy_file, service_name,
                                 write_policy_file):
        service_name.return_value = 'mysvc'
        old_policy = copy.deepcopy(TEST_POLICY)
        read_default_policy_file.return_value = old_policy
        policy_rcd.remove_policy_block(
            'neutron-dhcp-agent',
            ['try-restart', 'restart'])
        expect_policy = copy.deepcopy(TEST_POLICY)
        expect_policy['blocked_actions']['neutron-dhcp-agent'] = ['stop']
        write_policy_file.assert_called_once_with(
            '/etc/policy-rc.d/charm-mysvc.policy',
            expect_policy)
