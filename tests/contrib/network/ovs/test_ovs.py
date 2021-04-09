import mock
import types
import uuid

import charmhelpers.contrib.network.ovs as ovs

import tests.utils as test_utils


# NOTE(fnordahl): some functions drectly under the ``contrib.network.ovs``
# module have their unit tests in the ``test_ovs.py`` module in the
# ``tests.contrib.network`` package.


class TestOVS(test_utils.BaseTestCase):

    def test__dict_to_vsctl_set(self):
        indata = {
            'key': 'value',
            'otherkey': {
                'nestedkey': 'nestedvalue',
            },
        }
        # due to varying Dict ordering depending on Python version we need
        # to be a bit elaborate rather than comparing result directly
        result1 = ('--', 'set', 'aTable', 'anItem', 'key=value')
        result2 = ('--', 'set', 'aTable', 'anItem',
                   'otherkey:nestedkey=nestedvalue')
        for setcmd in ovs._dict_to_vsctl_set(indata, 'aTable', 'anItem'):
            self.assertTrue(setcmd == result1 or setcmd == result2)

    def test_add_bridge(self):
        self.patch_object(ovs.subprocess, 'check_call')
        self.patch_object(ovs, 'log')
        ovs.add_bridge('test')
        self.check_call.assert_called_once_with([
            "ovs-vsctl", "--", "--may-exist",
            "add-br", 'test'])
        self.assertTrue(self.log.call_count == 1)

        self.check_call.reset_mock()
        self.log.reset_mock()
        ovs.add_bridge('test', datapath_type='netdev')
        self.check_call.assert_called_with([
            "ovs-vsctl", "--", "--may-exist",
            "add-br", 'test', "--", "set",
            "bridge", "test", "datapath_type=netdev",
        ])
        self.assertTrue(self.log.call_count == 2)

        self.check_call.reset_mock()
        ovs.add_bridge('test', exclusive=True)
        self.check_call.assert_called_once_with([
            "ovs-vsctl", "--", "add-br", 'test'])

        self.check_call.reset_mock()
        self.patch_object(ovs, '_dict_to_vsctl_set')
        self._dict_to_vsctl_set.return_value = [['--', 'fakeextradata']]
        ovs.add_bridge('test', brdata={'fakeinput': None})
        self._dict_to_vsctl_set.assert_called_once_with(
            {'fakeinput': None}, 'bridge', 'test')
        self.check_call.assert_called_once_with([
            'ovs-vsctl', '--', '--may-exist', 'add-br', 'test',
            '--', 'fakeextradata'])

    def test_add_bridge_port(self):
        self.patch_object(ovs.subprocess, 'check_call')
        self.patch_object(ovs, 'log')
        ovs.add_bridge_port('test', 'eth1')
        self.check_call.assert_has_calls([
            mock.call(['ovs-vsctl', '--', '--may-exist', 'add-port',
                       'test', 'eth1']),
            mock.call(['ip', 'link', 'set', 'eth1', 'up']),
            mock.call(['ip', 'link', 'set', 'eth1', 'promisc', 'off'])
        ])
        self.assertTrue(self.log.call_count == 1)

        self.check_call.reset_mock()
        self.log.reset_mock()
        ovs.add_bridge_port('test', 'eth1', promisc=True)
        self.check_call.assert_has_calls([
            mock.call(['ovs-vsctl', '--', '--may-exist', 'add-port',
                       'test', 'eth1']),
            mock.call(['ip', 'link', 'set', 'eth1', 'up']),
            mock.call(['ip', 'link', 'set', 'eth1', 'promisc', 'on'])
        ])
        self.assertTrue(self.log.call_count == 1)

        self.check_call.reset_mock()
        self.log.reset_mock()
        ovs.add_bridge_port('test', 'eth1', promisc=None)
        self.check_call.assert_has_calls([
            mock.call(['ovs-vsctl', '--', '--may-exist', 'add-port',
                       'test', 'eth1']),
            mock.call(['ip', 'link', 'set', 'eth1', 'up']),
        ])
        self.assertTrue(self.log.call_count == 1)

        self.check_call.reset_mock()
        ovs.add_bridge_port('test', 'eth1', exclusive=True, linkup=False)
        self.check_call.assert_has_calls([
            mock.call(['ovs-vsctl', '--', 'add-port', 'test', 'eth1']),
            mock.call(['ip', 'link', 'set', 'eth1', 'promisc', 'off'])
        ])

        self.check_call.reset_mock()
        self.patch_object(ovs, '_dict_to_vsctl_set')
        self._dict_to_vsctl_set.return_value = [['--', 'fakeextradata']]
        ovs.add_bridge_port('test', 'eth1', ifdata={'fakeinput': None})
        self._dict_to_vsctl_set.assert_called_once_with(
            {'fakeinput': None}, 'Interface', 'eth1')
        self.check_call.assert_has_calls([
            mock.call(['ovs-vsctl', '--', '--may-exist', 'add-port',
                       'test', 'eth1', '--', 'fakeextradata']),
            mock.call(['ip', 'link', 'set', 'eth1', 'up']),
            mock.call(['ip', 'link', 'set', 'eth1', 'promisc', 'off'])
        ])
        self._dict_to_vsctl_set.reset_mock()
        self.check_call.reset_mock()
        ovs.add_bridge_port('test', 'eth1', portdata={'fakeportinput': None})
        self._dict_to_vsctl_set.assert_called_once_with(
            {'fakeportinput': None}, 'Port', 'eth1')
        self.check_call.assert_has_calls([
            mock.call(['ovs-vsctl', '--', '--may-exist', 'add-port',
                       'test', 'eth1', '--', 'fakeextradata']),
            mock.call(['ip', 'link', 'set', 'eth1', 'up']),
            mock.call(['ip', 'link', 'set', 'eth1', 'promisc', 'off'])
        ])

    def test_del_bridge_port(self):
        self.patch_object(ovs.subprocess, 'check_call')
        self.patch_object(ovs, 'log')
        ovs.del_bridge_port('test', 'eth1')
        self.check_call.assert_has_calls([
            mock.call(['ovs-vsctl', '--', '--if-exists', 'del-port',
                       'test', 'eth1']),
            mock.call(['ip', 'link', 'set', 'eth1', 'down']),
            mock.call(['ip', 'link', 'set', 'eth1', 'promisc', 'off'])
        ])
        self.assertTrue(self.log.call_count == 1)
        self.assertTrue(self.check_call.call_count == 3)
        self.check_call.reset_mock()
        ovs.del_bridge_port('test', 'eth1', linkdown=False)
        self.check_call.assert_called_once_with(
            ['ovs-vsctl', '--', '--if-exists', 'del-port', 'test', 'eth1'])

    def test_ovs_appctl(self):
        self.patch_object(ovs.subprocess, 'check_output')
        ovs.ovs_appctl('ovs-vswitchd', ('ofproto/list',))
        self.check_output.assert_called_once_with(
            ['ovs-appctl', '-t', 'ovs-vswitchd', 'ofproto/list'],
            universal_newlines=True)

    def test_add_bridge_bond(self):
        self.patch_object(ovs.subprocess, 'check_call')
        self.patch_object(ovs, '_dict_to_vsctl_set')
        self._dict_to_vsctl_set.return_value = [['--', 'fakekey=fakevalue']]
        portdata = {
            'bond-mode': 'balance-tcp',
            'lacp': 'active',
            'other-config': {
                'lacp-time': 'fast',
            },
        }
        ifdatamap = {
            'eth0': {
                'type': 'dpdk',
                'mtu-request': '9000',
                'options': {
                    'dpdk-devargs': '0000:01:00.0',
                },
            },
            'eth1': {
                'type': 'dpdk',
                'mtu-request': '9000',
                'options': {
                    'dpdk-devargs': '0000:02:00.0',
                },
            },
        }
        ovs.add_bridge_bond('br-ex', 'bond42', ['eth0', 'eth1'],
                            portdata, ifdatamap)
        self._dict_to_vsctl_set.assert_has_calls([
            mock.call(portdata, 'port', 'bond42'),
            mock.call(ifdatamap['eth0'], 'Interface', 'eth0'),
            mock.call(ifdatamap['eth1'], 'Interface', 'eth1'),
        ], any_order=True)
        self.check_call.assert_called_once_with([
            'ovs-vsctl',
            '--', '--may-exist', 'add-bond', 'br-ex', 'bond42', 'eth0', 'eth1',
            '--', 'fakekey=fakevalue',
            '--', 'fakekey=fakevalue',
            '--', 'fakekey=fakevalue'])

    def test_uuid_for_port(self):
        self.patch_object(ovs.ch_ovsdb, 'SimpleOVSDB')
        fake_uuid = uuid.UUID('efdce2cf-cd66-4060-a9f8-1db0e9a06216')
        ovsdb = mock.MagicMock()
        ovsdb.port.find.return_value = [
            {'_uuid': fake_uuid},
        ]
        self.SimpleOVSDB.return_value = ovsdb
        self.assertEquals(ovs.uuid_for_port('fake-port'), fake_uuid)
        ovsdb.port.find.assert_called_once_with('name=fake-port')

    def test_bridge_for_port(self):
        self.patch_object(ovs.ch_ovsdb, 'SimpleOVSDB')
        fake_uuid = uuid.UUID('818d03dd-efb8-44be-aba3-bde423bf1cc9')
        ovsdb = mock.MagicMock()
        ovsdb.bridge.__iter__.return_value = [
            {
                'name': 'fake-bridge',
                'ports': [fake_uuid],
            },
        ]
        self.SimpleOVSDB.return_value = ovsdb
        self.assertEquals(ovs.bridge_for_port(fake_uuid), 'fake-bridge')
        # If there is a single port on a bridge the ports property will not be
        # a list. ref: juju/charm-helpers#510
        ovsdb.bridge.__iter__.return_value = [
            {
                'name': 'fake-bridge',
                'ports': fake_uuid,
            },
        ]
        self.assertEquals(ovs.bridge_for_port(fake_uuid), 'fake-bridge')

    def test_patch_ports_on_bridge(self):
        self.patch_object(ovs.ch_ovsdb, 'SimpleOVSDB')
        self.patch_object(ovs, 'bridge_for_port')
        self.patch_object(ovs, 'uuid_for_port')
        ovsdb = mock.MagicMock()
        ovsdb.interface.find.return_value = [
            {
                'name': 'fake-interface-with-port-for-other-bridge',
                'options': {
                    'peer': 'fake-peer'
                },
            },
            {
                'name': 'fake-interface',
                'options': {
                    'peer': 'fake-peer'
                },
            },
        ]
        port_uuid = uuid.UUID('0d43905b-f80e-4eaa-9feb-a9017da8c6bc')
        ovsdb.port.find.side_effect = [
            [{
                '_uuid': port_uuid,
                'name': 'port-on-other-bridge',
            }],
            [{
                '_uuid': port_uuid,
                'name': 'fake-port',
            }],
        ]
        self.SimpleOVSDB.return_value = ovsdb
        self.bridge_for_port.side_effect = ['some-other-bridge', 'fake-bridge', 'fake-peer-bridge']
        for patch in ovs.patch_ports_on_bridge('fake-bridge'):
            self.assertEquals(
                patch,
                ovs.Patch(
                    this_end=ovs.PatchPort(
                        bridge='fake-bridge',
                        port='fake-port'),
                    other_end=ovs.PatchPort(
                        bridge='fake-peer-bridge',
                        port='fake-peer'))
            )
            break
        else:
            assert 0, 'Expected generator to provide output'
        ovsdb.port.find.side_effect = None
        ovsdb.port.find.return_value = []
        with self.assertRaises(ValueError):
            for patch in ovs.patch_ports_on_bridge('fake-bridge'):
                pass
        ovsdb.interface.find.return_value = []
        for patch in ovs.patch_ports_on_bridge('fake-bridge'):
            assert 0, 'Expected generator to provide empty iterator'
        self.assertTrue(isinstance(
            ovs.patch_ports_on_bridge('fake-bridge'), types.GeneratorType))
