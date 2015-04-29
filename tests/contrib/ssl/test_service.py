from testtools import TestCase
import tempfile
import shutil
import subprocess
import six
import mock

from os.path import exists, join, isdir

from charmhelpers.contrib.ssl import service


class ServiceCATest(TestCase):

    def setUp(self):
        super(ServiceCATest, self).setUp()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(ServiceCATest, self).tearDown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @mock.patch("charmhelpers.contrib.ssl.service.log")
    def test_init(self, *args):
        """
        Tests that a ServiceCA is initialized with the correct directory
        layout.
        """
        ca_root_dir = join(self.temp_dir, 'ca')
        ca = service.ServiceCA('fake-name', ca_root_dir)
        ca.init()

        paths_to_verify = [
            'certs/',
            'crl/',
            'newcerts/',
            'private/',
            'private/cacert.key',
            'cacert.pem',
            'serial',
            'index.txt',
            'ca.cnf',
            'signing.cnf',
        ]

        for path in paths_to_verify:
            full_path = join(ca_root_dir, path)
            self.assertTrue(exists(full_path),
                            'Path {} does not exist'.format(full_path))

            if path.endswith('/'):
                self.assertTrue(isdir(full_path),
                                'Path {} is not a dir'.format(full_path))

    @mock.patch("charmhelpers.contrib.ssl.service.log")
    def test_create_cert(self, *args):
        """
        Tests that a generated certificate is valid against the ca.
        """
        ca_root_dir = join(self.temp_dir, 'ca')
        ca = service.ServiceCA('fake-name', ca_root_dir)
        ca.init()

        ca.get_or_create_cert('fake-cert')

        # Verify that the cert belongs to the ca
        self.assertTrue('fake-cert' in ca)

        full_cert_path = join(ca_root_dir, 'certs', 'fake-cert.crt')
        cmd = ['openssl', 'verify', '-verbose',
               '-CAfile', join(ca_root_dir, 'cacert.pem'), full_cert_path]

        output = subprocess.check_output(cmd,
                                         stderr=subprocess.STDOUT).strip()
        expected = '{}: OK'.format(full_cert_path)
        if six.PY3:
            expected = bytes(expected, 'utf-8')
        self.assertEqual(expected, output)
