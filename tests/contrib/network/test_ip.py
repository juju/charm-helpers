import subprocess
import unittest

import mock
import netifaces

import charmhelpers.contrib.network.ip as net_ip
from mock import patch

DUMMY_ADDRESSES = {
    'lo': {
        17: [{'peer': '00:00:00:00:00:00',
              'addr': '00:00:00:00:00:00'}],
        2: [{'peer': '127.0.0.1', 'netmask':
             '255.0.0.0', 'addr': '127.0.0.1'}],
        10: [{'netmask': 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff',
              'addr': '::1'}]
    },
    'eth0': {
        2: [{'addr': '192.168.1.55',
             'broadcast': '192.168.1.255',
             'netmask': '255.255.255.0'}],
        10: [{'addr': '2a01:348:2f4:0:685e:5748:ae62:209f',
              'netmask': 'ffff:ffff:ffff:ffff::'},
             {'addr': 'fe80::3e97:eff:fe8b:1cf7%eth0',
              'netmask': 'ffff:ffff:ffff:ffff::'}],
        17: [{'addr': '3c:97:0e:8b:1c:f7',
              'broadcast': 'ff:ff:ff:ff:ff:ff'}]
    },
    'eth1': {
        2: [{'addr': '10.5.0.1',
             'broadcast': '10.5.255.255',
             'netmask': '255.255.0.0'}],
        10: [{'addr': 'fe80::3e97:eff:fe8b:1cf7%eth1',
              'netmask': 'ffff:ffff:ffff:ffff::'}],
        17: [{'addr': '3c:97:0e:8b:1c:f7',
              'broadcast': 'ff:ff:ff:ff:ff:ff'}]
    }
}


class IPTest(unittest.TestCase):

    def test_get_address_in_network_with_invalid_net(self):
        for net in ['192.168.300/22', '192.168.1.0/2a', '2.a']:
            self.assertRaises(ValueError,
                              net_ip.get_address_in_network,
                              net)

    def _test_get_address_in_network(self, expect_ip_addr,
                                     network, fallback=None, fatal=False):

        def side_effect(iface):
            return DUMMY_ADDRESSES[iface]

        with mock.patch.object(netifaces, 'interfaces') as interfaces:
            interfaces.return_value = DUMMY_ADDRESSES.keys()
            with mock.patch.object(netifaces, 'ifaddresses') as ifaddresses:
                ifaddresses.side_effect = side_effect
                if not fatal:
                    self.assertEqual(expect_ip_addr,
                                     net_ip.get_address_in_network(
                                         network, fallback, fatal))
                else:
                    net_ip.get_address_in_network(network, fallback, fatal)

    @mock.patch.object(subprocess, 'call')
    def test_get_address_in_network_with_none(self, popen):
        fallback = '10.10.10.10'
        self.assertEqual(fallback,
                         net_ip.get_address_in_network(None, fallback))

        self.assertRaises(SystemExit, self._test_get_address_in_network,
                          None, None, fatal=True)

    def test_get_address_in_network_ipv4(self):
        self._test_get_address_in_network('192.168.1.55', '192.168.1.0/24')

    def test_get_address_in_network_ipv6(self):
        self._test_get_address_in_network('2a01:348:2f4:0:685e:5748:ae62:209f',
                                          '2a01:348:2f4::/64')

    def test_get_address_in_network_with_non_existent_net(self):
        self._test_get_address_in_network(None, '172.16.0.0/16')

    def test_get_address_in_network_fallback_works(self):
        fallback = '10.10.0.0'
        self._test_get_address_in_network(fallback, '172.16.0.0/16', fallback)

    @mock.patch.object(subprocess, 'call')
    def test_get_address_in_network_not_found_fatal(self, popen):
        self.assertRaises(SystemExit, self._test_get_address_in_network,
                          None, '172.16.0.0/16', fatal=True)

    def test_get_address_in_network_not_found_not_fatal(self):
        self._test_get_address_in_network(None, '172.16.0.0/16', fatal=False)

    def test_is_address_in_network(self):
        self.assertTrue(
            net_ip.is_address_in_network(
                '192.168.1.0/24',
                '192.168.1.1'))
        self.assertFalse(
            net_ip.is_address_in_network(
                '192.168.1.0/24',
                '10.5.1.1'))
        self.assertRaises(ValueError, net_ip.is_address_in_network,
                          'broken', '192.168.1.1')
        self.assertRaises(ValueError, net_ip.is_address_in_network,
                          '192.168.1.0/24', 'hostname')
        self.assertTrue(
            net_ip.is_address_in_network(
                '2a01:348:2f4::/64',
                '2a01:348:2f4:0:685e:5748:ae62:209f')
        )
        self.assertFalse(
            net_ip.is_address_in_network(
                '2a01:348:2f4::/64',
                'fdfc:3bd5:210b:cc8d:8c80:9e10:3f07:371')
        )

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_for_address(self, _interfaces, _ifaddresses):
        def mock_ifaddresses(iface):
            return DUMMY_ADDRESSES[iface]
        _interfaces.return_value = ['eth0', 'eth1']
        _ifaddresses.side_effect = mock_ifaddresses
        self.assertEquals(
            net_ip.get_iface_for_address('192.168.1.220'),
            'eth0')
        self.assertEquals(net_ip.get_iface_for_address('10.5.20.4'), 'eth1')
        self.assertEquals(
            net_ip.get_iface_for_address('2a01:348:2f4:0:685e:5748:ae62:210f'),
            'eth0'
        )
        self.assertEquals(net_ip.get_iface_for_address('172.4.5.5'), None)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_netmask_for_address(self, _interfaces, _ifaddresses):
        def mock_ifaddresses(iface):
            return DUMMY_ADDRESSES[iface]
        _interfaces.return_value = ['eth0', 'eth1']
        _ifaddresses.side_effect = mock_ifaddresses
        self.assertEquals(
            net_ip.get_netmask_for_address('192.168.1.220'),
            '255.255.255.0')
        self.assertEquals(
            net_ip.get_netmask_for_address('10.5.20.4'),
            '255.255.0.0')
        self.assertEquals(net_ip.get_netmask_for_address('172.4.5.5'), None)
        self.assertEquals(
            net_ip.get_netmask_for_address('2a01:348:2f4:0:685e:5748:ae62:210f'),
            'ffff:ffff:ffff:ffff::'
        )

    def test_is_ipv6(self):
        self.assertFalse(net_ip.is_ipv6('myhost'))
        self.assertFalse(net_ip.is_ipv6('172.4.5.5'))
        self.assertTrue(net_ip.is_ipv6('2a01:348:2f4:0:685e:5748:ae62:209f'))

    @patch.object(netifaces, 'ifaddresses')
    def test_get_ipv6_addr_no_ipv6(self, _ifaddresses):
        DUMMY_ADDRESSES = {
            'eth0': {
                2: [{'addr': '192.168.1.55',
                     'broadcast': '192.168.1.255',
                     'netmask': '255.255.255.0'}]
            }
        }

        def mock_ifaddresses(iface):
            return DUMMY_ADDRESSES[iface]

        _ifaddresses.side_effect = mock_ifaddresses
        self.assertRaises(Exception, net_ip.get_ipv6_addr)

    @patch.object(netifaces, 'ifaddresses')
    def test_get_ipv6_addr_no_global_ipv6(self, _ifaddresses):
        DUMMY_ADDRESSES = {
            'eth0': {
                10: [{'addr': 'fe80::3e97:eff:fe8b:1cf7%eth0',
                      'netmask': 'ffff:ffff:ffff:ffff::'}],
            }
        }

        def mock_ifaddresses(iface):
            return DUMMY_ADDRESSES[iface]

        _ifaddresses.side_effect = mock_ifaddresses
        self.assertRaises(Exception, net_ip.get_ipv6_addr)

    @patch.object(netifaces, 'ifaddresses')
    def test_get_ipv6_addr_invalid_nic(self, _ifaddresses):
        _ifaddresses.side_effect = ValueError()
        self.assertRaises(ValueError, net_ip.get_ipv6_addr, 'eth1')

    @patch.object(netifaces, 'ifaddresses')
    def test_get_ipv4_addr(self, _ifaddresses):
        DUMMY_ADDRESSES = {
            'eth0': {
                2: [{'addr': '192.168.0.1',
                      'netmask': '255.255.255.0'}],
            }
        }

        def mock_ifaddresses(iface):
            return DUMMY_ADDRESSES[iface]

        _ifaddresses.side_effect = mock_ifaddresses
        result = net_ip.get_ipv4_addr("eth0")
        self.assertEqual("192.168.0.1", result)

    @patch.object(netifaces, 'ifaddresses')
    def test_get_ipv4_addr_interface_does_not_exist(self, _ifaddresses):
        _ifaddresses.side_effect = ValueError()
        result = net_ip.get_ipv4_addr("eth0")
        self.assertIs(None, result)

    @patch.object(netifaces, 'ifaddresses')
    def test_get_ipv4_addr_interface_has_no_ipv4(self, _ifaddresses):

        # This will raise a KeyError since we are looking for "2"
        # (actally, netiface.AF_INET).
        DUMMY_ADDRESSES = {
            'eth0': {
                10: [{'addr': 'fe80::3e97:eff:fe8b:1cf7%eth0',
                      'netmask': 'ffff:ffff:ffff:ffff::'}],
            }
        }

        def mock_ifaddresses(iface):
            return DUMMY_ADDRESSES[iface]

        _ifaddresses.side_effect = mock_ifaddresses

        result = net_ip.get_ipv4_addr("eth0")
        self.assertIs(None, result)
