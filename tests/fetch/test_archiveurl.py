import os
from testtools import TestCase
from urlparse import urlparse
from mock import (
    MagicMock,
    patch,
    mock_open,
    Mock,
)
from charmhelpers.fetch import (
    archiveurl,
    UnhandledSource,
)
import urllib2
import sys


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

    @patch('urllib2.urlopen')
    def test_downloads(self, _urlopen):
        for url in self.valid_urls:
            response = MagicMock()
            response.read.return_value = "bar"
            _urlopen.return_value = response

            _open = mock_open()
            with patch('charmhelpers.fetch.archiveurl.open', _open, create=True):
                self.fh.download(url, "foo")

            response.read.assert_called_with()
            _open.assert_called_once_with("foo", 'w')
            _open().write.assert_called_with("bar")

    @patch('charmhelpers.fetch.archiveurl.mkdir')
    @patch('charmhelpers.fetch.archiveurl.extract')
    def test_installs(self, _extract, _mkdir):
        self.fh.download = MagicMock()

        for url in self.valid_urls:
            filename = urlparse(url).path
            dest = os.path.join('foo', 'fetched', os.path.basename(filename))
            _extract.return_value = dest
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                where = self.fh.install(url)
            self.fh.download.assert_called_with(url, dest)
            _extract.assert_called_with(dest)
            self.assertEqual(where, dest)

        url = "http://www.example.com/archive.tar.gz"

        self.fh.download.side_effect = urllib2.URLError('fail')
        with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
            self.assertRaises(UnhandledSource, self.fh.install, url)

        self.fh.download.side_effect = OSError('fail')
        with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
            self.assertRaises(UnhandledSource, self.fh.install, url)

    @patch('charmhelpers.fetch.archiveurl.urlretrieve')
    @patch('charmhelpers.fetch.archiveurl.ArchiveUrlFetchHandler.validate_file')
    def test_download_and_validate(self, vfmock, urlmock):
        urlmock.return_value = ('/tmp/tmpebM9Hv', Mock())
        dlurl = 'http://example.com/foo.tgz'
        dlhash = '988881adc9fc3655077dc2d4d757d480b5ea0e11'
        self.fh.download_and_validate(dlurl, dlhash)
        vfmock.assert_called_with('/tmp/tmpebM9Hv', dlhash, 'sha1')

        self.assertRaises(ValueError, self.fh.download_and_validate, 'http://x.com/', 'garbage')
        self.assertRaises(ValueError, self.fh.download_and_validate, 'http://x.com', 'garbage', 'md5')

    @patch('builtins.open' if sys.version_info > (3,) else '__builtin__.open')
    def test_validate_file(self, mo):
        mo.return_value.__enter__ = lambda s: s
        mo.return_value.__exit__ = Mock()
        mo.return_value.read.return_value = "foobar"

        # hard coded validations of the phrase 'foobar'
        shav = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        mdfv = "d41d8cd98f00b204e9800998ecf8427e"

        self.fh.validate_file('/tmp/foo', shav)
        self.fh.validate_file('/tmp/foo', mdfv, vmethod='md5')

        self.assertRaises(ValueError, self.fh.validate_file, 'a', 'b', 'bloop')
        self.assertRaises(ValueError, self.fh.validate_file, '/tmp/foo', 'b')
