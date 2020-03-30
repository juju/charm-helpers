import textwrap

import charmhelpers.contrib.network.ovs.ovn as ovn

import tests.utils as test_utils


CLUSTER_STATUS = textwrap.dedent("""
0ea6
Name: OVN_Northbound
Cluster ID: f6a3 (f6a36e77-97bf-4740-b46a-705cbe4fef45)
Server ID: 0ea6 (0ea6e785-c2bb-4640-b7a2-85104c11a2c1)
Address: ssl:10.219.3.174:6643
Status: cluster member
Role: follower
Term: 3
Leader: 22dd
Vote: unknown

Election timer: 1000
Log: [2, 10]
Entries not yet committed: 0
Entries not yet applied: 0
Connections: ->f6cf ->22dd <-22dd <-f6cf
Servers:
    0ea6 (0ea6 at ssl:10.219.3.174:6643) (self)
    f6cf (f6cf at ssl:10.219.3.64:6643)
    22dd (22dd at ssl:10.219.3.137:6643)
""")

NORTHD_STATUS_ACTIVE = textwrap.dedent("""
Status: active
""")

NORTHD_STATUS_STANDBY = textwrap.dedent("""
Status: standby
""")


class TestOVSDB(test_utils.BaseTestCase):

    def test_ovn_rundir(self):
        self.patch_object(ovn.os.path, 'exists')
        self.exists.side_effect = [False, False]
        self.assertEquals(ovn.ovn_rundir(), '/var/run/ovn')
        self.exists.side_effect = [False, True]
        self.assertEquals(ovn.ovn_rundir(), '/var/run/openvswitch')
        self.exists.side_effect = [True]
        self.assertEquals(ovn.ovn_rundir(), '/var/run/ovn')

    def test_ovn_sysconfdir(self):
        self.patch_object(ovn.os.path, 'exists')
        self.exists.side_effect = [False, False]
        self.assertEquals(ovn.ovn_sysconfdir(), '/etc/ovn')
        self.exists.side_effect = [False, True]
        self.assertEquals(ovn.ovn_sysconfdir(), '/etc/openvswitch')
        self.exists.side_effect = [True]
        self.assertEquals(ovn.ovn_sysconfdir(), '/etc/ovn')

    def test_ovs_appctl(self):
        self.patch_object(ovn.utils, '_run')
        self.patch_object(ovn, 'ovn_rundir')
        self.ovn_rundir.return_value = '/var/run/openvswitch'
        ovn.ovs_appctl('ovn-northd', 'is-paused')
        self._run.assert_called_once_with('ovs-appctl', '-t', 'ovn-northd',
                                          'is-paused')
        self._run.reset_mock()
        ovn.ovs_appctl('ovnnb_db', 'cluster/status')
        self._run.assert_called_once_with('ovs-appctl', '-t',
                                          '/var/run/openvswitch/ovnnb_db.ctl',
                                          'cluster/status')
        self._run.reset_mock()
        ovn.ovs_appctl('ovnsb_db', 'cluster/status')
        self._run.assert_called_once_with('ovs-appctl', '-t',
                                          '/var/run/openvswitch/ovnsb_db.ctl',
                                          'cluster/status')

    def test_cluster_status(self):
        self.patch_object(ovn, 'ovs_appctl')
        self.ovs_appctl.return_value = CLUSTER_STATUS
        expect = {
            'name': 'OVN_Northbound',
            'cluster_id': ('f6a3', 'f6a36e77-97bf-4740-b46a-705cbe4fef45'),
            'server_id': ('0ea6', '0ea6e785-c2bb-4640-b7a2-85104c11a2c1'),
            'address': 'ssl:10.219.3.174:6643',
            'status': 'cluster member',
            'role': 'follower',
            'term': '3',
            'leader': '22dd',
            'vote': 'unknown',
            'election_timer': '1000',
            'log': '[2, 10]',
            'entries_not_yet_committed': '0',
            'entries_not_yet_applied': '0',
            'connections': '->f6cf ->22dd <-22dd <-f6cf',
            'servers': [
                '0ea6 (0ea6 at ssl:10.219.3.174:6643) (self)',
                'f6cf (f6cf at ssl:10.219.3.64:6643)',
                '22dd (22dd at ssl:10.219.3.137:6643)',
            ],
        }
        self.assertDictEqual(ovn.cluster_status('ovnnb_db'), expect)
        self.ovs_appctl.assert_called_once_with('ovnnb_db', 'cluster/status',
                                                'OVN_Northbound')

    def test_is_cluster_leader(self):
        self.patch_object(ovn, 'cluster_status')
        self.cluster_status.return_value = {'leader': 'abcd'}
        self.assertFalse(ovn.is_cluster_leader('ovnnb_db'))
        self.cluster_status.return_value = {'leader': 'self'}
        self.assertTrue(ovn.is_cluster_leader('ovnnb_db'))

    def test_is_northd_active(self):
        self.patch_object(ovn, 'ovs_appctl')
        self.ovs_appctl.return_value = NORTHD_STATUS_ACTIVE
        self.assertTrue(ovn.is_northd_active())
        self.ovs_appctl.assert_called_once_with('ovn-northd', 'status')
        self.ovs_appctl.return_value = NORTHD_STATUS_STANDBY
        self.assertFalse(ovn.is_northd_active())
