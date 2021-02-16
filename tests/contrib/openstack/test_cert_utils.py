import json
import mock
import unittest

import charmhelpers.contrib.openstack.cert_utils as cert_utils


class CertUtilsTests(unittest.TestCase):

    def test_CertRequest(self):
        cr = cert_utils.CertRequest()
        self.assertEqual(cr.entries, [])
        self.assertIsNone(cr.hostname_entry)

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    def test_CertRequest_add_entry(self, local_unit):
        cr = cert_utils.CertRequest()
        cr.add_entry('admin', 'admin.openstack.local', ['10.10.10.10'])
        self.assertEqual(
            cr.get_request(),
            {'cert_requests':
                '{"admin.openstack.local": {"sans": ["10.10.10.10"]}}',
             'unit_name': 'unit_2'})

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_CertRequest_add_hostname_cn(self, local_address, get_hostname,
                                         get_vip_in_network,
                                         resolve_network_cidr, local_unit):
        resolve_network_cidr.side_effect = lambda x: x
        get_vip_in_network.return_value = '10.1.2.100'
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        cr = cert_utils.CertRequest()
        cr.add_hostname_cn()
        self.assertEqual(
            cr.get_request(),
            {'cert_requests':
                '{"juju-unit-2": {"sans": ["10.1.2.100", "10.1.2.3"]}}',
             'unit_name': 'unit_2'})

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_CertRequest_add_hostname_cn_ip(self, local_address, get_hostname,
                                            get_vip_in_network,
                                            resolve_network_cidr, local_unit):
        resolve_network_cidr.side_effect = lambda x: x
        get_vip_in_network.return_value = '10.1.2.100'
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        cr = cert_utils.CertRequest()
        cr.add_hostname_cn()
        cr.add_hostname_cn_ip(['10.1.2.4'])
        self.assertEqual(
            cr.get_request(),
            {'cert_requests':
                ('{"juju-unit-2": {"sans": ["10.1.2.100", "10.1.2.3", '
                 '"10.1.2.4"]}}'),
             'unit_name': 'unit_2'})

    @mock.patch.object(cert_utils, 'get_certificate_sans')
    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'network_get_primary_address')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_get_certificate_request(self, local_address, get_hostname,
                                     config, resolve_address,
                                     network_get_primary_address,
                                     get_vip_in_network, resolve_network_cidr,
                                     local_unit, get_certificate_sans):
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _config = {
            'os-internal-hostname': 'internal.openstack.local',
            'os-admin-hostname': 'admin.openstack.local',
            'os-public-hostname': 'public.openstack.local',
        }
        _resolve_address = {
            'int': '10.0.0.2',
            'internal': '10.0.0.2',
            'admin': '10.10.0.2',
            'public': '10.20.0.2',
        }
        _npa = {
            'internal': '10.0.0.3',
            'admin': '10.10.0.3',
            'public': '10.20.0.3',
        }
        _vips = {
            '10.0.0.0/16': '10.0.0.100',
            '10.10.0.0/16': '10.10.0.100',
            '10.20.0.0/16': '10.20.0.100',
        }
        _resolve_nets = {
            '10.0.0.3': '10.0.0.0/16',
            '10.10.0.3': '10.10.0.0/16',
            '10.20.0.3': '10.20.0.0/16',
        }
        get_certificate_sans.return_value = list(set(
            list(_resolve_address.values()) +
            list(_npa.values()) +
            list(_vips.values())))
        expect = {
            'admin.openstack.local': {
                'sans': ['10.10.0.100', '10.10.0.2', '10.10.0.3']},
            'internal.openstack.local': {
                'sans': ['10.0.0.100', '10.0.0.2', '10.0.0.3']},
            'juju-unit-2': {'sans': ['10.1.2.3']},
            'public.openstack.local': {
                'sans': ['10.20.0.100', '10.20.0.2', '10.20.0.3']}}
        self.maxDiff = None
        config.side_effect = lambda x: _config.get(x)
        get_vip_in_network.side_effect = lambda x: _vips.get(x)
        resolve_network_cidr.side_effect = lambda x: _resolve_nets.get(x)
        network_get_primary_address.side_effect = lambda x: _npa.get(x)
        resolve_address.side_effect = \
            lambda endpoint_type: _resolve_address[endpoint_type]
        output = json.loads(
            cert_utils.get_certificate_request()['cert_requests'])
        self.assertEqual(
            output,
            expect)
        get_certificate_sans.assert_called_once_with(
            bindings=['internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'get_certificate_sans')
    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'network_get_primary_address')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_get_certificate_request_no_hostnames(
            self, local_address, get_hostname, config, resolve_address,
            network_get_primary_address, get_vip_in_network,
            resolve_network_cidr, local_unit, get_certificate_sans):
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _config = {
            'os-admin-hostname': 'admin.openstack.local',
            'os-public-hostname': 'public.openstack.local',
        }
        _resolve_address = {
            'int': '10.0.0.2',
            'internal': '10.0.0.2',
            'admin': '10.10.0.2',
            'public': '10.20.0.2',
        }
        _npa = {
            'internal': '10.0.0.3',
            'admin': '10.10.0.3',
            'public': '10.20.0.3',
            'mybinding': '10.30.0.3',
        }
        _vips = {
            '10.0.0.0/16': '10.0.0.100',
            '10.10.0.0/16': '10.10.0.100',
            '10.20.0.0/16': '10.20.0.100',
        }
        _resolve_nets = {
            '10.0.0.3': '10.0.0.0/16',
            '10.10.0.3': '10.10.0.0/16',
            '10.20.0.3': '10.20.0.0/16',
        }
        get_certificate_sans.return_value = list(set(
            list(_resolve_address.values()) +
            list(_npa.values()) +
            list(_vips.values())))
        expect = {
            'admin.openstack.local': {
                'sans': ['10.10.0.100', '10.10.0.2', '10.10.0.3']},
            'juju-unit-2': {'sans': [
                '10.0.0.100', '10.0.0.2', '10.0.0.3', '10.1.2.3', '10.30.0.3']},
            'public.openstack.local': {
                'sans': ['10.20.0.100', '10.20.0.2', '10.20.0.3']}}
        self.maxDiff = None
        config.side_effect = lambda x: _config.get(x)
        get_vip_in_network.side_effect = lambda x: _vips.get(x)
        resolve_network_cidr.side_effect = lambda x: _resolve_nets.get(x)
        network_get_primary_address.side_effect = lambda x: _npa.get(x)
        resolve_address.side_effect = \
            lambda endpoint_type: _resolve_address[endpoint_type]
        output = json.loads(
            cert_utils.get_certificate_request(
                bindings=['mybinding'])['cert_requests'])
        self.assertEqual(
            output,
            expect)
        get_certificate_sans.assert_called_once_with(
            bindings=['mybinding', 'internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'get_certificate_request')
    @mock.patch.object(cert_utils, 'local_address')
    @mock.patch.object(cert_utils.os, 'symlink')
    @mock.patch.object(cert_utils.os.path, 'isfile')
    @mock.patch.object(cert_utils, 'get_hostname')
    def test_create_ip_cert_links(self, get_hostname, isfile,
                                  symlink, local_address, get_cert_request):
        cert_request = {'cert_requests': {
            'admin.openstack.local': {
                'sans': ['10.10.0.100', '10.10.0.2', '10.10.0.3']},
            'internal.openstack.local': {
                'sans': ['10.0.0.100', '10.0.0.2', '10.0.0.3']},
            'juju-unit-2': {'sans': ['10.1.2.3']},
            'public.openstack.local': {
                'sans': ['10.20.0.100', '10.20.0.2', '10.20.0.3']}}}
        get_cert_request.return_value = cert_request
        _files = {
            '/etc/ssl/cert_juju-unit-2': True,
            '/etc/ssl/cert_10.1.2.3': False,
            '/etc/ssl/cert_admin.openstack.local': True,
            '/etc/ssl/cert_10.10.0.100': False,
            '/etc/ssl/cert_10.10.0.2': False,
            '/etc/ssl/cert_10.10.0.3': False,
            '/etc/ssl/cert_internal.openstack.local': True,
            '/etc/ssl/cert_10.0.0.100': False,
            '/etc/ssl/cert_10.0.0.2': False,
            '/etc/ssl/cert_10.0.0.3': False,
            '/etc/ssl/cert_public.openstack.local': True,
            '/etc/ssl/cert_10.20.0.100': False,
            '/etc/ssl/cert_10.20.0.2': False,
            '/etc/ssl/cert_10.20.0.3': False,
            '/etc/ssl/cert_funky-name': False,
        }
        isfile.side_effect = lambda x: _files[x]
        expected = [
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.100'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.100'),
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.2'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.2'),
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.3'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.3'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.100'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.100'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.2'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.2'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.3'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.3'),
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_10.1.2.3'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_10.1.2.3'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.100'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.100'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.2'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.2'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.3'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.3')]
        cert_utils.create_ip_cert_links('/etc/ssl')
        symlink.assert_has_calls(expected, any_order=True)
        # Customer hostname
        symlink.reset_mock()
        get_hostname.return_value = 'juju-unit-2'
        cert_utils.create_ip_cert_links(
            '/etc/ssl',
            custom_hostname_link='funky-name')
        expected.extend([
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_funky-name'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_funky-name'),
        ])
        symlink.assert_has_calls(expected, any_order=True)
        get_cert_request.assert_called_with(
            json_encode=False, bindings=['internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'get_certificate_request')
    @mock.patch.object(cert_utils, 'local_address')
    @mock.patch.object(cert_utils.os, 'symlink')
    @mock.patch.object(cert_utils.os.path, 'isfile')
    @mock.patch.object(cert_utils, 'get_hostname')
    def test_create_ip_cert_links_bindings(
            self, get_hostname, isfile, symlink, local_address, get_cert_request):
        cert_request = {'cert_requests': {
            'admin.openstack.local': {
                'sans': ['10.10.0.100', '10.10.0.2', '10.10.0.3']},
            'internal.openstack.local': {
                'sans': ['10.0.0.100', '10.0.0.2', '10.0.0.3']},
            'juju-unit-2': {'sans': ['10.1.2.3']},
            'public.openstack.local': {
                'sans': ['10.20.0.100', '10.20.0.2', '10.20.0.3']}}}
        get_cert_request.return_value = cert_request
        _files = {
            '/etc/ssl/cert_juju-unit-2': True,
            '/etc/ssl/cert_10.1.2.3': False,
            '/etc/ssl/cert_admin.openstack.local': True,
            '/etc/ssl/cert_10.10.0.100': False,
            '/etc/ssl/cert_10.10.0.2': False,
            '/etc/ssl/cert_10.10.0.3': False,
            '/etc/ssl/cert_internal.openstack.local': True,
            '/etc/ssl/cert_10.0.0.100': False,
            '/etc/ssl/cert_10.0.0.2': False,
            '/etc/ssl/cert_10.0.0.3': False,
            '/etc/ssl/cert_public.openstack.local': True,
            '/etc/ssl/cert_10.20.0.100': False,
            '/etc/ssl/cert_10.20.0.2': False,
            '/etc/ssl/cert_10.20.0.3': False,
            '/etc/ssl/cert_funky-name': False,
        }
        isfile.side_effect = lambda x: _files[x]
        expected = [
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.100'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.100'),
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.2'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.2'),
            mock.call('/etc/ssl/cert_admin.openstack.local', '/etc/ssl/cert_10.10.0.3'),
            mock.call('/etc/ssl/key_admin.openstack.local', '/etc/ssl/key_10.10.0.3'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.100'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.100'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.2'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.2'),
            mock.call('/etc/ssl/cert_internal.openstack.local', '/etc/ssl/cert_10.0.0.3'),
            mock.call('/etc/ssl/key_internal.openstack.local', '/etc/ssl/key_10.0.0.3'),
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_10.1.2.3'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_10.1.2.3'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.100'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.100'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.2'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.2'),
            mock.call('/etc/ssl/cert_public.openstack.local', '/etc/ssl/cert_10.20.0.3'),
            mock.call('/etc/ssl/key_public.openstack.local', '/etc/ssl/key_10.20.0.3')]
        cert_utils.create_ip_cert_links('/etc/ssl', bindings=['mybindings'])
        symlink.assert_has_calls(expected, any_order=True)
        # Customer hostname
        symlink.reset_mock()
        get_hostname.return_value = 'juju-unit-2'
        cert_utils.create_ip_cert_links(
            '/etc/ssl',
            custom_hostname_link='funky-name', bindings=['mybinding'])
        expected.extend([
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_funky-name'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_funky-name'),
        ])
        symlink.assert_has_calls(expected, any_order=True)
        get_cert_request.assert_called_with(
            json_encode=False, bindings=['mybinding', 'internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'write_file')
    def test_install_certs(self, write_file):
        certs = {
            'admin.openstack.local': {
                'cert': 'ADMINCERT',
                'key': 'ADMINKEY'}}
        cert_utils.install_certs('/etc/ssl', certs, chain='CHAIN')
        expected = [
            mock.call(
                path='/etc/ssl/cert_admin.openstack.local',
                content='ADMINCERT\nCHAIN',
                owner='root', group='root',
                perms=0o640),
            mock.call(
                path='/etc/ssl/key_admin.openstack.local',
                content='ADMINKEY',
                owner='root', group='root',
                perms=0o640),
        ]
        write_file.assert_has_calls(expected)

    @mock.patch.object(cert_utils, 'write_file')
    def test_install_certs_ca(self, write_file):
        certs = {
            'admin.openstack.local': {
                'cert': 'ADMINCERT',
                'key': 'ADMINKEY'}}
        ca = 'MYCA'
        cert_utils.install_certs('/etc/ssl', certs, ca)
        expected = [
            mock.call(
                path='/etc/ssl/cert_admin.openstack.local',
                content='ADMINCERT\nMYCA',
                owner='root', group='root',
                perms=0o640),
            mock.call(
                path='/etc/ssl/key_admin.openstack.local',
                content='ADMINKEY',
                owner='root', group='root',
                perms=0o640),
        ]
        write_file.assert_has_calls(expected)

    @mock.patch.object(cert_utils, '_manage_ca_certs')
    @mock.patch.object(cert_utils, 'remote_service_name')
    @mock.patch.object(cert_utils, 'local_unit')
    @mock.patch.object(cert_utils, 'create_ip_cert_links')
    @mock.patch.object(cert_utils, 'install_certs')
    @mock.patch.object(cert_utils, 'install_ca_cert')
    @mock.patch.object(cert_utils, 'mkdir')
    @mock.patch.object(cert_utils, 'relation_get')
    def test_process_certificates(self, relation_get, mkdir, install_ca_cert,
                                  install_certs, create_ip_cert_links,
                                  local_unit, remote_service_name,
                                  _manage_ca_certs):
        remote_service_name.return_value = 'vault'
        local_unit.return_value = 'devnull/2'
        certs = {
            'admin.openstack.local': {
                'cert': 'ADMINCERT',
                'key': 'ADMINKEY'}}
        _relation_info = {
            'keystone_2.processed_requests': json.dumps(certs),
            'chain': 'MYCHAIN',
            'ca': 'ROOTCA',
        }
        relation_get.return_value = _relation_info
        self.assertFalse(cert_utils.process_certificates(
            'myservice',
            'certificates:2',
            'vault/0',
            custom_hostname_link='funky-name'))
        local_unit.return_value = 'keystone/2'
        self.assertTrue(cert_utils.process_certificates(
            'myservice',
            'certificates:2',
            'vault/0',
            custom_hostname_link='funky-name'))
        _manage_ca_certs.assert_called_once_with(
            'ROOTCA', 'certificates:2')
        install_certs.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            {'admin.openstack.local': {
                'key': 'ADMINKEY', 'cert': 'ADMINCERT'}},
            'MYCHAIN', user='root', group='root')
        create_ip_cert_links.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            custom_hostname_link='funky-name',
            bindings=['internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, '_manage_ca_certs')
    @mock.patch.object(cert_utils, 'remote_service_name')
    @mock.patch.object(cert_utils, 'local_unit')
    @mock.patch.object(cert_utils, 'create_ip_cert_links')
    @mock.patch.object(cert_utils, 'install_certs')
    @mock.patch.object(cert_utils, 'install_ca_cert')
    @mock.patch.object(cert_utils, 'mkdir')
    @mock.patch.object(cert_utils, 'relation_get')
    def test_process_certificates_bindings(
            self, relation_get, mkdir, install_ca_cert,
            install_certs, create_ip_cert_links,
            local_unit, remote_service_name, _manage_ca_certs):
        remote_service_name.return_value = 'vault'
        local_unit.return_value = 'devnull/2'
        certs = {
            'admin.openstack.local': {
                'cert': 'ADMINCERT',
                'key': 'ADMINKEY'}}
        _relation_info = {
            'keystone_2.processed_requests': json.dumps(certs),
            'chain': 'MYCHAIN',
            'ca': 'ROOTCA',
        }
        relation_get.return_value = _relation_info
        self.assertFalse(cert_utils.process_certificates(
            'myservice',
            'certificates:2',
            'vault/0',
            custom_hostname_link='funky-name'))
        local_unit.return_value = 'keystone/2'
        self.assertTrue(cert_utils.process_certificates(
            'myservice',
            'certificates:2',
            'vault/0',
            custom_hostname_link='funky-name',
            bindings=['mybinding']))
        _manage_ca_certs.assert_called_once_with(
            'ROOTCA', 'certificates:2')
        install_certs.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            {'admin.openstack.local': {
                'key': 'ADMINKEY', 'cert': 'ADMINCERT'}},
            'MYCHAIN', user='root', group='root')
        create_ip_cert_links.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            custom_hostname_link='funky-name',
            bindings=['mybinding', 'internal', 'admin', 'public'])

    @mock.patch.object(cert_utils, 'remote_service_name')
    @mock.patch.object(cert_utils, 'relation_ids')
    def test_get_cert_relation_ca_name(self, relation_ids, remote_service_name):
        remote_service_name.return_value = 'vault'

        # Test with argument:
        self.assertEqual(cert_utils.get_cert_relation_ca_name('certificates:1'),
                         'vault_juju_ca_cert')
        remote_service_name.assert_called_once_with(relid='certificates:1')
        remote_service_name.reset_mock()

        # Test without argument:
        relation_ids.return_value = ['certificates:2']
        self.assertEqual(cert_utils.get_cert_relation_ca_name(),
                         'vault_juju_ca_cert')
        remote_service_name.assert_called_once_with(relid='certificates:2')
        remote_service_name.reset_mock()

        # Test without argument nor 'certificates' relation:
        relation_ids.return_value = []
        self.assertEqual(cert_utils.get_cert_relation_ca_name(), '')
        remote_service_name.assert_not_called()

    @mock.patch.object(cert_utils, 'remote_service_name')
    @mock.patch.object(cert_utils.os, 'remove')
    @mock.patch.object(cert_utils.os.path, 'exists')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'install_ca_cert')
    def test__manage_ca_certs(self, install_ca_cert, config, os_exists,
                              os_remove, remote_service_name):
        remote_service_name.return_value = 'vault'
        _config = {}
        config.side_effect = lambda x: _config.get(x)
        os_exists.return_value = False
        cert_utils._manage_ca_certs('CA', 'certificates:2')
        install_ca_cert.assert_called_once_with(
            b'CA',
            name='vault_juju_ca_cert')
        self.assertFalse(os_remove.called)
        # Test old cert removed.
        install_ca_cert.reset_mock()
        os_exists.reset_mock()
        os_exists.return_value = True
        cert_utils._manage_ca_certs('CA', 'certificates:2')
        install_ca_cert.assert_called_once_with(
            b'CA',
            name='vault_juju_ca_cert')
        os_remove.assert_called_once_with(
            '/usr/local/share/ca-certificates/keystone_juju_ca_cert.crt')
        # Test cert is installed from config
        _config['ssl_ca'] = 'Q0FGUk9NQ09ORklHCg=='
        install_ca_cert.reset_mock()
        os_remove.reset_mock()
        os_exists.reset_mock()
        os_exists.return_value = True
        cert_utils._manage_ca_certs('CA', 'certificates:2')
        expected = [
            mock.call(b'CAFROMCONFIG', name='keystone_juju_ca_cert'),
            mock.call(b'CA', name='vault_juju_ca_cert')]
        install_ca_cert.assert_has_calls(expected)
        self.assertFalse(os_remove.called)

    @mock.patch.object(cert_utils, 'local_unit')
    @mock.patch.object(cert_utils, 'related_units')
    @mock.patch.object(cert_utils, 'relation_ids')
    @mock.patch.object(cert_utils, 'relation_get')
    def test_get_requests_for_local_unit(self, relation_get, relation_ids,
                                         related_units, local_unit):
        local_unit.return_value = 'rabbitmq-server/2'
        relation_ids.return_value = ['certificates:12']
        related_units.return_value = ['vault/0']
        certs = {
            'juju-cd4bb3-5.lxd': {
                'cert': 'BASECERT',
                'key': 'BASEKEY'},
            'juju-cd4bb3-5.internal': {
                'cert': 'INTERNALCERT',
                'key': 'INTERNALKEY'}}
        _relation_info = {
            'rabbitmq-server_2.processed_requests': json.dumps(certs),
            'chain': 'MYCHAIN',
            'ca': 'ROOTCA',
        }
        relation_get.return_value = _relation_info
        self.assertEqual(
            cert_utils.get_requests_for_local_unit(),
            [{
                'ca': 'ROOTCA',
                'certs': {
                    'juju-cd4bb3-5.lxd': {
                        'cert': 'BASECERT',
                        'key': 'BASEKEY'},
                    'juju-cd4bb3-5.internal': {
                        'cert': 'INTERNALCERT',
                        'key': 'INTERNALKEY'}},
                'chain': 'MYCHAIN'}]
        )

    @mock.patch.object(cert_utils, 'get_requests_for_local_unit')
    def test_get_bundle_for_cn(self, get_requests_for_local_unit):
        get_requests_for_local_unit.return_value = [{
            'ca': 'ROOTCA',
            'certs': {
                'juju-cd4bb3-5.lxd': {
                    'cert': 'BASECERT',
                    'key': 'BASEKEY'},
                'juju-cd4bb3-5.internal': {
                    'cert': 'INTERNALCERT',
                    'key': 'INTERNALKEY'}},
            'chain': 'MYCHAIN'}]
        self.assertEqual(
            cert_utils.get_bundle_for_cn('juju-cd4bb3-5.internal'),
            {
                'ca': 'ROOTCA',
                'cert': 'INTERNALCERT',
                'chain': 'MYCHAIN',
                'key': 'INTERNALKEY'})

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_relation_ip')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_get_certificate_sans(self, local_address, get_hostname,
                                  config, resolve_address,
                                  get_relation_ip,
                                  get_vip_in_network, resolve_network_cidr,
                                  local_unit):
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _config = {
            'os-internal-hostname': 'internal.openstack.local',
            'os-admin-hostname': 'admin.openstack.local',
            'os-public-hostname': 'public.openstack.local',
        }
        _resolve_address = {
            'int': '10.0.0.2',
            'internal': '10.0.0.2',
            'admin': '10.10.0.2',
            'public': '10.20.0.2',
        }
        _npa = {
            'internal': '10.0.0.3',
            'admin': '10.10.0.3',
            'public': '10.20.0.3',
        }
        _vips = {
            '10.0.0.0/16': '10.0.0.100',
            '10.10.0.0/16': '10.10.0.100',
            '10.20.0.0/16': '10.20.0.100',
        }
        _resolve_nets = {
            '10.0.0.3': '10.0.0.0/16',
            '10.10.0.3': '10.10.0.0/16',
            '10.20.0.3': '10.20.0.0/16',
        }
        expect = list(set([
            '10.10.0.100', '10.10.0.2', '10.10.0.3',
            '10.0.0.100', '10.0.0.2', '10.0.0.3',
            '10.1.2.3',
            '10.20.0.100', '10.20.0.2', '10.20.0.3']))
        self.maxDiff = None
        config.side_effect = lambda x: _config.get(x)
        get_vip_in_network.side_effect = lambda x: _vips.get(x)
        resolve_network_cidr.side_effect = lambda x: _resolve_nets.get(x)
        get_relation_ip.side_effect = lambda x, cidr_network: _npa.get(x)
        resolve_address.side_effect = \
            lambda endpoint_type: _resolve_address[endpoint_type]
        expected_get_relation_ip_calls = [
            mock.call('internal', cidr_network=None),
            mock.call('admin', cidr_network=None),
            mock.call('public', cidr_network=None)]
        self.assertEqual(cert_utils.get_certificate_sans().sort(),
                         expect.sort())
        get_relation_ip.assert_has_calls(
            expected_get_relation_ip_calls, any_order=True)

    @mock.patch.object(cert_utils, 'local_unit', return_value='unit/2')
    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_relation_ip')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'local_address')
    def test_get_certificate_sans_bindings(
            self, local_address, get_hostname, config, resolve_address,
            get_relation_ip, get_vip_in_network, resolve_network_cidr, local_unit):
        local_address.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _config = {
            'os-internal-hostname': 'internal.openstack.local',
            'os-admin-hostname': 'admin.openstack.local',
            'os-public-hostname': 'public.openstack.local',
        }
        _resolve_address = {
            'int': '10.0.0.2',
            'internal': '10.0.0.2',
            'admin': '10.10.0.2',
            'public': '10.20.0.2',
        }
        _npa = {
            'internal': '10.0.0.3',
            'admin': '10.10.0.3',
            'public': '10.20.0.3',
        }
        _vips = {
            '10.0.0.0/16': '10.0.0.100',
            '10.10.0.0/16': '10.10.0.100',
            '10.20.0.0/16': '10.20.0.100',
        }
        _resolve_nets = {
            '10.0.0.3': '10.0.0.0/16',
            '10.10.0.3': '10.10.0.0/16',
            '10.20.0.3': '10.20.0.0/16',
        }
        expect = list(set([
            '10.10.0.100', '10.10.0.2', '10.10.0.3',
            '10.0.0.100', '10.0.0.2', '10.0.0.3',
            '10.1.2.3',
            '10.20.0.100', '10.20.0.2', '10.20.0.3']))
        self.maxDiff = None
        config.side_effect = lambda x: _config.get(x)
        get_vip_in_network.side_effect = lambda x: _vips.get(x)
        resolve_network_cidr.side_effect = lambda x: _resolve_nets.get(x)
        get_relation_ip.side_effect = lambda x, cidr_network: _npa.get(x)
        resolve_address.side_effect = \
            lambda endpoint_type: _resolve_address[endpoint_type]
        expected_get_relation_ip_calls = [
            mock.call('internal', cidr_network=None),
            mock.call('admin', cidr_network=None),
            mock.call('public', cidr_network=None),
            mock.call('mybinding', cidr_network=None)]
        self.assertEqual(
            cert_utils.get_certificate_sans(bindings=['mybinding']).sort(),
            expect.sort())
        get_relation_ip.assert_has_calls(
            expected_get_relation_ip_calls, any_order=True)
