import shutil
import tempfile
import yaml

import tests.utils

import charmhelpers.contrib.openstack.files.policy_rc_d_script as policy_rc_d


NOVS_POLICY_FILE_CONTENTS = """
blocked_actions:
  neutron-dhcp-agent: [restart, stop, try-restart]
  neutron-l3-agent: [restart, stop, try-restart]
policy_requestor_name: neutron-openvswitch
policy_requestor_type: charm
"""

COMPUTE_POLICY_FILE_CONTENTS = """
blocked_actions:
  libvirt: [restart, stop, try-restart]
  nova-compute: [restart, stop, try-restart]
policy_requestor_name: nova-compute
policy_requestor_type: charm
"""

ANOTHER_POLICY_FILE_CONTENTS = """
blocked_actions:
  libvirt: [restart, stop, try-restart]
policy_requestor_name: mycharm
policy_requestor_type: charm
"""


class PolicyRCDScriptTestCase(tests.utils.BaseTestCase):

    def setUp(self):
        super(PolicyRCDScriptTestCase, self).setUp()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(PolicyRCDScriptTestCase, self).tearDown()
        shutil.rmtree(self.test_dir)

    def write_policy(self, pfile_name, contents):
        test_policy_file = '{}/{}'.format(self.test_dir, pfile_name)
        with open(test_policy_file, 'w') as f:
            f.write(contents)
        return test_policy_file

    def test_read_policy_file(self):
        test_policy_file = self.write_policy(
            'novs.policy',
            NOVS_POLICY_FILE_CONTENTS)
        policy = policy_rc_d.read_policy_file(test_policy_file)
        self.assertEqual(
            policy,
            [
                policy_rc_d.SystemPolicy(
                    policy_requestor_name='neutron-openvswitch',
                    policy_requestor_type='charm',
                    service='neutron-dhcp-agent',
                    blocked_actions=['restart', 'stop', 'try-restart']),
                policy_rc_d.SystemPolicy(
                    policy_requestor_name='neutron-openvswitch',
                    policy_requestor_type='charm',
                    service='neutron-l3-agent',
                    blocked_actions=['restart', 'stop', 'try-restart'])])

    def test_get_policies(self):
        self.write_policy('novs.policy', NOVS_POLICY_FILE_CONTENTS)
        self.write_policy('compute.policy', COMPUTE_POLICY_FILE_CONTENTS)
        policies = policy_rc_d.get_policies(self.test_dir)
        self.maxDiff = None
        self.assertEqual(
            sorted(policies),
            [
                policy_rc_d.SystemPolicy(
                    policy_requestor_name='neutron-openvswitch',
                    policy_requestor_type='charm',
                    service='neutron-dhcp-agent',
                    blocked_actions=['restart', 'stop', 'try-restart']),
                policy_rc_d.SystemPolicy(
                    policy_requestor_name='neutron-openvswitch',
                    policy_requestor_type='charm',
                    service='neutron-l3-agent',
                    blocked_actions=['restart', 'stop', 'try-restart']),
                policy_rc_d.SystemPolicy(
                    policy_requestor_name='nova-compute',
                    policy_requestor_type='charm',
                    service='libvirt',
                    blocked_actions=['restart', 'stop', 'try-restart']),
                policy_rc_d.SystemPolicy(
                    policy_requestor_name='nova-compute',
                    policy_requestor_type='charm',
                    service='nova-compute',
                    blocked_actions=['restart', 'stop', 'try-restart'])])

    def test_record_blocked_action(self):
        self.patch_object(policy_rc_d.time, 'time')
        self.time.return_value = 456
        self.patch_object(policy_rc_d.uuid, 'uuid1')
        uuids = ['uuid1', 'uuid2']
        self.uuid1.side_effect = lambda: uuids.pop()
        blocking_policies = [
            policy_rc_d.SystemPolicy(
                policy_requestor_name='cinder',
                policy_requestor_type='charm',
                service='cinder',
                blocked_actions=['restart', 'stop', 'try-restart']),
            policy_rc_d.SystemPolicy(
                policy_requestor_name='cinder-ceph',
                policy_requestor_type='charm',
                service='cinder',
                blocked_actions=['restart', 'stop', 'try-restart'])]
        policy_rc_d.record_blocked_action(
            'cinder-api',
            'restart',
            blocking_policies,
            self.test_dir)
        expect = [
            (
                '{}/charm-cinder-uuid2.deferred'.format(self.test_dir),
                {
                    'action': 'restart',
                    'reason': 'Package update',
                    'policy_requestor_name': 'cinder',
                    'policy_requestor_type': 'charm',
                    'service': 'cinder-api',
                    'timestamp': 456.0}),
            (
                '{}/charm-cinder-ceph-uuid1.deferred'.format(self.test_dir),
                {
                    'action': 'restart',
                    'reason': 'Package update',
                    'policy_requestor_name': 'cinder-ceph',
                    'policy_requestor_type': 'charm',
                    'service': 'cinder-api',
                    'timestamp': 456.0})]
        for defer_file, contents in expect:
            with open(defer_file, 'r') as f:
                self.assertEqual(
                    yaml.safe_load(f),
                    contents)

    def test_get_blocking_policies(self):
        self.write_policy('novs.policy', NOVS_POLICY_FILE_CONTENTS)
        self.write_policy('compute.policy', COMPUTE_POLICY_FILE_CONTENTS)
        policies = policy_rc_d.get_blocking_policies(
            'libvirt',
            'restart',
            self.test_dir)
        self.assertEqual(
            policies,
            [
                policy_rc_d.SystemPolicy(
                    policy_requestor_name='nova-compute',
                    policy_requestor_type='charm',
                    service='libvirt',
                    blocked_actions=['restart', 'stop', 'try-restart'])])

    def test_process_action_request(self):
        self.write_policy('novs.policy', NOVS_POLICY_FILE_CONTENTS)
        self.write_policy('compute.policy', COMPUTE_POLICY_FILE_CONTENTS)
        self.write_policy('another.policy', ANOTHER_POLICY_FILE_CONTENTS)
        self.assertEqual(
            policy_rc_d.process_action_request(
                'libvirt',
                'restart',
                self.test_dir,
                self.test_dir),
            (
                False,
                ('restart of libvirt blocked by charm mycharm, '
                 'charm nova-compute')))
        self.assertEqual(
            policy_rc_d.process_action_request(
                'glance-api',
                'restart',
                self.test_dir,
                self.test_dir),
            (
                True,
                'Permitting glance-api restart'))
