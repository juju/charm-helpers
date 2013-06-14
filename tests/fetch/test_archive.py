import os
from testtools import TestCase
from urlparse import urlparse
import tarfile
import zipfile
from mock import (
    MagicMock,
    patch,
    mock_open,
)
from charmhelpers.fetch import archive


class UrlArchiveFetchHandlerTest(TestCase):

    def setUp(self):
        super(UrlArchiveFetchHandlerTest, self).setUp()
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
        self.fh = archive.UrlArchiveFetchHandler()

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
            with patch('charmhelpers.fetch.archive.open', _open, create=True):
                self.fh.download(url, "foo")

            response.read.assert_called_with()
            _open.assert_called_once_with("foo", 'w')
            _open().write.assert_called_with("bar")

    @patch('charmhelpers.fetch.archive.extract')
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


class ArchiveTestCase(TestCase):

    @patch('os.path.isfile')
    def test_gets_archive_handler_by_ext(self, _isfile):
        tar_archive_handler = archive.extract_tarfile
        zip_archive_handler = archive.extract_zipfile
        _isfile.return_value = False

        for ext in ('tar.gz', 'tgz', 'tar.bz2', 'tbz2', 'tbz'):
            handler = archive.get_archive_handler("somefile.{}".format(ext))
            self.assertEqual(handler, tar_archive_handler)

        for ext in ('zip', 'jar'):
            handler = archive.get_archive_handler("somefile.{}".format(ext))
            self.assertEqual(handler, zip_archive_handler)

    @patch('zipfile.is_zipfile')
    @patch('tarfile.is_tarfile')
    @patch('os.path.isfile')
    def test_gets_archive_hander_by_filetype(self, _isfile, _istarfile,
                                             _iszipfile):
        tar_archive_handler = archive.extract_tarfile
        zip_archive_handler = archive.extract_zipfile
        _isfile.return_value = True

        _istarfile.return_value = True
        _iszipfile.return_value = False
        handler = archive.get_archive_handler("foo")
        self.assertEqual(handler, tar_archive_handler)

        _istarfile.return_value = False
        _iszipfile.return_value = True
        handler = archive.get_archive_handler("foo")
        self.assertEqual(handler, zip_archive_handler)

    @patch('charmhelpers.core.hookenv.charm_dir')
    def test_gets_archive_dest_default(self, _charmdir):
        _charmdir.return_value = "foo"
        thedir = archive.archive_dest_default("baz")
        self.assertEqual(thedir, os.path.join("foo","archives","baz"))


    def test_extracts_archive(self):
        archive_class = MagicMock()
        archive_obj = MagicMock()
        archive_class.return_value = archive_obj
        archive_name = "foo"
        destdir = "bar"
        archive.extract_archive(archive_class, archive_name, destdir)
        archive_class.assert_called_with(archive_name)
        archive_obj.extract_all.assert_called_with(destdir)

    @patch('charmhelpers.fetch.archive.extract_archive')
    def test_extracts_tarfile(self, _extract):
        archive.extract_tarfile("foo", "bar")
        _extract.assert_called_with(tarfile.TarFile, "foo", "bar")

    @patch('charmhelpers.fetch.archive.extract_archive')
    def test_extracts_zipfile(self, _extract):
        archive.extract_zipfile("foo", "bar")
        _extract.assert_called_with(zipfile.ZipFile, "foo", "bar")


    @patch('charmhelpers.core.host.mkdir')
    @patch('charmhelpers.fetch.archive.get_archive_handler')
    @patch('charmhelpers.fetch.archive.archive_dest_default')
    def test_extracts(self, _defdest, _gethandler, _mkdir):
        archive_name = "foo"
        archive_handler = MagicMock()
        _gethandler.return_value = archive_handler

        archive.extract(archive_name, "bar")

        _gethandler.assert_called_with(archive_name)
        archive_handler.assert_called_with(archive_name, "bar")
        _defdest.assert_not_called()
        _mkdir.assert_called_with("bar")


    @patch('charmhelpers.core.host.mkdir')
    @patch('charmhelpers.fetch.archive.get_archive_handler')
    def test_unhandled_extract_raises_exc(self, _gethandler, _mkdir):
        archive_name = "foo"
        _gethandler.return_value = None

        self.assertRaises(archive.ArchiveError, archive.extract,
                          archive_name)

        _gethandler.assert_called_with(archive_name)
        _mkdir.assert_not_called()


    @patch('charmhelpers.core.host.mkdir')
    @patch('charmhelpers.fetch.archive.get_archive_handler')
    @patch('charmhelpers.fetch.archive.archive_dest_default')
    def test_extracts_default_dest(self, _defdest, _gethandler, _mkdir):
        archive_name = "foo"
        _defdest.return_value = "bar"
        archive_handler = MagicMock()
        _gethandler.return_value = archive_handler

        archive.extract(archive_name)

        archive_handler.assert_called_with(archive_name, "bar")
        _gethandler.assert_called_with(archive_name)
        _defdest.assert_called_with(archive_name)
        _mkdir.assert_called_with("bar")
