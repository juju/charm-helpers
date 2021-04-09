import textwrap
import uuid

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


class TestOVN(test_utils.BaseTestCase):

    def test_ovn_appctl(self):
        self.patch_object(ovn.utils, '_run')
        ovn.ovn_appctl('ovn-northd', ('is-paused',))
        self._run.assert_called_once_with('ovn-appctl', '-t', 'ovn-northd',
                                          'is-paused')
        self._run.reset_mock()
        ovn.ovn_appctl('ovnnb_db', ('cluster/status',))
        self._run.assert_called_once_with('ovn-appctl', '-t',
                                          '/var/run/ovn/ovnnb_db.ctl',
                                          'cluster/status')
        self._run.reset_mock()
        ovn.ovn_appctl('ovnnb_db', ('cluster/status',), use_ovs_appctl=True)
        self._run.assert_called_once_with('ovs-appctl', '-t',
                                          '/var/run/ovn/ovnnb_db.ctl',
                                          'cluster/status')
        self._run.reset_mock()
        ovn.ovn_appctl('ovnsb_db', ('cluster/status',),
                       rundir='/var/run/openvswitch')
        self._run.assert_called_once_with('ovn-appctl', '-t',
                                          '/var/run/openvswitch/ovnsb_db.ctl',
                                          'cluster/status')

    def test_cluster_status(self):
        self.patch_object(ovn, 'ovn_appctl')
        self.ovn_appctl.return_value = CLUSTER_STATUS
        expect = ovn.OVNClusterStatus(
            'OVN_Northbound',
            uuid.UUID('f6a36e77-97bf-4740-b46a-705cbe4fef45'),
            uuid.UUID('0ea6e785-c2bb-4640-b7a2-85104c11a2c1'),
            'ssl:10.219.3.174:6643',
            'cluster member',
            'follower',
            3,
            '22dd',
            'unknown',
            1000,
            '[2, 10]',
            0,
            0,
            '->f6cf ->22dd <-22dd <-f6cf',
            [
                ('0ea6', 'ssl:10.219.3.174:6643'),
                ('f6cf', 'ssl:10.219.3.64:6643'),
                ('22dd', 'ssl:10.219.3.137:6643'),
            ])
        self.assertEquals(ovn.cluster_status('ovnnb_db'), expect)
        self.ovn_appctl.assert_called_once_with('ovnnb_db', ('cluster/status',
                                                'OVN_Northbound'),
                                                rundir=None,
                                                use_ovs_appctl=False)
        self.assertFalse(expect.is_cluster_leader)
        expect = ovn.OVNClusterStatus(
            'OVN_Northbound',
            uuid.UUID('f6a36e77-97bf-4740-b46a-705cbe4fef45'),
            uuid.UUID('0ea6e785-c2bb-4640-b7a2-85104c11a2c1'),
            'ssl:10.219.3.174:6643',
            'cluster member',
            'leader',
            3,
            'self',
            'unknown',
            1000,
            '[2, 10]',
            0,
            0,
            '->f6cf ->22dd <-22dd <-f6cf',
            [
                ('0ea6', 'ssl:10.219.3.174:6643'),
                ('f6cf', 'ssl:10.219.3.64:6643'),
                ('22dd', 'ssl:10.219.3.137:6643'),
            ])
        self.assertTrue(expect.is_cluster_leader)

    def test_is_northd_active(self):
        self.patch_object(ovn, 'ovn_appctl')
        self.ovn_appctl.return_value = NORTHD_STATUS_ACTIVE
        self.assertTrue(ovn.is_northd_active())
        self.ovn_appctl.assert_called_once_with('ovn-northd', ('status',))
        self.ovn_appctl.return_value = NORTHD_STATUS_STANDBY
        self.assertFalse(ovn.is_northd_active())
