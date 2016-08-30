import os

from unittest import TestCase
from mock import (
    MagicMock,
    patch,
    mock_open,
    Mock,
    ANY
)
from charmhelpers.fetch import (
    archiveurl,
    UnhandledSource,
)

import six
if six.PY3:
    from urllib.parse import urlparse
    from urllib.error import URLError
else:
    from urllib2 import URLError
    from urlparse import urlparse


class ArchiveUrlFetchHandlerTest(TestCase):

    def setUp(self):
        super(ArchiveUrlFetchHandlerTest, self).setUp()
        self.valid_urls = (
            "http://example.com/foo.tar.gz",
            "http://example.com/foo.tgz",
            "http://example.com/foo.tar.bz2",
            "http://example.com/foo.tbz2",
            "http://example.com/foo.zip",
            "http://example.com/foo.zip?bar=baz&x=y#whee",
            "ftp://example.com/foo.tar.gz",
            "https://example.com/foo.tgz",
            "file://example.com/foo.tar.bz2",
        )
        self.invalid_urls = (
            "git://example.com/foo.tar.gz",
            "http://example.com/foo",
            "http://example.com/foobar=baz&x=y#tar.gz",
            "http://example.com/foobar?h=baz.zip",
            "bzr+ssh://example.com/foo.tar.gz",
            "lp:example/foo.tgz",
            "file//example.com/foo.tar.bz2",
            "garbage",
        )
        self.fh = archiveurl.ArchiveUrlFetchHandler()

    def test_handles_archive_urls(self):
        for url in self.valid_urls:
            result = self.fh.can_handle(url)
            self.assertEqual(result, True, url)
        for url in self.invalid_urls:
            result = self.fh.can_handle(url)
            self.assertNotEqual(result, True, url)

    @patch('charmhelpers.fetch.archiveurl.urlopen')
    def test_downloads(self, _urlopen):
        for url in self.valid_urls:
            response = MagicMock()
            response.read.return_value = "bar"
            _urlopen.return_value = response

            _open = mock_open()
            with patch('charmhelpers.fetch.archiveurl.open',
                       _open, create=True):
                self.fh.download(url, "foo")

            response.read.assert_called_with()
            _open.assert_called_once_with("foo", 'wb')
            _open().write.assert_called_with("bar")

    @patch('charmhelpers.fetch.archiveurl.check_hash')
    @patch('charmhelpers.fetch.archiveurl.mkdir')
    @patch('charmhelpers.fetch.archiveurl.extract')
    def test_installs(self, _extract, _mkdir, _check_hash):
        self.fh.download = MagicMock()

        for url in self.valid_urls:
            filename = urlparse(url).path
            dest = os.path.join('foo', 'fetched', os.path.basename(filename))
            _extract.return_value = dest
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                where = self.fh.install(url, checksum='deadbeef')
            self.fh.download.assert_called_with(url, dest)
            _extract.assert_called_with(dest, None)
            _check_hash.assert_called_with(dest, 'deadbeef', 'sha1')
            self.assertEqual(where, dest)
            _check_hash.reset_mock()

        url = "http://www.example.com/archive.tar.gz"

        self.fh.download.side_effect = URLError('fail')
        with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
            self.assertRaises(UnhandledSource, self.fh.install, url)

        self.fh.download.side_effect = OSError('fail')
        with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
            self.assertRaises(UnhandledSource, self.fh.install, url)

    @patch('charmhelpers.fetch.archiveurl.check_hash')
    @patch('charmhelpers.fetch.archiveurl.mkdir')
    @patch('charmhelpers.fetch.archiveurl.extract')
    def test_install_with_hash_in_url(self, _extract, _mkdir, _check_hash):
        self.fh.download = MagicMock()
        url = "file://example.com/foo.tar.bz2#sha512=beefdead"
        with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
            self.fh.install(url)
        _check_hash.assert_called_with(ANY, 'beefdead', 'sha512')

    @patch('charmhelpers.fetch.archiveurl.mkdir')
    @patch('charmhelpers.fetch.archiveurl.extract')
    def test_install_with_duplicate_hash_in_url(self, _extract, _mkdir):
        self.fh.download = MagicMock()
        url = "file://example.com/foo.tar.bz2#sha512=a&sha512=b"
        with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
            with self.assertRaisesRegexp(
                    TypeError, "Expected 1 hash value, not 2"):
                self.fh.install(url)

    @patch('charmhelpers.fetch.archiveurl.urlretrieve')
    @patch('charmhelpers.fetch.archiveurl.check_hash')
    def test_download_and_validate(self, vfmock, urlmock):
        urlmock.return_value = ('/tmp/tmpebM9Hv', Mock())
        dlurl = 'http://example.com/foo.tgz'
        dlhash = '988881adc9fc3655077dc2d4d757d480b5ea0e11'
        self.fh.download_and_validate(dlurl, dlhash)
        vfmock.assert_called_with('/tmp/tmpebM9Hv', dlhash, 'sha1')
