import os
from testtools import TestCase
from mock import (
    MagicMock,
    patch,
)
import unittest

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


@unittest.skipIf(six.PY3, 'bzr does not support Python 3')
class BzrUrlFetchHandlerTest(TestCase):

    def setUp(self):
        super(BzrUrlFetchHandlerTest, self).setUp()
        if six.PY3:
            return
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

    @unittest.skipIf(six.PY3, 'bzr does not support Python 3')
    def test_handles_bzr_urls(self):
        for url in self.valid_urls:
            result = self.fh.can_handle(url)
            self.assertEqual(result, True, url)
        for url in self.invalid_urls:
            result = self.fh.can_handle(url)
            self.assertNotEqual(result, True, url)

    @unittest.skipIf(six.PY3, 'bzr does not support Python 3')
    @patch('bzrlib.workingtree.WorkingTree.open')
    @patch('bzrlib.bzrdir.BzrDir.create_branch_convenience')
    @patch('bzrlib.branch.Branch.open')
    def test_branch(self, _open, _bzrdir, _tree_open):
        dest_path = "/destination/path"
        for url in self.valid_urls:
            self.fh.remote_branch = MagicMock()
            self.fh.load_plugins = MagicMock()
            self.fh.branch(url, dest_path)

            _open.assert_called_with(url)
            _bzrdir.assert_called_with(dest_path)
            _tree_open.assert_called_with(dest_path)

        for url in self.invalid_urls:
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                self.assertRaises(UnhandledSource, self.fh.branch, url, dest_path)

    @unittest.skipIf(six.PY3, 'bzr does not support Python 3')
    @patch('charmhelpers.fetch.bzrurl.mkdir')
    def test_installs(self, _mkdir):
        self.fh.branch = MagicMock()

        for url in self.valid_urls:
            branch_name = urlparse(url).path.strip("/").split("/")[-1]
            dest = os.path.join('foo', 'fetched', os.path.basename(branch_name))
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                where = self.fh.install(url)
            self.assertEqual(where, dest)
            _mkdir.assert_called_with(where, perms=0o755)
