import subprocess
import unittest

import mock
import netifaces

import charmhelpers.contrib.network.ip as net_ip


class IPTest(unittest.TestCase):

    def test_get_address_in_network_with_invalid_net(self):
        for net in ['192.168.300/22', '192.168.1.0/2a', '2.a']:
            self.assertRaises(ValueError,
                              net_ip.get_address_in_network,
                              net)

    def _test_get_address_in_network(self, expect_ip_addr,
                                     network, fallback=None, fatal=False):

        def side_effect(iface):
            ffff = 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'
            results = {'lo': {17: [{'peer': '00:00:00:00:00:00',
                                    'addr': '00:00:00:00:00:00'}],
                              2: [{'peer': '127.0.0.1', 'netmask':
                                   '255.0.0.0', 'addr': '127.0.0.1'}],
                              10: [{'netmask': ffff,
                                    'addr': '::1'}]
                              },
                       'eth0': {17: [{'broadcast': 'ff:ff:ff:ff:ff:ff',
                                      'addr': '28:92:4a:19:8c:e8'}]
                                },
                       'eth2': {17: [{'broadcast': 'ff:ff:ff:ff:ff:ff',
                                      'addr': 'e0:06:e6:41:dd:dd'}],
                                2: [{'broadcast': '192.168.1.255',
                                     'netmask': '255.255.255.0',
                                     'addr': '192.168.1.108'}],
                                10: [{'netmask': 'ffff:ffff:ffff:ffff::',
                                      'addr': 'fe80::e206:e6ff:fe41:dddd%eth2'}
                                     ]
                                },
                       }
            return results[iface]

        with mock.patch.object(netifaces, 'interfaces') as interfaces:
            interfaces.return_value = ['lo', 'eth0', 'eth2']
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

    def test_get_address_in_network_works(self):
        self._test_get_address_in_network('192.168.1.108', '192.168.1.0/24')

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
