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

    def test_update_dns_ha_resource_params_none(self):
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

    def test_update_dns_ha_resource_params_one(self):
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

    def test_update_dns_ha_resource_params_all(self):
        EXPECTED_RESOURCES = {'res_test_admin_hostname': 'ocf:maas:dns',
                              'res_test_internal_hostname': 'ocf:maas:dns',
                              'res_test_public_hostname': 'ocf:maas:dns',
                              'res_test_haproxy': 'lsb:haproxy'}
        EXPECTED_RESOURCE_PARAMS = {
            'res_test_admin_hostname': ('params fqdn="test.admin.maas" '
                                        'ip_address="10.0.0.1" '),
            'res_test_internal_hostname': ('params fqdn="test.internal.maas" '
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
                     'res_test_internal_hostname '
                     'res_test_public_hostname')},
            relation_id='ha:1')
