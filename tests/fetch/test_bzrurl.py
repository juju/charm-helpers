import os
import shutil
import subprocess
import tempfile
from testtools import TestCase
from mock import (
    MagicMock,
    patch,
)

import six
if six.PY3:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse

try:
    from charmhelpers.fetch import (
        bzrurl,
        UnhandledSource,
    )
except ImportError:
    bzrurl = None
    UnhandledSource = None


class BzrUrlFetchHandlerTest(TestCase):

    def setUp(self):
        super(BzrUrlFetchHandlerTest, self).setUp()
        self.valid_urls = (
            "bzr+ssh://example.com/branch-name",
            "bzr+ssh://example.com/branch-name/",
            "lp:lp-branch-name",
            "lp:example/lp-branch-name",
        )
        self.invalid_urls = (
            "http://example.com/foo.tar.gz",
            "http://example.com/foo.tgz",
            "http://example.com/foo.tar.bz2",
            "http://example.com/foo.tbz2",
            "http://example.com/foo.zip",
            "http://example.com/foo.zip?bar=baz&x=y#whee",
            "ftp://example.com/foo.tar.gz",
            "https://example.com/foo.tgz",
            "file://example.com/foo.tar.bz2",
            "git://example.com/foo.tar.gz",
            "http://example.com/foo",
            "http://example.com/foobar=baz&x=y#tar.gz",
            "http://example.com/foobar?h=baz.zip",
            "abc:example",
            "file//example.com/foo.tar.bz2",
            "garbage",
        )
        self.fh = bzrurl.BzrUrlFetchHandler()

    def test_handles_bzr_urls(self):
        for url in self.valid_urls:
            result = self.fh.can_handle(url)
            self.assertEqual(result, True, url)
        for url in self.invalid_urls:
            result = self.fh.can_handle(url)
            self.assertNotEqual(result, True, url)

    @patch('charmhelpers.fetch.bzrurl.check_output')
    def test_branch(self, check_output):
        dest_path = "/destination/path"
        for url in self.valid_urls:
            self.fh.remote_branch = MagicMock()
            self.fh.load_plugins = MagicMock()
            self.fh.branch(url, dest_path)

            check_output.assert_called_with(['bzr', 'branch', url, dest_path], stderr=-2)

        for url in self.invalid_urls:
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                self.assertRaises(UnhandledSource, self.fh.branch,
                                  url, dest_path)

    @patch('charmhelpers.fetch.bzrurl.check_output')
    def test_branch_revno(self, check_output):
        dest_path = "/destination/path"
        for url in self.valid_urls:
            self.fh.remote_branch = MagicMock()
            self.fh.load_plugins = MagicMock()
            self.fh.branch(url, dest_path, revno=42)

            check_output.assert_called_with(['bzr', 'branch', '-r', '42',
                                             url, dest_path], stderr=-2)

        for url in self.invalid_urls:
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                self.assertRaises(UnhandledSource, self.fh.branch, url,
                                  dest_path)

    def test_branch_functional(self):
        src = None
        dst = None
        try:
            src = tempfile.mkdtemp()
            subprocess.check_output(['bzr', 'init', src], stderr=subprocess.STDOUT)
            dst = tempfile.mkdtemp()
            os.rmdir(dst)
            self.fh.branch(src, dst)
            assert os.path.exists(os.path.join(dst, '.bzr'))
            self.fh.branch(src, dst)  # idempotent
            assert os.path.exists(os.path.join(dst, '.bzr'))
        finally:
            if src:
                shutil.rmtree(src, ignore_errors=True)
            if dst:
                shutil.rmtree(dst, ignore_errors=True)

    def test_installs(self):
        self.fh.branch = MagicMock()

        for url in self.valid_urls:
            branch_name = urlparse(url).path.strip("/").split("/")[-1]
            dest = os.path.join('foo', 'fetched')
            dest_dir = os.path.join(dest, os.path.basename(branch_name))
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                where = self.fh.install(url)
            self.assertEqual(where, dest_dir)

    @patch('charmhelpers.fetch.bzrurl.mkdir')
    def test_installs_dir(self, _mkdir):
        self.fh.branch = MagicMock()

        for url in self.valid_urls:
            branch_name = urlparse(url).path.strip("/").split("/")[-1]
            dest = os.path.join('opt', 'f')
            dest_dir = os.path.join(dest, os.path.basename(branch_name))
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                where = self.fh.install(url, dest)
            self.assertEqual(where, dest_dir)
            _mkdir.assert_called_with(dest, perms=0o755)
