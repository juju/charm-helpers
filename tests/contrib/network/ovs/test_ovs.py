import sys

import charmhelpers.contrib.network.ovs as ovs

import tests.utils as test_utils


# NOTE(fnordahl): some functions drectly under the ``contrib.network.ovs``
# module have their unit tests in the ``test_ovs.py`` module in the
# ``tests.contrib.network`` package.


class TestOVS(test_utils.BaseTestCase):

    def test_add_br(self):
        self.patch_object(ovs.utils, '_run')
        ovs.add_br('br-x', exclusive=True)
        self._run.assert_called_once_with(
            'ovs-vsctl', 'add-br', 'br-x')
        self._run.reset_mock()
        brdata = {
            'protocols': 'OpenFlow10,OpenFlow13,OpenFlow14',
            'external-ids': {
                'charm': 'managed',
            },
        }
        ovs.add_br('br-x', brdata=brdata)
        if sys.version_info >= (3, 6):
            # Skip test on Python versions prior to 3.5due to Dict ordering
            self._run.assert_called_once_with(
                'ovs-vsctl', 'add-br', 'br-x', '--may-exist',
                '--',
                'set', 'bridge', 'br-x',
                'protocols=OpenFlow10,OpenFlow13,OpenFlow14',
                '--',
                'set', 'bridge', 'br-x', 'external-ids:charm=managed')

    def test_del_br(self):
        self.patch_object(ovs.utils, '_run')
        ovs.del_br('br-x')
        self._run.assert_called_once_with(
            'ovs-vsctl', 'del-br', 'br-x')

    def test_add_port(self):
        self.patch_object(ovs.utils, '_run')
        ovs.add_port('br-x', 'enp3s0f0')
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
        ovs.add_port('br-x', 'enp3s0f0', ifdata=ifdata)
        if sys.version_info >= (3, 6):
            # Skip test on Python versions prior to 3.5due to Dict ordering
            self._run.assert_called_once_with(
                'ovs-vsctl', '--may-exist', 'add-port', 'br-x', 'enp3s0f0',
                '--',
                'set', 'Interface', 'enp3s0f0', 'type=internal',
                '--',
                'set', 'Interface', 'enp3s0f0',
                'external-ids:iface-id=fakeifid',
                '--',
                'set', 'Interface', 'enp3s0f0',
                'external-ids:iface-status=active',
                '--',
                'set', 'Interface', 'enp3s0f0',
                'external-ids:attached-mac=fakeaddr')
        self._run.reset_mock()
        ovs.add_port('br-x', 'enp3s0f0', exclusive=True)
        self._run.assert_called_once_with(
            'ovs-vsctl', 'add-port', 'br-x', 'enp3s0f0')
        self._run.reset_mock()
        ovs.add_port('br-x', 'enp3s0f0', ifdata=ifdata)
        if sys.version_info >= (3, 6):
            # Skip test on Python versions prior to 3.5due to Dict ordering
            self._run.assert_called_once_with(
                'ovs-vsctl', '--may-exist', 'add-port', 'br-x', 'enp3s0f0',
                '--',
                'set', 'Interface', 'enp3s0f0', 'type=internal',
                '--',
                'set', 'Interface', 'enp3s0f0',
                'external-ids:iface-id=fakeifid',
                '--',
                'set', 'Interface', 'enp3s0f0',
                'external-ids:iface-status=active',
                '--',
                'set', 'Interface', 'enp3s0f0',
                'external-ids:attached-mac=fakeaddr')

    def test_list_ports(self):
        self.patch_object(ovs.utils, '_run')
        self._run.return_value = '\n'
        ovs.list_ports('someBridge')
        self._run.assert_called_once_with('ovs-vsctl', 'list-ports',
                                          'someBridge')
