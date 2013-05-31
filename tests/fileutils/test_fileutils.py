import os
from testtools import TestCase
from mock import patch, MagicMock
import tarfile
import zipfile

from charmhelpers import fileutils

class ArchiveTestCase(TestCase):

    @patch('os.path.isfile')
    def test_gets_archive_handler_by_ext(self, _isfile):
        tar_archive_handler = fileutils.extract_tarfile
        zip_archive_handler = fileutils.extract_zipfile
        _isfile.return_value = False

        for ext in ('tar.gz', 'tgz', 'tar.bz2', 'tbz2', 'tbz'):
            handler = fileutils.get_archive_handler("somefile.{}".format(ext))
            self.assertEqual(handler, tar_archive_handler)

        for ext in ('zip', 'jar'):
            handler = fileutils.get_archive_handler("somefile.{}".format(ext))
            self.assertEqual(handler, zip_archive_handler)

    @patch('zipfile.is_zipfile')
    @patch('tarfile.is_tarfile')
    @patch('os.path.isfile')
    def test_gets_archive_hander_by_filetype(self, _isfile, _istarfile,
                                             _iszipfile):
        tar_archive_handler = fileutils.extract_tarfile
        zip_archive_handler = fileutils.extract_zipfile
        _isfile.return_value = True

        _istarfile.return_value = True
        _iszipfile.return_value = False
        handler = fileutils.get_archive_handler("foo")
        self.assertEqual(handler, tar_archive_handler)

        _istarfile.return_value = False
        _iszipfile.return_value = True
        handler = fileutils.get_archive_handler("foo")
        self.assertEqual(handler, zip_archive_handler)

    @patch('charmhelpers.core.hookenv.charm_dir')
    def test_gets_archive_dest_default(self, _charmdir):
        _charmdir.return_value = "foo"
        thedir = fileutils.archive_dest_default("baz")
        self.assertEqual(thedir, os.path.join("foo","archives","baz"))


    def test_extracts_archive(self):
        archive_class = MagicMock()
        archive_obj = MagicMock()
        archive_class.return_value = archive_obj
        archive_name = "foo"
        destdir = "bar"
        fileutils.extract_archive(archive_class, archive_name, destdir)
        archive_class.assert_called_with(archive_name)
        archive_obj.extract_all.assert_called_with(destdir)

    @patch('charmhelpers.fileutils.extract_archive')
    def test_extracts_tarfile(self, _extract):
        fileutils.extract_tarfile("foo", "bar")
        _extract.assert_called_with(tarfile.TarFile, "foo", "bar")

    @patch('charmhelpers.fileutils.extract_archive')
    def test_extracts_zipfile(self, _extract):
        fileutils.extract_zipfile("foo", "bar")
        _extract.assert_called_with(zipfile.ZipFile, "foo", "bar")


    @patch('charmhelpers.core.host.mkdir')
    @patch('charmhelpers.fileutils.get_archive_handler')
    @patch('charmhelpers.fileutils.archive_dest_default')
    def test_extracts(self, _defdest, _gethandler, _mkdir):
        archive_name = "foo"
        archive_handler = MagicMock()
        _gethandler.return_value = archive_handler

        fileutils.extract(archive_name, "bar")

        _gethandler.assert_called_with(archive_name)
        archive_handler.assert_called_with(archive_name, "bar")
        _defdest.assert_not_called()
        _mkdir.assert_called_with("bar")


    @patch('charmhelpers.core.host.mkdir')
    @patch('charmhelpers.fileutils.get_archive_handler')
    def test_unhandled_extract_raises_exc(self, _gethandler, _mkdir):
        archive_name = "foo"
        _gethandler.return_value = None

        self.assertRaises(fileutils.ArchiveError, fileutils.extract,
                          archive_name)

        _gethandler.assert_called_with(archive_name)
        _mkdir.assert_not_called()


    @patch('charmhelpers.core.host.mkdir')
    @patch('charmhelpers.fileutils.get_archive_handler')
    @patch('charmhelpers.fileutils.archive_dest_default')
    def test_extracts_default_dest(self, _defdest, _gethandler, _mkdir):
        archive_name = "foo"
        _defdest.return_value = "bar"
        archive_handler = MagicMock()
        _gethandler.return_value = archive_handler

        fileutils.extract(archive_name)

        archive_handler.assert_called_with(archive_name, "bar")
        _gethandler.assert_called_with(archive_name)
        _defdest.assert_called_with(archive_name)
        _mkdir.assert_called_with("bar")
