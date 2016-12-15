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
        self.check_output.return_value = b'3.13.0-19-generic'
        kname = neutron.headers_package()
        self.assertEquals(kname, 'linux-headers-3.13.0-19-generic')

    def test_kernel_version(self):
        self.check_output.return_value = b'3.13.0-19-generic'
        kver_maj, kver_min = neutron.kernel_version()
        self.assertEquals((kver_maj, kver_min), (3, 13))

    @patch.object(neutron, 'kernel_version')
    def test_determine_dkms_package_old_kernel(self, _kernel_version):
        self.check_output.return_value = b'3.4.0-19-generic'
        _kernel_version.return_value = (3, 10)
        dkms_package = neutron.determine_dkms_package()
        self.assertEquals(dkms_package, ['linux-headers-3.4.0-19-generic',
                                         'openvswitch-datapath-dkms'])

    @patch.object(neutron, 'kernel_version')
    def test_determine_dkms_package_new_kernel(self, _kernel_version):
        _kernel_version.return_value = (3, 13)
        dkms_package = neutron.determine_dkms_package()
        self.assertEquals(dkms_package, [])

    def test_quantum_plugins(self):
        self.config.return_value = 'foo'
        plugins = neutron.quantum_plugins()
        self.assertEquals(plugins['ovs']['services'],
                          ['quantum-plugin-openvswitch-agent'])
        self.assertEquals(plugins['nvp']['services'], [])

    def test_neutron_plugins_preicehouse(self):
        self.config.return_value = 'foo'
        self.os_release.return_value = 'havana'
        plugins = neutron.neutron_plugins()
        self.assertEquals(plugins['ovs']['config'],
                          '/etc/neutron/plugins/openvswitch/ovs_neutron_plugin.ini')
        self.assertEquals(plugins['nvp']['services'], [])

    def test_neutron_plugins(self):
        self.config.return_value = 'foo'
        self.os_release.return_value = 'icehouse'
        plugins = neutron.neutron_plugins()
        self.assertEquals(plugins['ovs']['config'],
                          '/etc/neutron/plugins/ml2/ml2_conf.ini')
        self.assertEquals(plugins['nvp']['config'],
                          '/etc/neutron/plugins/vmware/nsx.ini')
        self.assertTrue('neutron-plugin-vmware' in
                        plugins['nvp']['server_packages'])
        self.assertEquals(plugins['n1kv']['config'],
                          '/etc/neutron/plugins/cisco/cisco_plugins.ini')
        self.assertEquals(plugins['Calico']['config'],
                          '/etc/neutron/plugins/ml2/ml2_conf.ini')
        self.assertEquals(plugins['plumgrid']['config'],
                          '/etc/neutron/plugins/plumgrid/plumgrid.ini')
        self.assertEquals(plugins['midonet']['config'],
                          '/etc/neutron/plugins/midonet/midonet.ini')

        self.assertEquals(plugins['nvp']['services'], [])
        self.assertEquals(plugins['nsx'], plugins['nvp'])

        self.os_release.return_value = 'kilo'
        plugins = neutron.neutron_plugins()
        self.assertEquals(plugins['midonet']['driver'],
                          'neutron.plugins.midonet.plugin.MidonetPluginV2')
        self.assertEquals(plugins['nsx']['config'],
                          '/etc/neutron/plugins/vmware/nsx.ini')

        self.os_release.return_value = 'liberty'
        self.config.return_value = 'mem-1.9'
        plugins = neutron.neutron_plugins()
        self.assertEquals(plugins['midonet']['driver'],
                          'midonet.neutron.plugin_v1.MidonetPluginV2')
        self.assertTrue('python-networking-midonet' in
                        plugins['midonet']['server_packages'])

        self.os_release.return_value = 'mitaka'
        self.config.return_value = 'mem-1.9'
        plugins = neutron.neutron_plugins()
        self.assertEquals(plugins['nsx']['config'],
                          '/etc/neutron/nsx.ini')
        self.assertTrue('python-vmware-nsx' in
                        plugins['nsx']['server_packages'])

    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_quantum(self, _network_manager):
        self.config.return_value = 'foo'
        _network_manager.return_value = 'quantum'
        plugins = neutron.neutron_plugin_attribute('ovs', 'services')
        self.assertEquals(plugins, ['quantum-plugin-openvswitch-agent'])

    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_neutron(self, _network_manager):
        self.config.return_value = 'foo'
        self.os_release.return_value = 'icehouse'
        _network_manager.return_value = 'neutron'
        plugins = neutron.neutron_plugin_attribute('ovs', 'services')
        self.assertEquals(plugins, ['neutron-plugin-openvswitch-agent'])

    @raises(Exception)
    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_foo(self, _network_manager):
        _network_manager.return_value = 'foo'
        self.assertRaises(Exception, neutron.neutron_plugin_attribute('ovs', 'services'))

    @raises(Exception)
    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_plugin_keyerror(self, _network_manager):
        self.config.return_value = 'foo'
        _network_manager.return_value = 'quantum'
        self.assertRaises(Exception, neutron.neutron_plugin_attribute('foo', 'foo'))

    @patch.object(neutron, 'network_manager')
    def test_neutron_plugin_attribute_attr_keyerror(self, _network_manager):
        self.config.return_value = 'foo'
        _network_manager.return_value = 'quantum'
        plugins = neutron.neutron_plugin_attribute('ovs', 'foo')
        self.assertEquals(plugins, None)

    @raises(Exception)
    def test_network_manager_essex(self):
        essex_cases = {
            'quantum': 'quantum',
            'neutron': 'quantum',
            'newhotness': 'newhotness',
        }
        self.os_release.return_value = 'essex'
        for nwmanager in essex_cases:
            self.config.return_value = nwmanager
            self.assertRaises(Exception, neutron.network_manager())

    def test_network_manager_folsom(self):
        folsom_cases = {
            'quantum': 'quantum',
            'neutron': 'quantum',
            'newhotness': 'newhotness',
        }
        self.os_release.return_value = 'folsom'
        for nwmanager in folsom_cases:
            self.config.return_value = nwmanager
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, folsom_cases[nwmanager])

    def test_network_manager_grizzly(self):
        grizzly_cases = {
            'quantum': 'quantum',
            'neutron': 'quantum',
            'newhotness': 'newhotness',
        }
        self.os_release.return_value = 'grizzly'
        for nwmanager in grizzly_cases:
            self.config.return_value = nwmanager
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, grizzly_cases[nwmanager])

    def test_network_manager_havana(self):
        havana_cases = {
            'quantum': 'neutron',
            'neutron': 'neutron',
            'newhotness': 'newhotness',
        }
        self.os_release.return_value = 'havana'
        for nwmanager in havana_cases:
            self.config.return_value = nwmanager
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, havana_cases[nwmanager])

    def test_network_manager_icehouse(self):
        icehouse_cases = {
            'quantum': 'neutron',
            'neutron': 'neutron',
            'newhotness': 'newhotness',
        }
        self.os_release.return_value = 'icehouse'
        for nwmanager in icehouse_cases:
            self.config.return_value = nwmanager
            renamed_manager = neutron.network_manager()
            self.assertEquals(renamed_manager, icehouse_cases[nwmanager])

    def test_parse_bridge_mappings(self):
        ret = neutron.parse_bridge_mappings(None)
        self.assertEqual(ret, {})
        ret = neutron.parse_bridge_mappings("physnet1:br0")
        self.assertEqual(ret, {'physnet1': 'br0'})
        ret = neutron.parse_bridge_mappings("physnet1:br0 physnet2:br1")
        self.assertEqual(ret, {'physnet1': 'br0', 'physnet2': 'br1'})

    def test_parse_data_port_mappings(self):
        ret = neutron.parse_data_port_mappings(None)
        self.assertEqual(ret, {})
        ret = neutron.parse_data_port_mappings('br0:eth0')
        self.assertEqual(ret, {'eth0': 'br0'})
        # Back-compat test
        ret = neutron.parse_data_port_mappings('eth0', default_bridge='br0')
        self.assertEqual(ret, {'eth0': 'br0'})
        # Multiple mappings
        ret = neutron.parse_data_port_mappings('br0:eth0 br1:eth1')
        self.assertEqual(ret, {'eth0': 'br0', 'eth1': 'br1'})
        # MultMAC mappings
        ret = neutron.parse_data_port_mappings('br0:cb:23:ae:72:f2:33 '
                                               'br0:fa:16:3e:12:97:8e')
        self.assertEqual(ret, {'cb:23:ae:72:f2:33': 'br0',
                               'fa:16:3e:12:97:8e': 'br0'})

    def test_parse_vlan_range_mappings(self):
        ret = neutron.parse_vlan_range_mappings(None)
        self.assertEqual(ret, {})
        ret = neutron.parse_vlan_range_mappings('physnet1:1001:2000')
        self.assertEqual(ret, {'physnet1': ('1001', '2000')})
        ret = neutron.parse_vlan_range_mappings('physnet1:1001:2000 physnet2:2001:3000')
        self.assertEqual(ret, {'physnet1': ('1001', '2000'),
                               'physnet2': ('2001', '3000')})
        ret = neutron.parse_vlan_range_mappings('physnet1 physnet2:2001:3000')
        self.assertEqual(ret, {'physnet1': ('',),
                               'physnet2': ('2001', '3000')})
