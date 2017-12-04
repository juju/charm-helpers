from mock import patch
import unittest

from charmhelpers.contrib.openstack.ha import utils as ha


class HATests(unittest.TestCase):
    def setUp(self):
        super(HATests, self).setUp()
        [self._patch(m) for m in [
            'charm_name',
            'config',
            'relation_set',
            'resolve_address',
            'status_set',
        ]]
        self.resources = {'res_test_haproxy': 'lsb:haproxy'}
        self.resource_params = {'res_test_haproxy': 'op monitor interval="5s"'}
        self.conf = {}
        self.config.side_effect = lambda key: self.conf.get(key)

    def _patch(self, method):
        _m = patch.object(ha, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

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

    @patch.object(ha, 'assert_charm_supports_dns_ha')
    def test_update_dns_ha_resource_params_one(self,
                                               assert_charm_supports_dns_ha):
        EXPECTED_RESOURCES = {'res_test_public_hostname': 'ocf:maas:dns',
                              'res_test_haproxy': 'lsb:haproxy'}
        EXPECTED_RESOURCE_PARAMS = {
            'res_test_public_hostname': ('params fqdn="test.maas" '
                                         'ip_address="10.0.0.1" '),
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

    @patch.object(ha, 'assert_charm_supports_dns_ha')
    def test_update_dns_ha_resource_params_all(self,
                                               assert_charm_supports_dns_ha):
        EXPECTED_RESOURCES = {'res_test_admin_hostname': 'ocf:maas:dns',
                              'res_test_int_hostname': 'ocf:maas:dns',
                              'res_test_public_hostname': 'ocf:maas:dns',
                              'res_test_haproxy': 'lsb:haproxy'}
        EXPECTED_RESOURCE_PARAMS = {
            'res_test_admin_hostname': ('params fqdn="test.admin.maas" '
                                        'ip_address="10.0.0.1" '),
            'res_test_int_hostname': ('params fqdn="test.internal.maas" '
                                      'ip_address="10.0.0.1" '),
            'res_test_public_hostname': ('params fqdn="test.public.maas" '
                                         'ip_address="10.0.0.1" '),
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
