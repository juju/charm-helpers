from testtools import TestCase
from mock import patch, call, MagicMock

import charmhelpers.core as ch_core
import charmhelpers.contrib.openstack.ip as ip

TO_PATCH = [
    'config',
    'unit_get',
    'get_address_in_network',
    'is_clustered',
    'service_name',
    'network_get_primary_address',
    'resolve_network_cidr',
]


class TestConfig():

    def __init__(self):
        self.config = {}

    def set(self, key, value):
        self.config[key] = value

    def get(self, key):
        return self.config.get(key)


class IPTestCase(TestCase):

    def setUp(self):
        super(IPTestCase, self).setUp()
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        self.test_config = TestConfig()
        self.config.side_effect = self.test_config.get
        self.network_get_primary_address.side_effect = [
            NotImplementedError,
            ch_core.hookenv.NoNetworkBinding,
        ]

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.openstack.ip.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_resolve_address_default(self):
        self.is_clustered.return_value = False
        self.unit_get.return_value = 'unit1'
        self.get_address_in_network.return_value = 'unit1'
        self.assertEquals(ip.resolve_address(), 'unit1')
        self.unit_get.assert_called_with('public-address')
        calls = [call('os-public-network'),
                 call('prefer-ipv6')]
        self.config.assert_has_calls(calls)

    def test_resolve_address_default_internal(self):
        self.is_clustered.return_value = False
        self.unit_get.return_value = 'unit1'
        self.get_address_in_network.return_value = 'unit1'
        self.assertEquals(ip.resolve_address(ip.INTERNAL), 'unit1')
        self.unit_get.assert_called_with('private-address')
        calls = [call('os-internal-network'),
                 call('prefer-ipv6')]
        self.config.assert_has_calls(calls)

    def test_resolve_address_public_not_clustered(self):
        self.is_clustered.return_value = False
        self.test_config.set('os-public-network', '192.168.20.0/24')
        self.unit_get.return_value = 'unit1'
        self.get_address_in_network.return_value = '192.168.20.1'
        self.assertEquals(ip.resolve_address(), '192.168.20.1')
        self.unit_get.assert_called_with('public-address')
        calls = [call('os-public-network'),
                 call('prefer-ipv6')]
        self.config.assert_has_calls(calls)
        self.get_address_in_network.assert_called_with(
            '192.168.20.0/24',
            'unit1')

    def test_resolve_address_public_clustered(self):
        self.is_clustered.return_value = True
        self.test_config.set('os-public-network', '192.168.20.0/24')
        self.test_config.set('vip', '192.168.20.100 10.5.3.1')
        self.assertEquals(ip.resolve_address(), '192.168.20.100')

    def test_resolve_address_default_clustered(self):
        self.is_clustered.return_value = True
        self.test_config.set('vip', '10.5.3.1')
        self.assertEquals(ip.resolve_address(), '10.5.3.1')
        self.config.assert_has_calls(
            [call('vip'),
             call('os-public-network')])

    def test_resolve_address_public_clustered_inresolvable(self):
        self.is_clustered.return_value = True
        self.test_config.set('os-public-network', '192.168.20.0/24')
        self.test_config.set('vip', '10.5.3.1')
        self.assertRaises(ValueError, ip.resolve_address)

    def test_resolve_address_override(self):
        self.test_config.set('os-public-hostname', 'public.example.com')
        addr = ip.resolve_address()
        self.assertEqual('public.example.com', addr)

    @patch.object(ip, '_get_address_override')
    def test_resolve_address_no_override(self, _get_address_override):
        self.test_config.set('os-public-hostname', 'public.example.com')
        self.unit_get.return_value = '10.0.0.1'
        addr = ip.resolve_address(override=False)
        self.assertFalse(_get_address_override.called)
        self.assertEqual('10.0.0.1', addr)

    def test_resolve_address_override_template(self):
        self.test_config.set('os-public-hostname',
                             '{service_name}.example.com')
        self.service_name.return_value = 'foo'
        addr = ip.resolve_address()
        self.assertEqual('foo.example.com', addr)

    @patch.object(ip, 'get_ipv6_addr', lambda *args, **kwargs: ['::1'])
    def test_resolve_address_ipv6_fallback(self):
        self.test_config.set('prefer-ipv6', True)
        self.is_clustered.return_value = False
        self.assertEqual(ip.resolve_address(), '::1')

    @patch.object(ip, 'resolve_address')
    def test_canonical_url_http(self, resolve_address):
        resolve_address.return_value = 'unit1'
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        self.assertTrue(ip.canonical_url(configs),
                        'http://unit1')

    @patch.object(ip, 'resolve_address')
    def test_canonical_url_https(self, resolve_address):
        resolve_address.return_value = 'unit1'
        configs = MagicMock()
        configs.complete_contexts.return_value = ['https']
        self.assertTrue(ip.canonical_url(configs),
                        'https://unit1')

    @patch.object(ip, 'is_ipv6', lambda *args: True)
    @patch.object(ip, 'resolve_address')
    def test_canonical_url_ipv6(self, resolve_address):
        resolve_address.return_value = 'unit1'
        self.assertTrue(ip.canonical_url(None), 'http://[unit1]')

    @patch.object(ip, 'local_address')
    def test_resolve_address_network_get(self, local_address):
        self.is_clustered.return_value = False
        self.unit_get.return_value = 'unit1'
        self.network_get_primary_address.side_effect = None
        self.network_get_primary_address.return_value = '10.5.60.1'
        self.assertEqual(ip.resolve_address(), '10.5.60.1')
        local_address.assert_called_once_with(
            unit_get_fallback='public-address')
        calls = [call('os-public-network'),
                 call('prefer-ipv6')]
        self.config.assert_has_calls(calls)
        self.network_get_primary_address.assert_called_with('public')

    def test_resolve_address_network_get_clustered(self):
        self.is_clustered.return_value = True
        self.test_config.set('vip', '10.5.60.20 192.168.1.20')
        self.network_get_primary_address.side_effect = None
        self.network_get_primary_address.return_value = '10.5.60.1'
        self.resolve_network_cidr.return_value = '10.5.60.1/24'
        self.assertEqual(ip.resolve_address(), '10.5.60.20')
        calls = [call('os-public-hostname'),
                 call('vip'),
                 call('os-public-network')]
        self.config.assert_has_calls(calls)
        self.network_get_primary_address.assert_called_with('public')
