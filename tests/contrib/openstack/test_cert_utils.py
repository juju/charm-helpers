import json
import mock
import unittest

import charmhelpers.contrib.openstack.cert_utils as cert_utils


class CertUtilsTests(unittest.TestCase):

    def test_CertRequest(self):
        cr = cert_utils.CertRequest()
        self.assertEqual(cr.entries, [])
        self.assertIsNone(cr.hostname_entry)

    def test_CertRequest_add_entry(self):
        cr = cert_utils.CertRequest()
        cr.add_entry('admin', 'admin.openstack.local', ['10.10.10.10'])
        self.assertEqual(
            cr.get_request(),
            {'cert_requests':
                '{"admin.openstack.local": {"sans": ["10.10.10.10"]}}'})

    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'unit_get')
    def test_CertRequest_add_hostname_cn(self, unit_get, get_hostname,
                                         get_vip_in_network,
                                         resolve_network_cidr):
        resolve_network_cidr.side_effect = lambda x: x
        get_vip_in_network.return_value = '10.1.2.100'
        unit_get.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        cr = cert_utils.CertRequest()
        cr.add_hostname_cn()
        self.assertEqual(
            cr.get_request(),
            {'cert_requests':
                '{"juju-unit-2": {"sans": ["10.1.2.100", "10.1.2.3"]}}'})

    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'unit_get')
    def test_CertRequest_add_hostname_cn_ip(self, unit_get, get_hostname,
                                            get_vip_in_network,
                                            resolve_network_cidr):
        resolve_network_cidr.side_effect = lambda x: x
        get_vip_in_network.return_value = '10.1.2.100'
        unit_get.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        cr = cert_utils.CertRequest()
        cr.add_hostname_cn()
        cr.add_hostname_cn_ip(['10.1.2.4'])
        self.assertEqual(
            cr.get_request(),
            {'cert_requests':
                ('{"juju-unit-2": {"sans": ["10.1.2.100", "10.1.2.3", '
                 '"10.1.2.4"]}}')})

    @mock.patch.object(cert_utils, 'resolve_network_cidr')
    @mock.patch.object(cert_utils, 'get_vip_in_network')
    @mock.patch.object(cert_utils, 'network_get_primary_address')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'config')
    @mock.patch.object(cert_utils, 'get_hostname')
    @mock.patch.object(cert_utils, 'unit_get')
    def test_get_certificate_request(self, unit_get, get_hostname,
                                     config, resolve_address,
                                     network_get_primary_address,
                                     get_vip_in_network, resolve_network_cidr):
        unit_get.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _config = {
            'os-internal-hostname': 'internal.openstack.local',
            'os-admin-hostname': 'admin.openstack.local',
            'os-public-hostname': 'public.openstack.local',
        }
        _resolve_address = {
            'int': '10.0.0.2',
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

    @mock.patch.object(cert_utils, 'unit_get')
    @mock.patch.object(cert_utils.os, 'symlink')
    @mock.patch.object(cert_utils.os.path, 'isfile')
    @mock.patch.object(cert_utils, 'resolve_address')
    @mock.patch.object(cert_utils, 'get_hostname')
    def test_create_ip_cert_links(self, get_hostname, resolve_address, isfile,
                                  symlink, unit_get):
        unit_get.return_value = '10.1.2.3'
        get_hostname.return_value = 'juju-unit-2'
        _resolve_address = {
            'int': '10.0.0.2',
            'admin': '10.10.0.2',
            'public': '10.20.0.2',
        }
        resolve_address.side_effect = \
            lambda endpoint_type: _resolve_address[endpoint_type]
        _files = {
            '/etc/ssl/cert_juju-unit-2': True,
            '/etc/ssl/cert_10.0.0.2': False,
            '/etc/ssl/cert_10.10.0.2': True,
            '/etc/ssl/cert_10.20.0.2': False,
            '/etc/ssl/cert_funky-name': False,
        }
        isfile.side_effect = lambda x: _files[x]
        expected = [
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_10.0.0.2'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_10.0.0.2'),
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_10.20.0.2'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_10.20.0.2'),
        ]
        cert_utils.create_ip_cert_links('/etc/ssl')
        symlink.assert_has_calls(expected)
        symlink.reset_mock()
        cert_utils.create_ip_cert_links(
            '/etc/ssl',
            custom_hostname_link='funky-name')
        expected.extend([
            mock.call('/etc/ssl/cert_juju-unit-2', '/etc/ssl/cert_funky-name'),
            mock.call('/etc/ssl/key_juju-unit-2', '/etc/ssl/key_funky-name'),
        ])
        symlink.assert_has_calls(expected)

    @mock.patch.object(cert_utils, 'write_file')
    def test_install_certs(self, write_file):
        certs = {
            'admin.openstack.local': {
                'cert': 'ADMINCERT',
                'key': 'ADMINKEY'}}
        cert_utils.install_certs('/etc/ssl', certs)
        expected = [
            mock.call(
                path='/etc/ssl/cert_admin.openstack.local',
                content='ADMINCERT',
                perms=0o640),
            mock.call(
                path='/etc/ssl/key_admin.openstack.local',
                content='ADMINKEY',
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
                content='ADMINCERTMYCA',
                perms=0o640),
            mock.call(
                path='/etc/ssl/key_admin.openstack.local',
                content='ADMINKEY',
                perms=0o640),
        ]
        write_file.assert_has_calls(expected)

    @mock.patch.object(cert_utils, 'local_unit')
    @mock.patch.object(cert_utils, 'create_ip_cert_links')
    @mock.patch.object(cert_utils, 'install_certs')
    @mock.patch.object(cert_utils, 'install_ca_cert')
    @mock.patch.object(cert_utils, 'mkdir')
    @mock.patch.object(cert_utils, 'relation_get')
    def test_process_certificates(self, relation_get, mkdir, install_ca_cert,
                                  install_certs, create_ip_cert_links,
                                  local_unit):
        local_unit.return_value = 'keystone/2'
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
        cert_utils.process_certificates(
            'myservice',
            'certificates:2',
            'vault/0',
            custom_hostname_link='funky-name')
        install_ca_cert.assert_called_once_with(b'ROOTCA')
        install_certs.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            {'admin.openstack.local': {
                'key': 'ADMINKEY', 'cert': 'ADMINCERT'}},
            'MYCHAIN')
        create_ip_cert_links.assert_called_once_with(
            '/etc/apache2/ssl/myservice',
            custom_hostname_link='funky-name')

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
