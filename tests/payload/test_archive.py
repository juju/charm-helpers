import os
from testtools import TestCase
from mock import (
    patch,
    MagicMock,
)
from charmhelpers.payload import archive
from tempfile import mkdtemp
from shutil import rmtree
import subprocess


class ArchiveTestCase(TestCase):

    def create_archive(self, format):
        workdir = mkdtemp()
        if format == "tar":
            workfile = "{}/foo.tar.gz".format(workdir)
            cmd = "tar czf {} hosts".format(workfile)
        elif format == "zip":
            workfile = "{}/foo.zip".format(workdir)
            cmd = "zip {} hosts".format(workfile)
        curdir = os.getcwd()
        os.chdir("/etc")
        subprocess.check_output(cmd, shell=True)
        os.chdir(curdir)
        self.addCleanup(rmtree, workdir)
        return (workfile, ["hosts"])

    @patch('os.path.isfile')
    def test_gets_archive_handler_by_ext(self, _isfile):
        tar_archive_handler = archive.extract_tarfile
        zip_archive_handler = archive.extract_zipfile
        _isfile.return_value = False

        for ext in ('tar', 'tar.gz', 'tgz', 'tar.bz2', 'tbz2', 'tbz'):
            handler = archive.get_archive_handler("somefile.{}".format(ext))
            msg = "handler for extension: {}".format(ext)
            self.assertEqual(handler, tar_archive_handler, msg)

        for ext in ('zip', 'jar'):
            handler = archive.get_archive_handler("somefile.{}".format(ext))
            msg = "handler for extension {}".format(ext)
            self.assertEqual(handler, zip_archive_handler, msg)

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
        self.assertEqual(thedir, os.path.join("foo", "archives", "baz"))

        thedir = archive.archive_dest_default("baz/qux")
        self.assertEqual(thedir, os.path.join("foo", "archives", "qux"))

    def test_extracts_tarfile(self):
        destdir = mkdtemp()
        self.addCleanup(rmtree, destdir)
        tar_file, contents = self.create_archive("tar")
        archive.extract_tarfile(tar_file, destdir)
        for path in [os.path.join(destdir, item) for item in contents]:
            self.assertTrue(os.path.exists(path))

    def test_extracts_zipfile(self):
        destdir = mkdtemp()
        self.addCleanup(rmtree, destdir)
        try:
            zip_file, contents = self.create_archive("zip")
        except subprocess.CalledProcessError as e:
            if e.returncode == 127:
                self.skip("Skipping - zip is not installed")
            else:
                raise
        archive.extract_zipfile(zip_file, destdir)
        for path in [os.path.join(destdir, item) for item in contents]:
            self.assertTrue(os.path.exists(path))

    @patch('charmhelpers.core.host.mkdir')
    @patch('charmhelpers.payload.archive.get_archive_handler')
    @patch('charmhelpers.payload.archive.archive_dest_default')
    def test_extracts(self, _defdest, _gethandler, _mkdir):
        archive_name = "foo"
        archive_handler = MagicMock()
        _gethandler.return_value = archive_handler

        dest = archive.extract(archive_name, "bar")

        _gethandler.assert_called_with(archive_name)
        archive_handler.assert_called_with(archive_name, "bar")
        _defdest.assert_not_called()
        _mkdir.assert_called_with("bar")
        self.assertEqual(dest, "bar")

    @patch('charmhelpers.core.host.mkdir')
    @patch('charmhelpers.payload.archive.get_archive_handler')
    def test_unhandled_extract_raises_exc(self, _gethandler, _mkdir):
        archive_name = "foo"
        _gethandler.return_value = None

        self.assertRaises(archive.ArchiveError, archive.extract,
                          archive_name)

        _gethandler.assert_called_with(archive_name)
        _mkdir.assert_not_called()

    @patch('charmhelpers.core.host.mkdir')
    @patch('charmhelpers.payload.archive.get_archive_handler')
    @patch('charmhelpers.payload.archive.archive_dest_default')
    def test_extracts_default_dest(self, _defdest, _gethandler, _mkdir):
        expected_dest = "bar"
        archive_name = "foo"
        _defdest.return_value = expected_dest
        handler = MagicMock()
        handler.return_value = expected_dest
        _gethandler.return_value = handler

        dest = archive.extract(archive_name)
        self.assertEqual(expected_dest, dest)
        handler.assert_called_with(archive_name, expected_dest)
