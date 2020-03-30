import mock
import subprocess
import sys
import textwrap
import uuid

import tests.utils as utils

import charmhelpers.contrib.network.ovs.ovn as ovn


VSCTL_BRIDGE_TBL = textwrap.dedent("""
{"data":[[["uuid","1e21ba48-61ff-4b32-b35e-cb80411da351"],["set",[]],["set",[]],"0000a0369fdd3890","","<unknown>",["map",[["charm-ovn-chassis","managed"],["other","value"]]],["set",[]],["set",[]],["map",[]],["set",[]],false,["set",[]],"br-test",["set",[]],["map",[]],["set",[["uuid","617f9359-77e2-41be-8af6-4c44e7a6bcc3"],["uuid","da840476-8809-4107-8733-591f4696f056"]]],["set",[]],false,["map",[]],["set",[]],["map",[]],false],[["uuid","bb685b0f-a383-40a1-b7a5-b5c2066bfa42"],["set",[]],["set",[]],"00000e5b68bba140","","<unknown>",["map",[]],"secure",["set",[]],["map",[]],["set",[]],false,["set",[]],"br-int",["set",[]],["map",[["disable-in-band","true"]]],["set",[["uuid","07f4c231-9fd2-49b0-a558-5b69d657fdb0"],["uuid","8bbd2441-866f-4317-a284-09491702776c"],["uuid","d9e9c081-6482-4006-b7d6-239182b56c2e"]]],["set",[]],false,["map",[]],["set",[]],["map",[]],false]],"headings":["_uuid","auto_attach","controller","datapath_id","datapath_type","datapath_version","external_ids","fail_mode","flood_vlans","flow_tables","ipfix","mcast_snooping_enable","mirrors","name","netflow","other_config","ports","protocols","rstp_enable","rstp_status","sflow","status","stp_enable"]}
""")

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


class TestOVSDB(utils.BaseTestCase):

    def test__run(self):
        self.patch_object(ovn.subprocess, 'run')
        self.run.return_value = 'aReturn'
        self.assertEquals(ovn._run('aArg'), 'aReturn')
        self.run.assert_called_once_with(
            ('aArg',), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            check=True, universal_newlines=True)

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
        self.patch_object(ovn, '_run')
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

    def test_add_br(self):
        self.patch_object(ovn, '_run')
        ovn.add_br('br-x')
        self._run.assert_called_once_with(
            'ovs-vsctl', 'add-br', 'br-x', '--', 'set', 'bridge', 'br-x',
            'protocols=OpenFlow13')
        self._run.reset_mock()
        ovn.add_br('br-x', ('charm', 'managed'))
        self._run.assert_called_once_with(
            'ovs-vsctl', 'add-br', 'br-x', '--', 'set', 'bridge', 'br-x',
            'protocols=OpenFlow13', '--',
            'br-set-external-id', 'br-x', 'charm', 'managed')

    def test_del_br(self):
        self.patch_object(ovn, '_run')
        ovn.del_br('br-x')
        self._run.assert_called_once_with(
            'ovs-vsctl', 'del-br', 'br-x')

    def test_add_port(self):
        self.patch_object(ovn, '_run')
        ovn.add_port('br-x', 'enp3s0f0')
        self._run.assert_called_once_with(
            'ovs-vsctl', '--may-exist', 'add-port', 'br-x', 'enp3s0f0')
        self._run.reset_mock()
        ifdata = {
            'type': 'internal',
            'external-ids': {
                'iface-id': 'fakeifid',
                'iface-status': 'active',
                'attached-mac': 'fakeaddr',
            },
        }
        ovn.add_port('br-x', 'enp3s0f0', ifdata=ifdata)
        self._run.assert_called_once_with(
            'ovs-vsctl', '--may-exist', 'add-port', 'br-x', 'enp3s0f0',
            '--',
            'set', 'Interface', 'enp3s0f0', 'type=internal',
            '--',
            'set', 'Interface', 'enp3s0f0', 'external-ids:iface-id=fakeifid',
            '--',
            'set', 'Interface', 'enp3s0f0', 'external-ids:iface-status=active',
            '--',
            'set', 'Interface', 'enp3s0f0',
            'external-ids:attached-mac=fakeaddr')
        self._run.reset_mock()
        ovn.add_port('br-x', 'enp3s0f0', exclusive=True)
        self._run.assert_called_once_with(
            'ovs-vsctl', 'add-port', 'br-x', 'enp3s0f0')
        self._run.reset_mock()
        ovn.add_port('br-x', 'enp3s0f0', ifdata=ifdata)
        self._run.assert_called_once_with(
            'ovs-vsctl', '--may-exist', 'add-port', 'br-x', 'enp3s0f0',
            '--',
            'set', 'Interface', 'enp3s0f0', 'type=internal',
            '--',
            'set', 'Interface', 'enp3s0f0', 'external-ids:iface-id=fakeifid',
            '--',
            'set', 'Interface', 'enp3s0f0', 'external-ids:iface-status=active',
            '--',
            'set', 'Interface', 'enp3s0f0',
            'external-ids:attached-mac=fakeaddr')

    def test_list_ports(self):
        self.patch_object(ovn, '_run')
        ovn.list_ports('someBridge')
        self._run.assert_called_once_with('ovs-vsctl', 'list-ports',
                                          'someBridge')


class TestSimpleOVSDB(utils.BaseTestCase):

    def patch_target(self, attr, return_value=None):
        mocked = mock.patch.object(self.target, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test__find_tbl(self):
        self.target = ovn.SimpleOVSDB('atool', 'atable')
        self.patch_object(ovn, '_run')
        cp = mock.MagicMock()
        cp.stdout = mock.PropertyMock().return_value = VSCTL_BRIDGE_TBL
        self._run.return_value = cp
        self.maxDiff = None
        expect = {
            '_uuid': uuid.UUID('1e21ba48-61ff-4b32-b35e-cb80411da351'),
            'auto_attach': [],
            'controller': [],
            'datapath_id': '0000a0369fdd3890',
            'datapath_type': '',
            'datapath_version': '<unknown>',
            'external_ids': {
                'charm-ovn-chassis': 'managed',
                'other': 'value',
            },
            'fail_mode': [],
            'flood_vlans': [],
            'flow_tables': {},
            'ipfix': [],
            'mcast_snooping_enable': False,
            'mirrors': [],
            'name': 'br-test',
            'netflow': [],
            'other_config': {},
            'ports': [['uuid', '617f9359-77e2-41be-8af6-4c44e7a6bcc3'],
                      ['uuid', 'da840476-8809-4107-8733-591f4696f056']],
            'protocols': [],
            'rstp_enable': False,
            'rstp_status': {},
            'sflow': [],
            'status': {},
            'stp_enable': False}
        # this in effect also tests the __iter__ front end method
        for el in self.target:
            self.assertDictEqual(el, expect)
            break
        self._run.assert_called_once_with(
            'atool', '-f', 'json', 'find', 'atable')
        self._run.reset_mock()
        # this in effect also tests the find front end method
        for el in self.target.find(condition='name=br-test'):
            break
        self._run.assert_called_once_with(
            'atool', '-f', 'json', 'find', 'atable', 'name=br-test')

    def test_clear(self):
        self.target = ovn.SimpleOVSDB('atool', 'atable')
        self.patch_object(ovn, '_run')
        self.target.clear('1e21ba48-61ff-4b32-b35e-cb80411da351',
                          'external_ids')
        self._run.assert_called_once_with(
            'atool', 'clear', 'atable',
            '1e21ba48-61ff-4b32-b35e-cb80411da351', 'external_ids')

    def test_remove(self):
        self.target = ovn.SimpleOVSDB('atool', 'atable')
        self.patch_object(ovn, '_run')
        self.target.remove('1e21ba48-61ff-4b32-b35e-cb80411da351',
                           'external_ids', 'other')
        self._run.assert_called_once_with(
            'atool', 'remove', 'atable',
            '1e21ba48-61ff-4b32-b35e-cb80411da351', 'external_ids', 'other')

    def test_set(self):
        self.target = ovn.SimpleOVSDB('atool', 'atable')
        self.patch_object(ovn, '_run')
        self.target.set('1e21ba48-61ff-4b32-b35e-cb80411da351',
                        'external_ids:other', 'value')
        self._run.assert_called_once_with(
            'atool', 'set', 'atable',
            '1e21ba48-61ff-4b32-b35e-cb80411da351', 'external_ids:other=value')
