import mock
import textwrap
import uuid

import charmhelpers.contrib.network.ovs.ovsdb as ovsdb

import tests.utils as test_utils


VSCTL_BRIDGE_TBL = textwrap.dedent("""
    {"data":[[["uuid","1e21ba48-61ff-4b32-b35e-cb80411da351"],
    ["set",[]],["set",[]],"0000a0369fdd3890","","<unknown>",
    ["map",[["charm-ovn-chassis","managed"],["other","value"]]],
    ["set",[]],["set",[]],["map",[]],["set",[]],false,["set",[]],
    "br-test",["set",[]],["map",[]],["set",
    [["uuid","617f9359-77e2-41be-8af6-4c44e7a6bcc3"],
    ["uuid","da840476-8809-4107-8733-591f4696f056"]]],
    ["set",["OpenFlow10","OpenFlow13","OpenFlow14"]],false,["map",[]],
    ["set",[]],["map",[]],false],
    [["uuid","bb685b0f-a383-40a1-b7a5-b5c2066bfa42"],
    ["set",[]],["set",[]],"00000e5b68bba140","","<unknown>",
    ["map",[]],"secure",["set",[]],["map",[]],["set",[]],false,
    ["set",[]],"br-int",["set",[]],["map",[["disable-in-band","true"]]],
    ["set",[["uuid","07f4c231-9fd2-49b0-a558-5b69d657fdb0"],
    ["uuid","8bbd2441-866f-4317-a284-09491702776c"],
    ["uuid","d9e9c081-6482-4006-b7d6-239182b56c2e"]]],
    ["set",[]],false,["map",[]],["set",[]],["map",[]],false]],
    "headings":["_uuid","auto_attach","controller","datapath_id",
    "datapath_type","datapath_version","external_ids","fail_mode",
    "flood_vlans","flow_tables","ipfix","mcast_snooping_enable",
    "mirrors","name","netflow","other_config","ports","protocols",
    "rstp_enable","rstp_status","sflow","status","stp_enable"]}
    """)


class TestSimpleOVSDB(test_utils.BaseTestCase):

    def patch_target(self, attr, return_value=None):
        mocked = mock.patch.object(self.target, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test___init__(self):
        with self.assertRaises(RuntimeError):
            self.target = ovsdb.SimpleOVSDB('atool')
        with self.assertRaises(AttributeError):
            self.target = ovsdb.SimpleOVSDB('ovs-vsctl')
            self.target.unknown_table.find()

    def test__find_tbl(self):
        self.target = ovsdb.SimpleOVSDB('ovs-vsctl')
        self.patch_object(ovsdb.utils, '_run')
        self._run.return_value = VSCTL_BRIDGE_TBL
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
            'ports': [uuid.UUID('617f9359-77e2-41be-8af6-4c44e7a6bcc3'),
                      uuid.UUID('da840476-8809-4107-8733-591f4696f056')],
            'protocols': ['OpenFlow10', 'OpenFlow13', 'OpenFlow14'],
            'rstp_enable': False,
            'rstp_status': {},
            'sflow': [],
            'status': {},
            'stp_enable': False}
        # this in effect also tests the __iter__ front end method
        for el in self.target.bridge:
            self.assertDictEqual(el, expect)
            break
        self._run.assert_called_once_with(
            'ovs-vsctl', '-f', 'json', 'find', 'bridge')
        self._run.reset_mock()
        # this in effect also tests the find front end method
        for el in self.target.bridge.find(condition='name=br-test'):
            break
        self._run.assert_called_once_with(
            'ovs-vsctl', '-f', 'json', 'find', 'bridge', 'name=br-test')

    def test_clear(self):
        self.target = ovsdb.SimpleOVSDB('ovs-vsctl')
        self.patch_object(ovsdb.utils, '_run')
        self.target.interface.clear('1e21ba48-61ff-4b32-b35e-cb80411da351',
                                    'external_ids')
        self._run.assert_called_once_with(
            'ovs-vsctl', 'clear', 'interface',
            '1e21ba48-61ff-4b32-b35e-cb80411da351', 'external_ids')

    def test_remove(self):
        self.target = ovsdb.SimpleOVSDB('ovs-vsctl')
        self.patch_object(ovsdb.utils, '_run')
        self.target.interface.remove('1e21ba48-61ff-4b32-b35e-cb80411da351',
                                     'external_ids', 'other')
        self._run.assert_called_once_with(
            'ovs-vsctl', 'remove', 'interface',
            '1e21ba48-61ff-4b32-b35e-cb80411da351', 'external_ids', 'other')

    def test_set(self):
        self.target = ovsdb.SimpleOVSDB('ovs-vsctl')
        self.patch_object(ovsdb.utils, '_run')
        self.target.interface.set('1e21ba48-61ff-4b32-b35e-cb80411da351',
                                  'external_ids:other', 'value')
        self._run.assert_called_once_with(
            'ovs-vsctl', 'set', 'interface',
            '1e21ba48-61ff-4b32-b35e-cb80411da351', 'external_ids:other=value')
