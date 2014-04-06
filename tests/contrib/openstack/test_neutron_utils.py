import unittest
from mock import patch
from nose.tools import raises
import charmhelpers.contrib.openstack.neutron as neutron

TO_PATCH = [
    'log',
    'config',
    'os_release',
    'check_output',
]


class NeutronTests(unittest.TestCase):
    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.openstack.neutron.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_headers_package(self):
        self.check_output.return_value = '3.13.0-19-generic'
        kname = neutron.headers_package()
        self.assertEquals(kname, 'linux-headers-3.13.0-19-generic')

    def test_kernel_version(self):
        self.check_output.return_value = '3.13.0-19-generic'
        kver_maj, kver_min = neutron.kernel_version()
        self.assertEquals(kver_maj, 3)
        self.assertEquals(kver_min, 13)

    @patch.object(neutron, 'kernel_version')
    def test_determine_dkms_package_old_kernel(self, _kernel_version):
        _kernel_version.return_value = (3, 10)
        dkms_package = neutron.determine_dkms_package()
        self.assertEquals(dkms_package, ['openvswitch-datapath-dkms'])

    @patch.object(neutron, 'kernel_version')
    def test_determine_dkms_package_new_kernel(self, _kernel_version):
        _kernel_version.return_value = (3, 13)
        dkms_package = neutron.determine_dkms_package()
        self.assertEquals(dkms_package, [])

    def test_quantum_plugins(self):
        self.config.return_value = 'arse'
        bob = neutron.quantum_plugins()
        self.assertEquals(bob['ovs']['services'], ['quantum-plugin-openvswitch-agent'])

    def test_neutron_plugins(self):
        self.config.return_value = 'arse'
        self.os_release .return_value = 'icehouse'
        bob = neutron.neutron_plugins()
        self.assertEquals(bob['ovs']['services'], ['neutron-plugin-openvswitch-agent'])

    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_quantum(self, _network_manager):
        self.config.return_value = 'arse'
        _network_manager.return_value = 'quantum'
        bob = neutron.neutron_plugin_attribute('ovs', 'services')
        self.assertEquals(bob, ['quantum-plugin-openvswitch-agent'])

    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_neutron(self, _network_manager):
        self.config.return_value = 'arse'
        self.os_release .return_value = 'icehouse'
        _network_manager.return_value = 'neutron'
        bob = neutron.neutron_plugin_attribute('ovs', 'services')
        self.assertEquals(bob, ['neutron-plugin-openvswitch-agent'])

    @raises(Exception)
    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_another(self, _network_manager):
        _network_manager.return_value = 'another'
        self.assertRaises(Exception, neutron.neutron_plugin_attribute('ovs', 'services'))

    @raises(Exception)
    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_plugin_keyerror(self, _network_manager):
        self.config.return_value = 'arse'
        _network_manager.return_value = 'quantum'
        self.assertRaises(Exception, neutron.neutron_plugin_attribute('foo', 'foo'))

    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_attr_keyerror(self, _network_manager):
        self.config.return_value = 'arse'
        _network_manager.return_value = 'quantum'
        bob = neutron.neutron_plugin_attribute('ovs', 'foo')
        self.assertEquals(bob, None)

    @raises(Exception)
    def test_network_manager_essex(self):
        essex_cases = {
            'quantum': 'quantum',
            'neutron': 'quantum',
            'newhotness': 'newhotness',
        }
        for nwmanager in essex_cases:
            self.config.return_value = nwmanager
            self.os_release.return_value = 'essex'
            self.assertRaises(Exception, neutron.network_manager())

    def test_network_manager_folsom(self):
        folsom_cases = {
            'quantum': 'quantum',
            'neutron': 'quantum',
            'newhotness': 'newhotness',
        }
        for nwmanager in folsom_cases:
            self.config.return_value = nwmanager
            self.os_release.return_value = 'folsom'
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, folsom_cases[nwmanager])

    def test_network_manager_grizzly(self):
        grizzly_cases = {
            'quantum': 'quantum',
            'neutron': 'quantum',
            'newhotness': 'newhotness',
        }
        for nwmanager in grizzly_cases:
            self.config.return_value = nwmanager
            self.os_release.return_value = 'grizzly'
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, grizzly_cases[nwmanager])

    def test_network_manager_icehouse(self):
        icehouse_cases = {
            'quantum': 'neutron',
            'neutron': 'neutron',
            'newhotness': 'newhotness',
        }
        for nwmanager in icehouse_cases:
            self.config.return_value = nwmanager
            self.os_release.return_value = 'icehouse'
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, icehouse_cases[nwmanager])
