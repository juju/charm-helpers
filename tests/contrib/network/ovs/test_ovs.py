import mock

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

    def test_ovs_appctl(self):
        self.patch_object(ovs.subprocess, 'check_output')
        ovs.ovs_appctl('ovs-vswitchd', ('ofproto/list',))
        self.check_output.assert_called_once_with(
            ['ovs-appctl', '-t', 'ovs-vswitchd', 'ofproto/list'],
            universal_newlines=True)
