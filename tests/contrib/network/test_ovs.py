import subprocess
import unittest

from mock import patch, MagicMock

import charmhelpers.contrib.network.ovs as ovs

from tests.helpers import patch_open


# NOTE(fnordahl): some functions drectly under the ``contrib.network.ovs``
# module have their unit tests in the ``test_ovs.py`` module in the
# ``tests.contrib.network.ovs`` package.


GOOD_CERT = '''Certificate:
    Data:
        Version: 1 (0x0)
        Serial Number: 13798680962510501282 (0xbf7ec33a136235a2)
    Signature Algorithm: sha1WithRSAEncryption
        Issuer: C=US, ST=CA, L=Palo Alto, O=Open vSwitch, OU=Open vSwitch
        Validity
            Not Before: Jun 28 17:02:19 2013 GMT
            Not After : Jun 28 17:02:19 2019 GMT
        Subject: C=US, ST=CA, L=Palo Alto, O=Open vSwitch, OU=Open vSwitch
        Subject Public Key Info:
            Public Key Algorithm: rsaEncryption
                Public-Key: (2048 bit)
                Modulus:
                    00:e8:a7:db:0a:6d:c0:16:4a:14:96:1d:74:91:15:
                    64:3f:ae:2a:54:be:2a:fe:10:14:9a:73:39:d8:58:
                    74:7f:ab:d5:f2:39:aa:9a:27:7c:31:82:f8:74:42:
                    46:8d:c5:3b:42:55:52:be:75:7f:a5:b1:ec:d5:29:
                    9f:62:0e:de:31:27:2b:95:1f:24:0d:ca:8c:48:30:
                    96:9f:ba:b7:9d:eb:c1:bd:93:05:e3:d8:ca:66:5a:
                    e9:cb:a5:7a:3a:8d:27:e2:05:9d:88:fc:a9:ef:af:
                    47:4c:66:ce:c6:43:73:1a:85:f4:5f:b9:53:5b:29:
                    f3:c3:23:1f:0c:20:95:11:50:71:b2:f6:01:23:3f:
                    66:0f:5c:43:c2:90:fb:e5:98:73:98:e9:38:bb:1f:
                    1b:89:97:1e:dc:d7:98:07:68:32:ec:da:1d:69:0b:
                    e2:df:40:fb:64:52:e5:e9:40:27:b0:ca:73:21:51:
                    f6:8f:00:20:c0:2b:1a:d4:01:c2:32:38:9d:d1:8d:
                    88:71:46:a9:42:0d:ee:3b:1c:88:db:27:69:49:f9:
                    60:34:70:61:3d:60:df:7e:e4:e1:1d:c6:16:89:05:
                    ba:31:06:eb:88:b5:78:94:5d:8c:9d:88:fe:f2:c2:
                    80:a1:04:15:d3:84:85:d3:aa:5a:1d:53:5c:f8:57:
                    ae:61
                Exponent: 65537 (0x10001)
    Signature Algorithm: sha1WithRSAEncryption
         14:7e:ca:c3:fc:93:60:9f:80:e0:65:2e:ef:41:2d:f9:af:77:
         da:6d:e2:e0:11:70:17:fb:e5:67:4c:f0:ad:39:ec:96:ef:fe:
         d5:95:94:70:e5:52:31:68:63:8c:ea:b3:a1:8e:02:e2:91:4b:
         a8:8c:07:86:fd:80:98:a2:b1:90:2b:9c:2e:ab:f4:73:9d:8f:
         fd:31:b9:8f:fe:6c:af:d6:bf:72:44:89:08:93:19:ef:2b:c3:
         7c:ab:ba:bc:57:ca:f1:17:e4:e8:81:40:ca:65:df:84:be:10:
         2c:42:46:af:d2:e0:0d:df:5d:56:53:65:13:e0:20:55:b4:ee:
         cd:5e:b5:c4:97:1d:3e:a6:c1:9c:7e:b8:87:ee:64:78:a5:59:
         e5:b2:79:47:9a:8e:59:fa:c4:18:ea:27:fd:a2:d5:76:d0:ae:
         d9:05:f6:0e:23:ca:7d:66:a1:ba:18:67:f5:6d:bb:51:5a:f5:
         52:e9:17:bb:63:15:24:b4:61:25:9f:d9:9c:89:58:93:9a:c3:
         74:55:72:3e:f9:ff:ef:54:7d:e8:28:78:ba:3c:c7:15:ba:b9:
         c6:e3:8c:61:cb:a9:ed:8d:07:16:0d:8d:f6:1c:36:11:69:08:
         b8:45:7d:fc:fd:d1:ab:2d:9b:4e:9c:dd:11:78:50:c7:87:9f:
         4a:24:9c:a0
-----BEGIN CERTIFICATE-----
MIIDwjCCAqoCCQC/fsM6E2I1ojANBgkqhkiG9w0BAQUFADCBojELMAkGA1UEBhMC
VVMxCzAJBgNVBAgTAkNBMRIwEAYDVQQHEwlQYWxvIEFsdG8xFTATBgNVBAoTDE9w
ZW4gdlN3aXRjaDEfMB0GA1UECxMWT3BlbiB2U3dpdGNoIGNlcnRpZmllcjE6MDgG
A1UEAxMxb3ZzY2xpZW50IGlkOjU4MTQ5N2E1LWJjMDAtNGVjYy1iNzkwLTU3NTZj
ZWUxNmE0ODAeFw0xMzA2MjgxNzAyMTlaFw0xOTA2MjgxNzAyMTlaMIGiMQswCQYD
VQQGEwJVUzELMAkGA1UECBMCQ0ExEjAQBgNVBAcTCVBhbG8gQWx0bzEVMBMGA1UE
ChMMT3BlbiB2U3dpdGNoMR8wHQYDVQQLExZPcGVuIHZTd2l0Y2ggY2VydGlmaWVy
MTowOAYDVQQDEzFvdnNjbGllbnQgaWQ6NTgxNDk3YTUtYmMwMC00ZWNjLWI3OTAt
NTc1NmNlZTE2YTQ4MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA6Kfb
Cm3AFkoUlh10kRVkP64qVL4q/hAUmnM52Fh0f6vV8jmqmid8MYL4dEJGjcU7QlVS
vnV/pbHs1SmfYg7eMScrlR8kDcqMSDCWn7q3nevBvZMF49jKZlrpy6V6Oo0n4gWd
iPyp769HTGbOxkNzGoX0X7lTWynzwyMfDCCVEVBxsvYBIz9mD1xDwpD75ZhzmOk4
ux8biZce3NeYB2gy7NodaQvi30D7ZFLl6UAnsMpzIVH2jwAgwCsa1AHCMjid0Y2I
cUapQg3uOxyI2ydpSflgNHBhPWDffuThHcYWiQW6MQbriLV4lF2MnYj+8sKAoQQV
04SF06paHVNc+FeuYQIDAQABMA0GCSqGSIb3DQEBBQUAA4IBAQAUfsrD/JNgn4Dg
ZS7vQS35r3fabeLgEXAX++VnTPCtOeyW7/7VlZRw5VIxaGOM6rOhjgLikUuojAeG
/YCYorGQK5wuq/RznY/9MbmP/myv1r9yRIkIkxnvK8N8q7q8V8rxF+TogUDKZd+E
vhAsQkav0uAN311WU2UT4CBVtO7NXrXElx0+psGcfriH7mR4pVnlsnlHmo5Z+sQY
6if9otV20K7ZBfYOI8p9ZqG6GGf1bbtRWvVS6Re7YxUktGEln9mciViTmsN0VXI+
+f/vVH3oKHi6PMcVurnG44xhy6ntjQcWDY32HDYRaQi4RX38/dGrLZtOnN0ReFDH
h59KJJyg
-----END CERTIFICATE-----
'''

PEM_ENCODED = '''-----BEGIN CERTIFICATE-----
MIIDwjCCAqoCCQC/fsM6E2I1ojANBgkqhkiG9w0BAQUFADCBojELMAkGA1UEBhMC
VVMxCzAJBgNVBAgTAkNBMRIwEAYDVQQHEwlQYWxvIEFsdG8xFTATBgNVBAoTDE9w
ZW4gdlN3aXRjaDEfMB0GA1UECxMWT3BlbiB2U3dpdGNoIGNlcnRpZmllcjE6MDgG
A1UEAxMxb3ZzY2xpZW50IGlkOjU4MTQ5N2E1LWJjMDAtNGVjYy1iNzkwLTU3NTZj
ZWUxNmE0ODAeFw0xMzA2MjgxNzAyMTlaFw0xOTA2MjgxNzAyMTlaMIGiMQswCQYD
VQQGEwJVUzELMAkGA1UECBMCQ0ExEjAQBgNVBAcTCVBhbG8gQWx0bzEVMBMGA1UE
ChMMT3BlbiB2U3dpdGNoMR8wHQYDVQQLExZPcGVuIHZTd2l0Y2ggY2VydGlmaWVy
MTowOAYDVQQDEzFvdnNjbGllbnQgaWQ6NTgxNDk3YTUtYmMwMC00ZWNjLWI3OTAt
NTc1NmNlZTE2YTQ4MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA6Kfb
Cm3AFkoUlh10kRVkP64qVL4q/hAUmnM52Fh0f6vV8jmqmid8MYL4dEJGjcU7QlVS
vnV/pbHs1SmfYg7eMScrlR8kDcqMSDCWn7q3nevBvZMF49jKZlrpy6V6Oo0n4gWd
iPyp769HTGbOxkNzGoX0X7lTWynzwyMfDCCVEVBxsvYBIz9mD1xDwpD75ZhzmOk4
ux8biZce3NeYB2gy7NodaQvi30D7ZFLl6UAnsMpzIVH2jwAgwCsa1AHCMjid0Y2I
cUapQg3uOxyI2ydpSflgNHBhPWDffuThHcYWiQW6MQbriLV4lF2MnYj+8sKAoQQV
04SF06paHVNc+FeuYQIDAQABMA0GCSqGSIb3DQEBBQUAA4IBAQAUfsrD/JNgn4Dg
ZS7vQS35r3fabeLgEXAX++VnTPCtOeyW7/7VlZRw5VIxaGOM6rOhjgLikUuojAeG
/YCYorGQK5wuq/RznY/9MbmP/myv1r9yRIkIkxnvK8N8q7q8V8rxF+TogUDKZd+E
vhAsQkav0uAN311WU2UT4CBVtO7NXrXElx0+psGcfriH7mR4pVnlsnlHmo5Z+sQY
6if9otV20K7ZBfYOI8p9ZqG6GGf1bbtRWvVS6Re7YxUktGEln9mciViTmsN0VXI+
+f/vVH3oKHi6PMcVurnG44xhy6ntjQcWDY32HDYRaQi4RX38/dGrLZtOnN0ReFDH
h59KJJyg
-----END CERTIFICATE-----'''

BAD_CERT = ''' NO MARKERS '''
TO_PATCH = [
    "apt_install",
    "log",
    "hashlib",
]


class OVSHelpersTest(unittest.TestCase):

    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.network.ovs.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    @patch('subprocess.check_output')
    def test_get_bridges(self, check_output):
        check_output.return_value = b"br1\n br2  "
        self.assertEqual(ovs.get_bridges(), ['br1', 'br2'])
        check_output.assert_called_once_with(['ovs-vsctl', 'list-br'])

    @patch('subprocess.check_output')
    def test_get_bridge_ports(self, check_output):
        check_output.return_value = b"p1\n p2  \np3"
        self.assertEqual(ovs.get_bridge_ports('br1'), ['p1', 'p2', 'p3'])
        check_output.assert_called_once_with(
            ['ovs-vsctl', '--', 'list-ports', 'br1'])

    @patch.object(ovs, 'get_bridges')
    @patch.object(ovs, 'get_bridge_ports')
    def test_get_bridges_and_ports_map(self, get_bridge_ports, get_bridges):
        get_bridges.return_value = ['br1', 'br2']
        get_bridge_ports.side_effect = [
            ['p1', 'p2'],
            ['p3']]
        self.assertEqual(ovs.get_bridges_and_ports_map(), {
            'br1': ['p1', 'p2'],
            'br2': ['p3'],
        })

    @patch('subprocess.check_call')
    def test_del_bridge(self, check_call):
        ovs.del_bridge('test')
        check_call.assert_called_with(["ovs-vsctl", "--", "--if-exists",
                                       "del-br", 'test'])
        self.assertTrue(self.log.call_count == 1)

    @patch.object(ovs, 'port_to_br')
    @patch.object(ovs, 'add_bridge_port')
    @patch.object(ovs, 'lsb_release')
    @patch('os.path.exists')
    @patch('subprocess.check_call')
    def test_add_ovsbridge_linuxbridge(self, check_call, exists, lsb_release,
                                       add_bridge_port,
                                       port_to_br):
        exists.return_value = True
        lsb_release.return_value = {'DISTRIB_CODENAME': 'bionic'}
        port_to_br.return_value = None
        if_and_port_data = {
            'external-ids': {'mycharm': 'br-ex'}
        }
        with patch_open() as (mock_open, mock_file):
            ovs.add_ovsbridge_linuxbridge(
                'br-ex', 'br-eno1', ifdata=if_and_port_data,
                portdata=if_and_port_data)

        check_call.assert_called_with(['ifup', 'veth-br-eno1'])
        add_bridge_port.assert_called_with(
            'br-ex', 'veth-br-eno1', ifdata=if_and_port_data, exclusive=False,
            portdata=if_and_port_data)

    @patch.object(ovs, 'port_to_br')
    @patch.object(ovs, 'add_bridge_port')
    @patch.object(ovs, 'lsb_release')
    @patch('os.path.exists')
    @patch('subprocess.check_call')
    def test_add_ovsbridge_linuxbridge_already_direct_wired(
            self, check_call, exists, lsb_release, add_bridge_port, port_to_br):
        exists.return_value = True
        lsb_release.return_value = {'DISTRIB_CODENAME': 'bionic'}
        port_to_br.return_value = 'br-ex'
        ovs.add_ovsbridge_linuxbridge('br-ex', 'br-eno1')
        check_call.assert_not_called()
        add_bridge_port.assert_not_called()

    @patch.object(ovs, 'port_to_br')
    @patch.object(ovs, 'add_bridge_port')
    @patch.object(ovs, 'lsb_release')
    @patch('os.path.exists')
    @patch('subprocess.check_call')
    def test_add_ovsbridge_linuxbridge_longname(self, check_call, exists,
                                                lsb_release, add_bridge_port,
                                                port_to_br):
        exists.return_value = True
        lsb_release.return_value = {'DISTRIB_CODENAME': 'bionic'}
        port_to_br.return_value = None
        mock_hasher = MagicMock()
        mock_hasher.hexdigest.return_value = '12345678901234578910'
        self.hashlib.sha256.return_value = mock_hasher
        with patch_open() as (mock_open, mock_file):
            ovs.add_ovsbridge_linuxbridge('br-ex', 'br-reallylongname')

        check_call.assert_called_with(['ifup', 'cvb12345678-10'])
        add_bridge_port.assert_called_with(
            'br-ex', 'cvb12345678-10', ifdata=None, exclusive=False,
            portdata=None)

    @patch('os.path.exists')
    def test_is_linuxbridge_interface_false(self, exists):
        exists.return_value = False
        result = ovs.is_linuxbridge_interface('eno1')
        self.assertFalse(result)

    @patch('os.path.exists')
    def test_is_linuxbridge_interface_true(self, exists):
        exists.return_value = True
        result = ovs.is_linuxbridge_interface('eno1')
        self.assertTrue(result)

    @patch('subprocess.check_call')
    def test_set_manager(self, check_call):
        ovs.set_manager('manager')
        check_call.assert_called_with(['ovs-vsctl', 'set-manager',
                                       'ssl:manager'])
        self.assertTrue(self.log.call_count == 1)

    @patch('subprocess.check_call')
    def test_set_Open_vSwitch_column_value(self, check_call):
        ovs.set_Open_vSwitch_column_value('other_config:foo=bar')
        check_call.assert_called_with(['ovs-vsctl', 'set',
                                       'Open_vSwitch', '.', 'other_config:foo=bar'])
        self.assertTrue(self.log.call_count == 1)

    @patch('os.path.exists')
    def test_get_certificate_good_cert(self, exists):
        exists.return_value = True
        with patch_open() as (mock_open, mock_file):
            mock_file.read.return_value = GOOD_CERT
            self.assertEqual(ovs.get_certificate(), PEM_ENCODED)
        self.assertTrue(self.log.call_count == 1)

    @patch('os.path.exists')
    def test_get_certificate_bad_cert(self, exists):
        exists.return_value = True
        with patch_open() as (mock_open, mock_file):
            mock_file.read.return_value = BAD_CERT
            self.assertRaises(RuntimeError, ovs.get_certificate)
        self.assertTrue(self.log.call_count == 1)

    @patch('os.path.exists')
    def test_get_certificate_missing(self, exists):
        exists.return_value = False
        self.assertIsNone(ovs.get_certificate())
        self.assertTrue(self.log.call_count == 1)

    @patch('os.path.exists')
    @patch.object(ovs, 'service')
    def test_full_restart(self, service, exists):
        exists.return_value = False
        ovs.full_restart()
        service.assert_called_with('force-reload-kmod', 'openvswitch-switch')

    @patch('os.path.exists')
    @patch.object(ovs, 'service')
    def test_full_restart_upstart(self, service, exists):
        exists.return_value = True
        ovs.full_restart()
        service.assert_called_with('start', 'openvswitch-force-reload-kmod')

    @patch('subprocess.check_output')
    def test_port_to_br(self, check_output):
        check_output.return_value = b'br-ex'
        self.assertEqual(ovs.port_to_br('br-lb'),
                         'br-ex')

    @patch('subprocess.check_output')
    def test_port_to_br_not_found(self, check_output):
        check_output.side_effect = subprocess.CalledProcessError(1, 'not found')
        self.assertEqual(ovs.port_to_br('br-lb'), None)

    @patch('subprocess.check_call')
    def test_enable_ipfix_defaults(self, check_call):
        ovs.enable_ipfix('br-int',
                         '10.5.0.10:4739')
        check_call.assert_called_once_with([
            'ovs-vsctl', 'set', 'Bridge', 'br-int', 'ipfix=@i', '--',
            '--id=@i', 'create', 'IPFIX',
            'targets="10.5.0.10:4739"',
            'sampling=64',
            'cache_active_timeout=60',
            'cache_max_flows=128',
        ])

    @patch('subprocess.check_call')
    def test_enable_ipfix_values(self, check_call):
        ovs.enable_ipfix('br-int',
                         '10.5.0.10:4739',
                         sampling=120,
                         cache_max_flows=24,
                         cache_active_timeout=120)
        check_call.assert_called_once_with([
            'ovs-vsctl', 'set', 'Bridge', 'br-int', 'ipfix=@i', '--',
            '--id=@i', 'create', 'IPFIX',
            'targets="10.5.0.10:4739"',
            'sampling=120',
            'cache_active_timeout=120',
            'cache_max_flows=24',
        ])

    @patch('subprocess.check_call')
    def test_disable_ipfix(self, check_call):
        ovs.disable_ipfix('br-int')
        check_call.assert_called_once_with(
            ['ovs-vsctl', 'clear', 'Bridge', 'br-int', 'ipfix']
        )

    @patch.object(ovs, 'lsb_release')
    @patch('os.path.exists')
    def test_setup_eni_sources_eni_folder(self, exists, lsb_release):
        exists.return_value = True
        lsb_release.return_value = {'DISTRIB_CODENAME': 'bionic'}
        with patch_open() as (_, mock_file):
            # Mocked initial /etc/network/interfaces file content:
            mock_file.__iter__.return_value = [
                'some line',
                'some other line']

            ovs.setup_eni()
            mock_file.write.assert_called_once_with(
                '\nsource /etc/network/interfaces.d/*')

    @patch.object(ovs, 'lsb_release')
    @patch('os.path.exists')
    def test_setup_eni_wont_source_eni_folder_twice(self, exists, lsb_release):
        exists.return_value = True
        lsb_release.return_value = {'DISTRIB_CODENAME': 'bionic'}
        with patch_open() as (_, mock_file):
            # Mocked initial /etc/network/interfaces file content:
            mock_file.__iter__.return_value = [
                'some line',
                '  source    /etc/network/interfaces.d/*   ',
                'some other line']

            ovs.setup_eni()
            self.assertFalse(mock_file.write.called)

    @patch.object(ovs, 'lsb_release')
    def test_setup_eni_raises_on_focal(self, lsb_release):
        lsb_release.return_value = {'DISTRIB_CODENAME': 'focal'}
        self.assertRaises(RuntimeError, ovs.setup_eni)
