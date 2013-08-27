from contextlib import contextmanager
import subprocess

from mock import patch, call, MagicMock
from testtools import TestCase

from charmhelpers.contrib import ssl


@contextmanager
def patch_open():
    '''Patch open() to allow mocking both open() itself and the file that is
    yielded.

    Yields the mock for "open" and "file", respectively.'''
    mock_open = MagicMock(spec=open)
    mock_file = MagicMock(spec=file)

    @contextmanager
    def stub_open(*args, **kwargs):
        mock_open(*args, **kwargs)
        yield mock_file

    with patch('__builtin__.open', stub_open):
        yield mock_open, mock_file


@contextmanager
def mock_open(filename, contents=None):
    ''' Slightly simpler mock of open to return contents for filename '''
    def mock_file(*args):
        if args[0] == filename:
            return io.StringIO(contents)
        else:
            return open(*args)
    with patch('__builtin__.open', mock_file):
        yield


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
                                      '/C=UK/ST=my_state/L=my_locality/'
                                      'O=my_organization/OU=my_unit/'
                                      'CN=mysite.example.com/'
                                      'emailAddress=me@example.com']
                                     )

    @patch('subprocess.check_call')
    def test_generate_selfsigned_file(self, mock_call):
        ssl.generate_selfsigned("mykey.key", "mycert.crt", config="test.cnf")
        mock_call.assert_called_with(['/usr/bin/openssl', 'req', '-new',
                                      '-newkey', 'rsa:1024', '-days', '365',
                                      '-nodes', '-x509', '-keyout',
                                      'mykey.key', '-out', 'mycert.crt',
                                      '-config', 'test.cnf'])
