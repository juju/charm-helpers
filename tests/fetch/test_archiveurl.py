import os
from testtools import TestCase
from urlparse import urlparse
from mock import (
    MagicMock,
    patch,
    mock_open,
)
from charmhelpers.fetch import archiveurl


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

    @patch('charmhelpers.fetch.archiveurl.extract')
    def test_installs(self, _extract):
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
