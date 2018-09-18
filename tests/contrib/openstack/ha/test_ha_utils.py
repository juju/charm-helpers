from mock import patch
import unittest
import json

from charmhelpers.contrib.openstack.ha import utils as ha

IFACE_LOOKUPS = {
    '10.5.100.1': 'eth1',
    'ffff::1': 'eth1',
    'ffaa::1': 'eth2',
}

NETMASK_LOOKUPS = {
    '10.5.100.1': '255.255.255.0',
    'ffff::1': '64',
    'ffaa::1': '32',
}


class HATests(unittest.TestCase):
    def setUp(self):
        super(HATests, self).setUp()
        [self._patch(m) for m in [
            'charm_name',
            'config',
            'relation_set',
            'resolve_address',
            'status_set',
            'get_hacluster_config',
            'get_iface_for_address',
            'get_netmask_for_address',
        ]]
        self.resources = {'res_test_haproxy': 'lsb:haproxy'}
        self.resource_params = {'res_test_haproxy': 'op monitor interval="5s"'}
        self.conf = {}
        self.config.side_effect = lambda key: self.conf.get(key)
        self.maxDiff = None
        self.get_iface_for_address.side_effect = \
            lambda x: IFACE_LOOKUPS.get(x)
        self.get_netmask_for_address.side_effect = \
            lambda x: NETMASK_LOOKUPS.get(x)

    def _patch(self, method):
        _m = patch.object(ha, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    @patch.object(ha, 'log', lambda *args, **kwargs: None)
    @patch.object(ha, 'assert_charm_supports_dns_ha')
    def test_update_dns_ha_resource_params_none(self,
                                                assert_charm_supports_dns_ha):
        self.conf = {
            'os-admin-hostname': None,
            'os-internal-hostname': None,
            'os-public-hostname': None,
        }

        with self.assertRaises(ha.DNSHAException):
            ha.update_dns_ha_resource_params(
                relation_id='ha:1',
                resources=self.resources,
                resource_params=self.resource_params)

    @patch.object(ha, 'log', lambda *args, **kwargs: None)
    @patch.object(ha, 'assert_charm_supports_dns_ha')
    def test_update_dns_ha_resource_params_one(self,
                                               assert_charm_supports_dns_ha):
        EXPECTED_RESOURCES = {'res_test_public_hostname': 'ocf:maas:dns',
                              'res_test_haproxy': 'lsb:haproxy'}
        EXPECTED_RESOURCE_PARAMS = {
            'res_test_public_hostname': ('params fqdn="test.maas" '
                                         'ip_address="10.0.0.1"'),
            'res_test_haproxy': 'op monitor interval="5s"'}

        self.conf = {
            'os-admin-hostname': None,
            'os-internal-hostname': None,
            'os-public-hostname': 'test.maas',
        }

        self.charm_name.return_value = 'test'
        self.resolve_address.return_value = '10.0.0.1'
        ha.update_dns_ha_resource_params(relation_id='ha:1',
                                         resources=self.resources,
                                         resource_params=self.resource_params)
        self.assertEqual(self.resources, EXPECTED_RESOURCES)
        self.assertEqual(self.resource_params, EXPECTED_RESOURCE_PARAMS)
        self.relation_set.assert_called_with(
            groups={'grp_test_hostnames': 'res_test_public_hostname'},
            relation_id='ha:1')

    @patch.object(ha, 'log', lambda *args, **kwargs: None)
    @patch.object(ha, 'assert_charm_supports_dns_ha')
    def test_update_dns_ha_resource_params_all(self,
                                               assert_charm_supports_dns_ha):
        EXPECTED_RESOURCES = {'res_test_admin_hostname': 'ocf:maas:dns',
                              'res_test_int_hostname': 'ocf:maas:dns',
                              'res_test_public_hostname': 'ocf:maas:dns',
                              'res_test_haproxy': 'lsb:haproxy'}
        EXPECTED_RESOURCE_PARAMS = {
            'res_test_admin_hostname': ('params fqdn="test.admin.maas" '
                                        'ip_address="10.0.0.1"'),
            'res_test_int_hostname': ('params fqdn="test.internal.maas" '
                                      'ip_address="10.0.0.1"'),
            'res_test_public_hostname': ('params fqdn="test.public.maas" '
                                         'ip_address="10.0.0.1"'),
            'res_test_haproxy': 'op monitor interval="5s"'}

        self.conf = {
            'os-admin-hostname': 'test.admin.maas',
            'os-internal-hostname': 'test.internal.maas',
            'os-public-hostname': 'test.public.maas',
        }

        self.charm_name.return_value = 'test'
        self.resolve_address.return_value = '10.0.0.1'
        ha.update_dns_ha_resource_params(relation_id='ha:1',
                                         resources=self.resources,
                                         resource_params=self.resource_params)
        self.assertEqual(self.resources, EXPECTED_RESOURCES)
        self.assertEqual(self.resource_params, EXPECTED_RESOURCE_PARAMS)
        self.relation_set.assert_called_with(
            groups={'grp_test_hostnames':
                    ('res_test_admin_hostname '
                     'res_test_int_hostname '
                     'res_test_public_hostname')},
            relation_id='ha:1')

    @patch.object(ha, 'lsb_release')
    def test_assert_charm_supports_dns_ha(self, lsb_release):
        lsb_release.return_value = {'DISTRIB_RELEASE': '16.04'}
        self.assertTrue(ha.assert_charm_supports_dns_ha())

    @patch.object(ha, 'lsb_release')
    def test_assert_charm_supports_dns_ha_exception(self, lsb_release):
        lsb_release.return_value = {'DISTRIB_RELEASE': '12.04'}
        self.assertRaises(ha.DNSHAException,
                          lambda: ha.assert_charm_supports_dns_ha())

    def tests_expect_ha(self):
        self.conf = {'vip': None,
                     'dns-ha': None}
        self.assertFalse(ha.expect_ha())

        self.conf = {'vip': '10.0.0.1',
                     'dns-ha': None}
        self.assertTrue(ha.expect_ha())

        self.conf = {'vip': None,
                     'dns-ha': True}
        self.assertTrue(ha.expect_ha())

    def test_update_hacluster_vip_single_vip(self):
        self.get_hacluster_config.return_value = {
            'vip': '10.5.100.1'
        }
        test_data = {'resources': {}, 'resource_params': {}}
        expected = {
            'groups': {
                'grp_testservice_vips': 'res_testservice_eth1_vip'
            },
            'resource_params': {
                'res_testservice_eth1_vip': ('params ip="10.5.100.1"'
                                             ' cidr_netmask="255.255.255.0"'
                                             ' nic="eth1"')
            },
            'resources': {
                'res_testservice_eth1_vip': 'ocf:heartbeat:IPaddr2'
            }
        }
        ha.update_hacluster_vip('testservice', test_data)
        self.assertEqual(test_data, expected)

    def test_update_hacluster_vip_multiple_vip(self):
        self.get_hacluster_config.return_value = {
            'vip': '10.5.100.1 ffff::1 ffaa::1'
        }
        test_data = {'resources': {}, 'resource_params': {}}
        expected = {
            'groups': {
                'grp_testservice_vips': ('res_testservice_eth1_vip '
                                         'res_testservice_eth1_vip_ipv6addr '
                                         'res_testservice_eth2_vip')
            },
            'resource_params': {
                'res_testservice_eth1_vip': ('params ip="10.5.100.1"'
                                             ' cidr_netmask="255.255.255.0"'
                                             ' nic="eth1"'),
                'res_testservice_eth1_vip_ipv6addr': ('params ipv6addr="ffff::1"'
                                                      ' cidr_netmask="64"'
                                                      ' nic="eth1"'),
                'res_testservice_eth2_vip': ('params ipv6addr="ffaa::1"'
                                             ' cidr_netmask="32"'
                                             ' nic="eth2"'),
            },
            'resources': {
                'res_testservice_eth1_vip': 'ocf:heartbeat:IPaddr2',
                'res_testservice_eth1_vip_ipv6addr': 'ocf:heartbeat:IPv6addr',
                'res_testservice_eth2_vip': 'ocf:heartbeat:IPv6addr',
            }
        }
        ha.update_hacluster_vip('testservice', test_data)
        self.assertEqual(test_data, expected)

    def test_generate_ha_relation_data(self):
        self.get_hacluster_config.return_value = {
            'vip': '10.5.100.1 ffff::1 ffaa::1'
        }
        expected = {
            'groups': {
                'grp_testservice_vips': ('res_testservice_eth1_vip '
                                         'res_testservice_eth1_vip_ipv6addr '
                                         'res_testservice_eth2_vip')
            },
            'resource_params': {
                'res_testservice_eth1_vip': ('params ip="10.5.100.1"'
                                             ' cidr_netmask="255.255.255.0"'
                                             ' nic="eth1"'),
                'res_testservice_eth1_vip_ipv6addr': ('params ipv6addr="ffff::1"'
                                                      ' cidr_netmask="64"'
                                                      ' nic="eth1"'),
                'res_testservice_eth2_vip': ('params ipv6addr="ffaa::1"'
                                             ' cidr_netmask="32"'
                                             ' nic="eth2"'),
                'res_testservice_haproxy': 'op monitor interval="5s"',
            },
            'resources': {
                'res_testservice_eth1_vip': 'ocf:heartbeat:IPaddr2',
                'res_testservice_eth1_vip_ipv6addr': 'ocf:heartbeat:IPv6addr',
                'res_testservice_eth2_vip': 'ocf:heartbeat:IPv6addr',
                'res_testservice_haproxy': 'lsb:haproxy',
            },
            'clones': {
                'cl_testservice_haproxy': 'res_testservice_haproxy',
            },
            'init_services': {
                'res_testservice_haproxy': 'haproxy'
            },
        }
        expected = {
            'json_{}'.format(k): json.dumps(v, **ha.JSON_ENCODE_OPTIONS)
            for k, v in expected.items() if v
        }
        self.assertEqual(ha.generate_ha_relation_data('testservice'),
                         expected)

    @patch.object(ha, 'log')
    @patch.object(ha, 'assert_charm_supports_dns_ha')
    def test_generate_ha_relation_data_dns_ha(self,
                                              assert_charm_supports_dns_ha,
                                              log):
        self.get_hacluster_config.return_value = {
            'vip': '10.5.100.1 ffff::1 ffaa::1'
        }
        self.conf = {
            'os-admin-hostname': 'test.admin.maas',
            'os-internal-hostname': 'test.internal.maas',
            'os-public-hostname': 'test.public.maas',
            'dns-ha': True,
        }
        self.resolve_address.return_value = '10.0.0.1'
        assert_charm_supports_dns_ha.return_value = True
        expected = {
            'groups': {
                'grp_testservice_hostnames': ('res_testservice_admin_hostname'
                                              ' res_testservice_int_hostname'
                                              ' res_testservice_public_hostname')
            },
            'resource_params': {
                'res_testservice_admin_hostname': ('params fqdn="test.admin.maas"'
                                                   ' ip_address="10.0.0.1"'),
                'res_testservice_int_hostname': ('params fqdn="test.internal.maas"'
                                                 ' ip_address="10.0.0.1"'),
                'res_testservice_public_hostname': ('params fqdn="test.public.maas"'
                                                    ' ip_address="10.0.0.1"'),
                'res_testservice_haproxy': 'op monitor interval="5s"',
            },
            'resources': {
                'res_testservice_admin_hostname': 'ocf:maas:dns',
                'res_testservice_int_hostname': 'ocf:maas:dns',
                'res_testservice_public_hostname': 'ocf:maas:dns',
                'res_testservice_haproxy': 'lsb:haproxy',
            },
            'clones': {
                'cl_testservice_haproxy': 'res_testservice_haproxy',
            },
            'init_services': {
                'res_testservice_haproxy': 'haproxy'
            },
        }
        expected = {
            'json_{}'.format(k): json.dumps(v, **ha.JSON_ENCODE_OPTIONS)
            for k, v in expected.items() if v
        }
        self.assertEqual(ha.generate_ha_relation_data('testservice'),
                         expected)
