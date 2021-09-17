from mock import patch
from testtools import TestCase

from charmhelpers.contrib import ssl


class HelpersTest(TestCase):
    @patch('subprocess.check_call')
    def test_generate_selfsigned_dict(self, mock_call):
        subject = {"country": "UK",
                   "locality": "my_locality",
                   "state": "my_state",
                   "organization": "my_organization",
                   "organizational_unit": "my_unit",
                   "cn": "mysite.example.com",
                   "email": "me@example.com"
                   }

        ssl.generate_selfsigned("mykey.key", "mycert.crt", subject=subject)
        mock_call.assert_called_with(['/usr/bin/openssl', 'req', '-new',
                                      '-newkey', 'rsa:1024', '-days', '365',
                                      '-nodes', '-x509', '-keyout',
                                      'mykey.key', '-out', 'mycert.crt',
                                      '-subj',
                                      '/C=UK/ST=my_state/L=my_locality'
                                      '/O=my_organization/OU=my_unit'
                                      '/CN=mysite.example.com'
                                      '/emailAddress=me@example.com']
                                     )

    @patch('charmhelpers.core.hookenv.log')
    def test_generate_selfsigned_failure(self, mock_log):
        # This is NOT enough, function requires cn key
        subject = {"country": "UK",
                   "locality": "my_locality"}

        result = ssl.generate_selfsigned("mykey.key", "mycert.crt", subject=subject)
        self.assertFalse(result)

    @patch('subprocess.check_call')
    def test_generate_selfsigned_file(self, mock_call):
        ssl.generate_selfsigned("mykey.key", "mycert.crt", config="test.cnf")
        mock_call.assert_called_with(['/usr/bin/openssl', 'req', '-new',
                                      '-newkey', 'rsa:1024', '-days', '365',
                                      '-nodes', '-x509', '-keyout',
                                      'mykey.key', '-out', 'mycert.crt',
                                      '-config', 'test.cnf'])

    @patch('subprocess.check_call')
    def test_generate_selfsigned_cn_key(self, mock_call):
        ssl.generate_selfsigned("mykey.key", "mycert.crt", keysize="2048", cn="mysite.example.com")
        mock_call.assert_called_with(['/usr/bin/openssl', 'req', '-new',
                                      '-newkey', 'rsa:2048', '-days', '365',
                                      '-nodes', '-x509', '-keyout',
                                      'mykey.key', '-out', 'mycert.crt',
                                      '-subj', '/CN=mysite.example.com'])
