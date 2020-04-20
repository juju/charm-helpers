from mock import patch, call

from testtools import TestCase
from tests.helpers import patch_open, FakeRelation

import charmhelpers.contrib.hahelpers.apache as apache_utils

cert = '''
        -----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAMO1fWOu8ntUMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMTQwNDIyMTUzNDA0WhcNMjQwNDE5MTUzNDA0WjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEAuk6dmZnMvVxykNidNjbIwXM3ShhMpwCvUmWwpybFAIqhtNTuGJF9Ikp5
kzB+ThQV1onK8O8YarNGQx+MOISEnlJ5npj3Atp33pKGHRn69lHKGVfJvRbN4A90
1hTueYsELzfPV2YWm4c6nQiXRT6Cy0yaw/DE8fBTHzAiE9+/XGPsjn5VPv8H6Wa1
f/d5FblE+RtHP6YpRo9Jh3XAn3iC9fVr8rblS4rk7ev8LfH/yIG2wRVOEPC6lYfu
MEIwPpxKV0c3Z6lqtMOgC5dgzWjrbItnQfB0JaIzSFMMxDhNCJocQRJDQ+0jmj+K
rMGB1QRZlVLZxx0xnv38G0GyfFMv8QIDAQABo1AwTjAdBgNVHQ4EFgQUcxEj7X26
poFDa0lw40aAKIqyNp0wHwYDVR0jBBgwFoAUcxEj7X26poFDa0lw40aAKIqyNp0w
DAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAQe6RUCqTYf0Ns8fKfAEb
QSxZKqCst02oC0F3Gm0opWiUetxZqmAYTAjztmlRFIw7hgF/P95SY1ujGLZmiAlU
poOTjQ/i7MvjkXPVCo92izwXi65qRmJGbjduIirOAYtBmBmm3qS9BmoDlLQMVNYn
bwFImc9ar0h+o3/VH1hry+2vEVikXiKK5uKZI6B7ejNYfAWydq6ilzfKIh75W852
OSbKt3NB/BTZZUdCvK6+B+MoeuzQHDO0/QKBEBfaKFeJki3mdyzFlNbYio1z00rM
E2zl3kh9gkZnMuV1uzHdfKJbtTcNn4hCls5x7T21jn4joADHaVez8FloykBUABu3
qw==
-----END CERTIFICATE-----
'''

IDENTITY_NEW_STYLE_CERTS = {
    'identity-service:0': {
        'keystone/0': {
            'ssl_cert_test-cn': 'keystone_provided_cert',
            'ssl_key_test-cn': 'keystone_provided_key',
        }
    }
}

IDENTITY_OLD_STYLE_CERTS = {
    'identity-service:0': {
        'keystone/0': {
            'ssl_cert': 'keystone_provided_cert',
            'ssl_key': 'keystone_provided_key',
        }
    }
}


class ApacheUtilsTests(TestCase):
    def setUp(self):
        super(ApacheUtilsTests, self).setUp()
        [self._patch(m) for m in [
            'log',
            'config_get',
            'relation_get',
            'relation_ids',
            'relation_list',
            'host',
        ]]

    def _patch(self, method):
        _m = patch.object(apache_utils, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def test_get_cert_from_config(self):
        '''Ensure cert and key from charm config override relation'''
        self.config_get.side_effect = [
            'some_ca_cert',  # config_get('ssl_cert')
            'some_ca_key',  # config_Get('ssl_key')
        ]
        result = apache_utils.get_cert('test-cn')
        self.assertEquals(('some_ca_cert', 'some_ca_key'), result)

    def test_get_ca_cert_from_config(self):
        self.config_get.return_value = "some_ca_cert"
        self.assertEquals('some_ca_cert', apache_utils.get_ca_cert())

    def test_get_cert_from_relation(self):
        self.config_get.return_value = None
        rel = FakeRelation(IDENTITY_NEW_STYLE_CERTS)
        self.relation_ids.side_effect = rel.relation_ids
        self.relation_list.side_effect = rel.relation_units
        self.relation_get.side_effect = rel.get
        result = apache_utils.get_cert('test-cn')
        self.assertEquals(('keystone_provided_cert', 'keystone_provided_key'),
                          result)

    def test_get_cert_from_relation_deprecated(self):
        self.config_get.return_value = None
        rel = FakeRelation(IDENTITY_OLD_STYLE_CERTS)
        self.relation_ids.side_effect = rel.relation_ids
        self.relation_list.side_effect = rel.relation_units
        self.relation_get.side_effect = rel.get
        result = apache_utils.get_cert()
        self.assertEquals(('keystone_provided_cert', 'keystone_provided_key'),
                          result)

    def test_get_ca_cert_from_relation(self):
        self.config_get.return_value = None
        self.relation_ids.side_effect = [['identity-service:0'],
                                         ['identity-credentials:1']]
        self.relation_list.return_value = 'keystone/0'
        self.relation_get.side_effect = [
            'keystone_provided_ca',
        ]
        result = apache_utils.get_ca_cert()
        self.relation_ids.assert_has_calls([call('identity-service'),
                                            call('identity-credentials')])
        self.assertEquals('keystone_provided_ca',
                          result)

    @patch.object(apache_utils.os.path, 'isfile')
    def test_retrieve_ca_cert(self, _isfile):
        _isfile.return_value = True
        with patch_open() as (_open, _file):
            _file.read.return_value = cert
            self.assertEqual(
                apache_utils.retrieve_ca_cert('mycertfile'),
                cert)
            _open.assert_called_once_with('mycertfile', 'rb')

    @patch.object(apache_utils.os.path, 'isfile')
    def test_retrieve_ca_cert_no_file(self, _isfile):
        _isfile.return_value = False
        with patch_open() as (_open, _file):
            self.assertEqual(
                apache_utils.retrieve_ca_cert('mycertfile'),
                None)
            self.assertFalse(_open.called)
