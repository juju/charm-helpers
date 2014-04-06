import unittest
from mock import patch
from nose.tools import raises
import charmhelpers.contrib.openstack.neutron as neutron


class NeutronTests(unittest.TestCase):
    @patch('charmhelpers.contrib.openstack.neutron.check_output')
    def test_headers_package(self, _check):
        _check.return_value = '3.13.0-19-generic'
        kname = neutron.headers_package()
        self.assertEquals(kname, 'linux-headers-3.13.0-19-generic')

    @patch('charmhelpers.contrib.openstack.neutron.check_output')
    def test_kernel_version(self, _check):
        _check.return_value = '3.13.0-19-generic'
        kver_maj, kver_min = neutron.kernel_version()
        self.assertEquals(kver_maj, 3)
        self.assertEquals(kver_min, 13)

    @patch('charmhelpers.contrib.openstack.neutron.kernel_version')
    def test_determine_dkms_package_old_kernel(self, _kernel_version):
        _kernel_version.return_value = (3, 10)
        dkms_package = neutron.determine_dkms_package()
        self.assertEquals(dkms_package, ['openvswitch-datapath-dkms'])

    @patch('charmhelpers.contrib.openstack.neutron.kernel_version')
    def test_determine_dkms_package_new_kernel(self, _kernel_version):
        _kernel_version.return_value = (3, 13)
        dkms_package = neutron.determine_dkms_package()
        self.assertEquals(dkms_package, [])

    @patch.object(neutron, 'config')
    def test_quantum_plugins(self, _config):
        _config.return_value = 'arse'
        bob = neutron.quantum_plugins()
        self.assertEquals(bob['ovs']['services'], ['quantum-plugin-openvswitch-agent'])

    @patch('charmhelpers.contrib.openstack.neutron.os_release')
    @patch.object(neutron, 'config')
    def test_neutron_plugins(self, _config, _os_release):
        _config.return_value = 'arse'
        _os_release .return_value = 'icehouse'
        bob = neutron.neutron_plugins()
        self.assertEquals(bob['ovs']['services'], ['neutron-plugin-openvswitch-agent'])

    @patch.object(neutron, 'config')
    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_quantum(self, _network_manager, _config):
        _config.return_value = 'arse'
        _network_manager.return_value = 'quantum'
        bob = neutron.neutron_plugin_attribute('ovs', 'services')
        self.assertEquals(bob, ['quantum-plugin-openvswitch-agent'])

    @patch('charmhelpers.contrib.openstack.neutron.os_release')
    @patch.object(neutron, 'config')
    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_neutron(self, _network_manager, _config, _os_release):
        _config.return_value = 'arse'
        _os_release .return_value = 'icehouse'
        _network_manager.return_value = 'neutron'
        bob = neutron.neutron_plugin_attribute('ovs', 'services')
        self.assertEquals(bob, ['neutron-plugin-openvswitch-agent'])

    @raises(Exception)
    @patch.object(neutron, 'log')
    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_another(self, _network_manager, _log):
        _network_manager.return_value = 'another'
        self.assertRaises(Exception, neutron.neutron_plugin_attribute('ovs', 'services'))

    @raises(Exception)
    @patch.object(neutron, 'log')
    @patch.object(neutron, 'config')
    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_plugin_keyerror(self, _network_manager, _config, _log):
        _config.return_value = 'arse'
        _network_manager.return_value = 'quantum'
        self.assertRaises(Exception, neutron.neutron_plugin_attribute('foo', 'foo'))

    @patch.object(neutron, 'config')
    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_attr_keyerror(self, _network_manager, _config):
        _config.return_value = 'arse'
        _network_manager.return_value = 'quantum'
        bob = neutron.neutron_plugin_attribute('ovs', 'foo')
        self.assertEquals(bob, None)

    @raises(Exception)
    @patch.object(neutron, 'os_release')
    @patch.object(neutron, 'config')
    @patch.object(neutron, 'log')
    def test_network_manager_essex(self, _log, _config, _os_release):
        essex_cases = {
            'quantum': 'quantum',
            'neutron': 'quantum',
            'newhotness': 'newhotness',
        }
        for nwmanager in essex_cases:
            _config.return_value = nwmanager
            _os_release.return_value = 'essex'
            self.assertRaises(Exception, neutron.network_manager())

    @patch.object(neutron, 'os_release')
    @patch.object(neutron, 'config')
    def test_network_manager_folsom(self, _config, _os_release):
        folsom_cases = {
            'quantum': 'quantum',
            'neutron': 'quantum',
            'newhotness': 'newhotness',
        }
        for nwmanager in folsom_cases:
            _config.return_value = nwmanager
            _os_release.return_value = 'folsom'
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, folsom_cases[nwmanager])

    @patch.object(neutron, 'os_release')
    @patch.object(neutron, 'config')
    def test_network_manager_grizzly(self, _config, _os_release):
        grizzly_cases = {
            'quantum': 'quantum',
            'neutron': 'quantum',
            'newhotness': 'newhotness',
        }
        for nwmanager in grizzly_cases:
            _config.return_value = nwmanager
            _os_release.return_value = 'grizzly'
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, grizzly_cases[nwmanager])

    @patch.object(neutron, 'os_release')
    @patch.object(neutron, 'config')
    def test_network_manager_icehouse(self, _config, _os_release):
        icehouse_cases = {
            'quantum': 'neutron',
            'neutron': 'neutron',
            'newhotness': 'newhotness',
        }
        for nwmanager in icehouse_cases:
            _config.return_value = nwmanager
            _os_release.return_value = 'icehouse'
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, icehouse_cases[nwmanager])
