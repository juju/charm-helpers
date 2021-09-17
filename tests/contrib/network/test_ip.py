import subprocess
import unittest

import mock
import netifaces

import charmhelpers.contrib.network.ip as net_ip
from mock import patch, MagicMock

import nose.tools
import six

if not six.PY3:
    builtin_open = '__builtin__.open'
    builtin_import = '__builtin__.__import__'
else:
    builtin_open = 'builtins.open'
    builtin_import = 'builtins.__import__'

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
              'netmask': 'ffff:ffff:ffff:ffff::'},
             {'netmask': 'ffff:ffff:ffff:ffff::/64',
              'addr': 'fd2d:dec4:cf59:3c16::1'},
             {'addr': '2001:db8:1::',
              'netmask': 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'}],
        17: [{'addr': '3c:97:0e:8b:1c:f7',
              'broadcast': 'ff:ff:ff:ff:ff:ff'}]
    },
    'eth0:1': {
        2: [{'addr': '192.168.1.56',
             'broadcast': '192.168.1.255',
             'netmask': '255.255.255.0'}],
    },
    'eth1': {
        2: [{'addr': '10.5.0.1',
             'broadcast': '10.5.255.255',
             'netmask': '255.255.0.0'},
            {'addr': '10.6.0.2',
             'broadcast': '10.6.0.255',
             'netmask': '255.255.255.0'}],
        3: [{'addr': 'fe80::3e97:eff:fe8b:1cf7%eth1',
             'netmask': 'ffff:ffff:ffff:ffff::'}],
        17: [{'addr': '3c:97:0e:8b:1c:f7',
              'broadcast': 'ff:ff:ff:ff:ff:ff'}]
    },
    'eth2': {
        10: [{'addr': '3a01:348:2f4:0:685e:5748:ae62:209f',
              'netmask': 'ffff:ffff:ffff:ffff::'},
             {'addr': 'fe80::3e97:edd:fe8b:1cf7%eth0',
              'netmask': 'ffff:ffff:ffff:ffff::'}],
        17: [{'addr': '3c:97:0e:8b:1c:f7',
              'broadcast': 'ff:ff:ff:ff:ff:ff'}]
    },
    'eth2:1': {
        2: [{'addr': '192.168.10.58',
             'broadcast': '192.168.1.255',
             'netmask': '255.255.255.0'}],
    },
}

IP_OUTPUT = b"""link/ether fa:16:3e:2a:cc:ce brd ff:ff:ff:ff:ff:ff
    inet 10.5.16.93/16 brd 10.5.255.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 2001:db8:1:0:d0cf:528c:23eb:6000/64 scope global
       valid_lft forever preferred_lft forever
    inet6 2001:db8:1:0:2918:3444:852:5b8a/64 scope global temporary dynamic
       valid_lft 86400sec preferred_lft 14400sec
    inet6 2001:db8:1:0:f816:3eff:fe2a:ccce/64 scope global dynamic
       valid_lft 86400sec preferred_lft 14400sec
    inet6 fe80::f816:3eff:fe2a:ccce/64 scope link
       valid_lft forever preferred_lft forever
"""

IP2_OUTPUT = b"""link/ether fa:16:3e:2a:cc:ce brd ff:ff:ff:ff:ff:ff
    inet 10.5.16.93/16 brd 10.5.255.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 2001:db8:1:0:d0cf:528c:23eb:6000/64 scope global
       valid_lft forever preferred_lft forever
    inet6 2001:db8:1:0:2918:3444:852:5b8a/64 scope global temporary dynamic
       valid_lft 86400sec preferred_lft 14400sec
    inet6 2001:db8:1:0:f816:3eff:fe2a:ccce/64 scope global mngtmpaddr dynamic
       valid_lft 86400sec preferred_lft 14400sec
    inet6 fe80::f816:3eff:fe2a:ccce/64 scope link
       valid_lft forever preferred_lft forever
"""

IP_OUTPUT_NO_VALID = b"""link/ether fa:16:3e:2a:cc:ce brd ff:ff:ff:ff:ff:ff
    inet 10.5.16.93/16 brd 10.5.255.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 2001:db8:1:0:2918:3444:852:5b8a/64 scope global temporary dynamic
       valid_lft 86400sec preferred_lft 14400sec
    inet6 fe80::f816:3eff:fe2a:ccce/64 scope link
       valid_lft forever preferred_lft forever
"""


class FakeAnswer(object):
    def __init__(self, ip):
        self.ip = ip

    def __str__(self):
        return self.ip


class FakeResolver(object):
    def __init__(self, ip):
        self.ip = ip

    def query(self, hostname, query_type):
        if self.ip == '':
            return []
        else:
            return [FakeAnswer(self.ip)]


class FakeReverse(object):
    def from_address(self, address):
        return '156.94.189.91.in-addr.arpa'


class FakeDNSName(object):
    def __init__(self, dnsname):
        pass


class FakeDNS(object):
    def __init__(self, ip):
        self.resolver = FakeResolver(ip)
        self.reversename = FakeReverse()
        self.name = MagicMock()
        self.name.Name = FakeDNSName


class IPTest(unittest.TestCase):

    def mock_ifaddresses(self, iface):
        return DUMMY_ADDRESSES[iface]

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
            interfaces.return_value = sorted(DUMMY_ADDRESSES.keys())
            with mock.patch.object(netifaces, 'ifaddresses') as ifaddresses:
                ifaddresses.side_effect = side_effect
                if not fatal:
                    self.assertEqual(expect_ip_addr,
                                     net_ip.get_address_in_network(network,
                                                                   fallback,
                                                                   fatal))
                else:
                    net_ip.get_address_in_network(network, fallback, fatal)

    @mock.patch.object(subprocess, 'call')
    def test_get_address_in_network_with_none(self, popen):
        fallback = '10.10.10.10'
        self.assertEqual(fallback,
                         net_ip.get_address_in_network(None, fallback))
        self.assertEqual(None,
                         net_ip.get_address_in_network(None))

        self.assertRaises(ValueError, self._test_get_address_in_network,
                          None, None, fatal=True)

    def test_get_address_in_network_ipv4(self):
        self._test_get_address_in_network('192.168.1.55', '192.168.1.0/24')

    def test_get_address_in_network_ipv4_multi(self):
        # Assumes that there is an address configured on both but the first
        # one is picked#
        self._test_get_address_in_network('192.168.1.55',
                                          '192.168.1.0/24 192.168.10.0/24')

    def test_get_address_in_network_ipv4_multi2(self):
        # Assumes that there is nothing configured on 192.168.11.0/24
        self._test_get_address_in_network('192.168.10.58',
                                          '192.168.11.0/24 192.168.10.0/24')

    def test_get_address_in_network_ipv4_secondary(self):
        self._test_get_address_in_network('10.6.0.2',
                                          '10.6.0.0/24')

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
        self.assertRaises(ValueError, self._test_get_address_in_network,
                          None, '172.16.0.0/16', fatal=True)

    def test_get_address_in_network_not_found_not_fatal(self):
        self._test_get_address_in_network(None, '172.16.0.0/16', fatal=False)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_address_in_network_netmask(self, _interfaces, _ifaddresses):
        """
        Validates that get_address_in_network works with a netmask
        that uses the format 'ffff:ffff:ffff::/prefixlen'
        """
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        self._test_get_address_in_network('fd2d:dec4:cf59:3c16::1',
                                          'fd2d:dec4:cf59:3c16::/64',
                                          fatal=False)

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
            net_ip.get_netmask_for_address(
                '2a01:348:2f4:0:685e:5748:ae62:210f'),
            '64'
        )
        self.assertEquals(
            net_ip.get_netmask_for_address('2001:db8:1::'),
            '128'
        )

    def test_is_ipv6(self):
        self.assertFalse(net_ip.is_ipv6('myhost'))
        self.assertFalse(net_ip.is_ipv6('172.4.5.5'))
        self.assertTrue(net_ip.is_ipv6('2a01:348:2f4:0:685e:5748:ae62:209f'))

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_no_ipv6(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        with nose.tools.assert_raises(Exception):
            net_ip.get_ipv6_addr('eth0:1')

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_no_global_ipv6(self, _interfaces,
                                          _ifaddresses):
        DUMMY_ADDRESSES = {
            'eth0': {
                10: [{'addr': 'fe80::3e97:eff:fe8b:1cf7%eth0',
                      'netmask': 'ffff:ffff:ffff:ffff::'}],
            }
        }
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        self.assertRaises(Exception, net_ip.get_ipv6_addr)

    @patch('charmhelpers.contrib.network.ip.get_iface_from_addr')
    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_exc_list(self, _interfaces, _ifaddresses,
                                    mock_get_iface_from_addr):
        def mock_ifaddresses(iface):
            return DUMMY_ADDRESSES[iface]

        _interfaces.return_value = ['eth0', 'eth1']
        _ifaddresses.side_effect = mock_ifaddresses

        result = net_ip.get_ipv6_addr(
            exc_list='2a01:348:2f4:0:685e:5748:ae62:209f',
            inc_aliases=True,
            fatal=False
        )
        self.assertEqual([], result)

    @patch('charmhelpers.contrib.network.ip.get_iface_from_addr')
    @patch('charmhelpers.contrib.network.ip.subprocess.check_output')
    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr(self, _interfaces, _ifaddresses, mock_check_out,
                           mock_get_iface_from_addr):
        mock_get_iface_from_addr.return_value = 'eth0'
        mock_check_out.return_value = \
            b"inet6 2a01:348:2f4:0:685e:5748:ae62:209f/64 scope global dynamic"
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_ipv6_addr(dynamic_only=False)
        self.assertEqual(['2a01:348:2f4:0:685e:5748:ae62:209f'], result)

    @patch('charmhelpers.contrib.network.ip.get_iface_from_addr')
    @patch('charmhelpers.contrib.network.ip.subprocess.check_output')
    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_global_dynamic(self, _interfaces, _ifaddresses,
                                          mock_check_out,
                                          mock_get_iface_from_addr):
        mock_get_iface_from_addr.return_value = 'eth0'
        mock_check_out.return_value = \
            b"inet6 2a01:348:2f4:0:685e:5748:ae62:209f/64 scope global dynamic"
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_ipv6_addr(dynamic_only=False)
        self.assertEqual(['2a01:348:2f4:0:685e:5748:ae62:209f'], result)

    @patch.object(netifaces, 'interfaces')
    def test_get_ipv6_addr_invalid_nic(self, _interfaces):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        self.assertRaises(Exception, net_ip.get_ipv6_addr, 'eth1')

    @patch('charmhelpers.contrib.network.ip.subprocess.check_output')
    def test_is_ipv6_disabled(self, mock_check_output):
        # verify that the function does look for the right thing
        mock_check_output.return_value = """
        Some lines before
        net.ipv6.conf.all.disable_ipv6 = 1
        Some lines afterward
        """
        self.assertTrue(net_ip.is_ipv6_disabled())
        mock_check_output.assert_called_once_with(
            ['sysctl', 'net.ipv6.conf.all.disable_ipv6'],
            stderr=subprocess.STDOUT, universal_newlines=True)
        # if it isn't there, it must return false
        mock_check_output.return_value = ""
        self.assertFalse(net_ip.is_ipv6_disabled())
        # If the syscall returns an error, then return True

        def fake_check_call(*args, **kwargs):
            raise subprocess.CalledProcessError(['called'], 1)
        mock_check_output.side_effect = fake_check_call
        self.assertTrue(net_ip.is_ipv6_disabled())

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth0")
        self.assertEqual(["192.168.1.55"], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_excaliases(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth0")
        self.assertEqual(['192.168.1.55'], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_incaliases(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth0", inc_aliases=True)
        self.assertEqual(['192.168.1.55', '192.168.1.56'], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_exclist(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth0", inc_aliases=True,
                                       exc_list=['192.168.1.55'])
        self.assertEqual(['192.168.1.56'], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_mixedaddr(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("eth2", inc_aliases=True)
        self.assertEqual(["192.168.10.58"], result)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_full_interface_path(self, _interfaces,
                                                _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__
        result = net_ip.get_iface_addr("/dev/eth0")
        self.assertEqual(["192.168.1.55"], result)

    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_invalid_type(self, _interfaces):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        with nose.tools.assert_raises(Exception):
            net_ip.get_iface_addr(iface='eth0', inet_type='AF_BOB')

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_invalid_interface(self, _interfaces, _ifaddresses):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        result = net_ip.get_ipv4_addr("eth3", fatal=False)
        self.assertEqual([], result)

    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_invalid_interface_fatal(self, _interfaces):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        with nose.tools.assert_raises(Exception):
            net_ip.get_ipv4_addr("eth3", fatal=True)

    @patch.object(netifaces, 'interfaces')
    def test_get_iface_addr_invalid_interface_fatal_incaliases(self,
                                                               _interfaces):
        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        with nose.tools.assert_raises(Exception):
            net_ip.get_ipv4_addr("eth3", fatal=True, inc_aliases=True)

    @patch.object(netifaces, 'ifaddresses')
    @patch.object(netifaces, 'interfaces')
    def test_get_get_iface_addr_interface_has_no_ipv4(self, _interfaces,
                                                      _ifaddresses):

        # This will raise a KeyError since we are looking for "2"
        # (actually, netiface.AF_INET).
        DUMMY_ADDRESSES = {
            'eth0': {
                10: [{'addr': 'fe80::3e97:eff:fe8b:1cf7%eth0',
                      'netmask': 'ffff:ffff:ffff:ffff::'}],
            }
        }

        _interfaces.return_value = DUMMY_ADDRESSES.keys()
        _ifaddresses.side_effect = DUMMY_ADDRESSES.__getitem__

        result = net_ip.get_ipv4_addr("eth0", fatal=False)
        self.assertEqual([], result)

    @patch('glob.glob')
    def test_get_bridges(self, _glob):
        _glob.return_value = ['/sys/devices/virtual/net/br0/bridge']
        self.assertEqual(['br0'], net_ip.get_bridges())

    @patch.object(net_ip, 'get_bridges')
    @patch('glob.glob')
    def test_get_bridge_nics(self, _glob, _get_bridges):
        _glob.return_value = ['/sys/devices/virtual/net/br0/brif/eth4',
                              '/sys/devices/virtual/net/br0/brif/eth5']
        self.assertEqual(['eth4', 'eth5'], net_ip.get_bridge_nics('br0'))

    @patch.object(net_ip, 'get_bridges')
    @patch('glob.glob')
    def test_get_bridge_nics_invalid_br(self, _glob, _get_bridges):
        _glob.return_value = []
        self.assertEqual([], net_ip.get_bridge_nics('br1'))

    @patch.object(net_ip, 'get_bridges')
    @patch.object(net_ip, 'get_bridge_nics')
    def test_is_bridge_member(self, _get_bridge_nics, _get_bridges):
        _get_bridges.return_value = ['br0']
        _get_bridge_nics.return_value = ['eth4', 'eth5']
        self.assertTrue(net_ip.is_bridge_member('eth4'))
        self.assertFalse(net_ip.is_bridge_member('eth6'))

    def test_format_ipv6_addr(self):
        DUMMY_ADDRESS = '2001:db8:1:0:f131:fc84:ea37:7d4'
        self.assertEquals(net_ip.format_ipv6_addr(DUMMY_ADDRESS),
                          '[2001:db8:1:0:f131:fc84:ea37:7d4]')

    def test_format_invalid_ipv6_addr(self):
        INVALID_IPV6_ADDR = 'myhost'
        self.assertEquals(net_ip.format_ipv6_addr(INVALID_IPV6_ADDR),
                          None)

    @patch('charmhelpers.contrib.network.ip.get_iface_from_addr')
    @patch('charmhelpers.contrib.network.ip.subprocess.check_output')
    @patch('charmhelpers.contrib.network.ip.get_iface_addr')
    def test_get_ipv6_global_address(self, mock_get_iface_addr, mock_check_out,
                                     mock_get_iface_from_addr):
        mock_get_iface_from_addr.return_value = 'eth0'
        mock_check_out.return_value = IP_OUTPUT
        scope_global_addr = '2001:db8:1:0:d0cf:528c:23eb:6000'
        scope_global_dyn_addr = '2001:db8:1:0:f816:3eff:fe2a:ccce'
        mock_get_iface_addr.return_value = [scope_global_addr,
                                            scope_global_dyn_addr,
                                            '2001:db8:1:0:2918:3444:852:5b8a',
                                            'fe80::f816:3eff:fe2a:ccce%eth0']
        self.assertEqual([scope_global_addr, scope_global_dyn_addr],
                         net_ip.get_ipv6_addr(dynamic_only=False))

    @patch('charmhelpers.contrib.network.ip.get_iface_from_addr')
    @patch('charmhelpers.contrib.network.ip.subprocess.check_output')
    @patch('charmhelpers.contrib.network.ip.get_iface_addr')
    def test_get_ipv6_global_dynamic_address(self, mock_get_iface_addr,
                                             mock_check_out,
                                             mock_get_iface_from_addr):
        mock_get_iface_from_addr.return_value = 'eth0'
        mock_check_out.return_value = IP_OUTPUT
        scope_global_addr = '2001:db8:1:0:d0cf:528c:23eb:6000'
        scope_global_dyn_addr = '2001:db8:1:0:f816:3eff:fe2a:ccce'
        mock_get_iface_addr.return_value = [scope_global_addr,
                                            scope_global_dyn_addr,
                                            '2001:db8:1:0:2918:3444:852:5b8a',
                                            'fe80::f816:3eff:fe2a:ccce%eth0']
        self.assertEqual([scope_global_dyn_addr], net_ip.get_ipv6_addr())

    @patch('charmhelpers.contrib.network.ip.get_iface_from_addr')
    @patch('charmhelpers.contrib.network.ip.subprocess.check_output')
    @patch('charmhelpers.contrib.network.ip.get_iface_addr')
    def test_get_ipv6_global_dynamic_address_ip2(self, mock_get_iface_addr,
                                                 mock_check_out,
                                                 mock_get_iface_from_addr):
        mock_get_iface_from_addr.return_value = 'eth0'
        mock_check_out.return_value = IP2_OUTPUT
        scope_global_addr = '2001:db8:1:0:d0cf:528c:23eb:6000'
        scope_global_dyn_addr = '2001:db8:1:0:f816:3eff:fe2a:ccce'
        mock_get_iface_addr.return_value = [scope_global_addr,
                                            scope_global_dyn_addr,
                                            '2001:db8:1:0:2918:3444:852:5b8a',
                                            'fe80::f816:3eff:fe2a:ccce%eth0']
        self.assertEqual([scope_global_dyn_addr], net_ip.get_ipv6_addr())

    @patch('charmhelpers.contrib.network.ip.subprocess.check_output')
    @patch('charmhelpers.contrib.network.ip.get_iface_addr')
    def test_get_ipv6_global_dynamic_address_invalid_address(
            self, mock_get_iface_addr, mock_check_out):
        mock_get_iface_addr.return_value = []
        with nose.tools.assert_raises(Exception):
            net_ip.get_ipv6_addr()

        mock_get_iface_addr.return_value = ['2001:db8:1:0:2918:3444:852:5b8a']
        mock_check_out.return_value = IP_OUTPUT_NO_VALID
        with nose.tools.assert_raises(Exception):
            net_ip.get_ipv6_addr()

    @patch('charmhelpers.contrib.network.ip.get_iface_addr')
    def test_get_ipv6_addr_w_iface(self, mock_get_iface_addr):
        mock_get_iface_addr.return_value = []
        net_ip.get_ipv6_addr(iface='testif', fatal=False)
        mock_get_iface_addr.assert_called_once_with(iface='testif',
                                                    inet_type='AF_INET6',
                                                    inc_aliases=False,
                                                    fatal=False, exc_list=None)

    @patch('charmhelpers.contrib.network.ip.unit_get')
    @patch('charmhelpers.contrib.network.ip.get_iface_from_addr')
    @patch('charmhelpers.contrib.network.ip.get_iface_addr')
    def test_get_ipv6_addr_no_iface(self, mock_get_iface_addr,
                                    mock_get_iface_from_addr, mock_unit_get):
        mock_unit_get.return_value = '1.2.3.4'
        mock_get_iface_addr.return_value = []
        mock_get_iface_from_addr.return_value = "testif"
        net_ip.get_ipv6_addr(fatal=False)
        mock_get_iface_from_addr.assert_called_once_with('1.2.3.4')
        mock_get_iface_addr.assert_called_once_with(iface='testif',
                                                    inet_type='AF_INET6',
                                                    inc_aliases=False,
                                                    fatal=False, exc_list=None)

    @patch('netifaces.interfaces')
    @patch('netifaces.ifaddresses')
    @patch('charmhelpers.contrib.network.ip.log')
    def test_get_iface_from_addr(self, mock_log, mock_ifaddresses,
                                 mock_interfaces):
        mock_ifaddresses.side_effect = lambda iface: DUMMY_ADDRESSES[iface]
        mock_interfaces.return_value = sorted(DUMMY_ADDRESSES.keys())
        addr = 'fe80::3e97:eff:fe8b:1cf7'
        self.assertEqual(net_ip.get_iface_from_addr(addr), 'eth0')

        with nose.tools.assert_raises(Exception):
            net_ip.get_iface_from_addr('1.2.3.4')

    def test_is_ip(self):
        self.assertTrue(net_ip.is_ip('10.0.0.1'))
        self.assertTrue(net_ip.is_ip('2001:db8:1:0:2918:3444:852:5b8a'))
        self.assertFalse(net_ip.is_ip('www.ubuntu.com'))

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_host_ip_with_hostname(self, apt_install):
        fake_dns = FakeDNS('10.0.0.1')
        with patch(builtin_import, side_effect=[fake_dns]):
            ip = net_ip.get_host_ip('www.ubuntu.com')
        self.assertEquals(ip, '10.0.0.1')

    @patch('charmhelpers.contrib.network.ip.ns_query')
    @patch('charmhelpers.contrib.network.ip.socket.gethostbyname')
    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_host_ip_with_hostname_no_dns(self, apt_install, socket,
                                              ns_query):
        ns_query.return_value = []
        fake_dns = FakeDNS(None)
        socket.return_value = '10.0.0.1'
        with patch(builtin_import, side_effect=[fake_dns]):
            ip = net_ip.get_host_ip('www.ubuntu.com')
        self.assertEquals(ip, '10.0.0.1')

    @patch('charmhelpers.contrib.network.ip.log')
    @patch('charmhelpers.contrib.network.ip.ns_query')
    @patch('charmhelpers.contrib.network.ip.socket.gethostbyname')
    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_host_ip_with_hostname_fallback(self, apt_install, socket,
                                                ns_query, *args):
        ns_query.return_value = []
        fake_dns = FakeDNS(None)

        def r():
            raise Exception()

        socket.side_effect = r
        with patch(builtin_import, side_effect=[fake_dns]):
            ip = net_ip.get_host_ip('www.ubuntu.com', fallback='127.0.0.1')
        self.assertEquals(ip, '127.0.0.1')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_host_ip_with_ip(self, apt_install):
        fake_dns = FakeDNS('5.5.5.5')
        with patch(builtin_import, side_effect=[fake_dns]):
            ip = net_ip.get_host_ip('4.2.2.1')
        self.assertEquals(ip, '4.2.2.1')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_ns_query_trigger_apt_install(self, apt_install):
        fake_dns = FakeDNS('5.5.5.5')
        with patch(builtin_import, side_effect=[ImportError, fake_dns]):
            nsq = net_ip.ns_query('5.5.5.5')
            if six.PY2:
                apt_install.assert_called_with('python-dnspython', fatal=True)
            else:
                apt_install.assert_called_with('python3-dnspython', fatal=True)
        self.assertEquals(nsq, '5.5.5.5')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_ns_query_ptr_record(self, apt_install):
        fake_dns = FakeDNS('127.0.0.1')
        with patch(builtin_import, side_effect=[fake_dns]):
            nsq = net_ip.ns_query('127.0.0.1')
        self.assertEquals(nsq, '127.0.0.1')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_ns_query_a_record(self, apt_install):
        fake_dns = FakeDNS('127.0.0.1')
        fake_dns_name = FakeDNSName('www.somedomain.tld')
        with patch(builtin_import, side_effect=[fake_dns]):
            nsq = net_ip.ns_query(fake_dns_name)
        self.assertEquals(nsq, '127.0.0.1')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_ns_query_blank_record(self, apt_install):
        fake_dns = FakeDNS(None)
        with patch(builtin_import, side_effect=[fake_dns, fake_dns]):
            nsq = net_ip.ns_query(None)
        self.assertEquals(nsq, None)

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_ns_query_lookup_fail(self, apt_install):
        fake_dns = FakeDNS('')
        with patch(builtin_import, side_effect=[fake_dns, fake_dns]):
            nsq = net_ip.ns_query('nonexistant')
        self.assertEquals(nsq, None)

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_hostname_with_ip(self, apt_install):
        fake_dns = FakeDNS('www.ubuntu.com')
        with patch(builtin_import, side_effect=[fake_dns, fake_dns]):
            hn = net_ip.get_hostname('4.2.2.1')
        self.assertEquals(hn, 'www.ubuntu.com')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_hostname_with_ip_not_fqdn(self, apt_install):
        fake_dns = FakeDNS('packages.ubuntu.com')
        with patch(builtin_import, side_effect=[fake_dns, fake_dns]):
            hn = net_ip.get_hostname('4.2.2.1', fqdn=False)
        self.assertEquals(hn, 'packages')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_hostname_with_hostname(self, apt_install):
        hn = net_ip.get_hostname('www.ubuntu.com')
        self.assertEquals(hn, 'www.ubuntu.com')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_hostname_with_hostname_trailingdot(self, apt_install):
        hn = net_ip.get_hostname('www.ubuntu.com.')
        self.assertEquals(hn, 'www.ubuntu.com')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_hostname_with_hostname_not_fqdn(self, apt_install):
        hn = net_ip.get_hostname('packages.ubuntu.com', fqdn=False)
        self.assertEquals(hn, 'packages')

    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_hostname_trigger_apt_install(self, apt_install):
        fake_dns = FakeDNS('www.ubuntu.com')
        with patch(builtin_import, side_effect=[ImportError, fake_dns,
                                                fake_dns]):
            hn = net_ip.get_hostname('4.2.2.1')
            if six.PY2:
                apt_install.assert_called_with('python-dnspython', fatal=True)
            else:
                apt_install.assert_called_with('python3-dnspython', fatal=True)

        self.assertEquals(hn, 'www.ubuntu.com')

    @patch('charmhelpers.contrib.network.ip.socket.gethostbyaddr')
    @patch('charmhelpers.contrib.network.ip.ns_query')
    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_hostname_lookup_fail(self, apt_install, ns_query, socket):
        fake_dns = FakeDNS('www.ubuntu.com')
        ns_query.return_value = []
        socket.return_value = ()
        with patch(builtin_import, side_effect=[fake_dns, fake_dns]):
            hn = net_ip.get_hostname('4.2.2.1')
        self.assertEquals(hn, None)

    @patch('charmhelpers.contrib.network.ip.socket.gethostbyaddr')
    @patch('charmhelpers.contrib.network.ip.ns_query')
    @patch('charmhelpers.contrib.network.ip.apt_install')
    def test_get_hostname_lookup_fail_gethostbyaddr_fallback(
            self, apt_install, ns_query, socket):
        fake_dns = FakeDNS('www.ubuntu.com')
        ns_query.return_value = []
        socket.return_value = ("www.ubuntu.com", "", "")
        with patch(builtin_import, side_effect=[fake_dns]):
            hn = net_ip.get_hostname('4.2.2.1')
        self.assertEquals(hn, "www.ubuntu.com")

    @patch('charmhelpers.contrib.network.ip.subprocess.call')
    def test_port_has_listener(self, subprocess_call):
        subprocess_call.return_value = 1
        self.assertEqual(net_ip.port_has_listener('ip-address', 50), False)
        subprocess_call.assert_called_with(['nc', '-z', 'ip-address', '50'])
        subprocess_call.return_value = 0
        self.assertEqual(net_ip.port_has_listener('ip-address', 70), True)
        subprocess_call.assert_called_with(['nc', '-z', 'ip-address', '70'])

    @patch.object(net_ip, 'log', lambda *args, **kwargs: None)
    @patch.object(net_ip, 'config')
    @patch.object(net_ip, 'network_get_primary_address')
    @patch.object(net_ip, 'get_address_in_network')
    @patch.object(net_ip, 'unit_get')
    @patch.object(net_ip, 'get_ipv6_addr')
    @patch.object(net_ip, 'assert_charm_supports_ipv6')
    def test_get_relation_ip(self, assert_charm_supports_ipv6, get_ipv6_addr,
                             unit_get, get_address_in_network,
                             network_get_primary_address, config):
        ACCESS_IP = '10.50.1.1'
        ACCESS_NETWORK = '10.50.1.0/24'
        AMQP_IP = '10.200.1.1'
        IPV6_IP = '2001:DB8::1'
        DEFAULT_IP = '172.16.1.1'
        assert_charm_supports_ipv6.return_value = True
        get_ipv6_addr.return_value = [IPV6_IP]
        unit_get.return_value = DEFAULT_IP
        get_address_in_network.return_value = DEFAULT_IP
        network_get_primary_address.return_value = AMQP_IP

        # Network-get calls
        _config = {'prefer-ipv6': False}
        config.side_effect = lambda key: _config.get(key)

        network_get_primary_address.side_effect = NotImplementedError
        self.assertEqual(DEFAULT_IP, net_ip.get_relation_ip('amqp'))

        network_get_primary_address.side_effect = net_ip.NoNetworkBinding
        self.assertEqual(DEFAULT_IP, net_ip.get_relation_ip('doesnotexist'))

        network_get_primary_address.side_effect = None
        self.assertEqual(AMQP_IP, net_ip.get_relation_ip('amqp'))

        self.assertFalse(get_address_in_network.called)

        # Specific CIDR network
        get_address_in_network.return_value = ACCESS_IP
        network_get_primary_address.return_value = DEFAULT_IP
        self.assertEqual(
            ACCESS_IP,
            net_ip.get_relation_ip('shared-db',
                                   cidr_network=ACCESS_NETWORK))
        get_address_in_network.assert_called_with(ACCESS_NETWORK, DEFAULT_IP)

        self.assertFalse(assert_charm_supports_ipv6.called)

        # IPv6
        _config = {'prefer-ipv6': True}
        config.side_effect = lambda key: _config.get(key)
        self.assertEqual(IPV6_IP, net_ip.get_relation_ip('amqp'))
        assert_charm_supports_ipv6.assert_called_with()
