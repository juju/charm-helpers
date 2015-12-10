import os
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
        giturl,
        UnhandledSource,
    )
except ImportError:
    giturl = None
    UnhandledSource = None


class GitUrlFetchHandlerTest(TestCase):
    def setUp(self):
        super(GitUrlFetchHandlerTest, self).setUp()
        self.valid_urls = (
            "http://example.com/git-branch",
            "https://example.com/git-branch",
            "git://example.com/git-branch",
        )
        self.invalid_urls = (
            "file://example.com/foo.tar.bz2",
            "abc:example",
            "garbage",
        )
        self.fh = giturl.GitUrlFetchHandler()

    def test_handles_git_urls(self):
        for url in self.valid_urls:
            result = self.fh.can_handle(url)
            self.assertEqual(result, True, url)
        for url in self.invalid_urls:
            result = self.fh.can_handle(url)
            self.assertNotEqual(result, True, url)

    @patch('git.Repo.clone_from')
    def test_branch(self, _clone_from):
        dest_path = "/destination/path"
        branch = "master"
        for url in self.valid_urls:
            self.fh.remote_branch = MagicMock()
            self.fh.load_plugins = MagicMock()
            self.fh.clone(url, dest_path, branch, None)

            _clone_from.assert_called_with(url, dest_path, branch=branch)

        for url in self.invalid_urls:
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                self.assertRaises(UnhandledSource, self.fh.clone, url,
                                  dest_path, None,
                                  branch)

    @patch('charmhelpers.fetch.giturl.mkdir')
    def test_installs(self, _mkdir):
        self.fh.clone = MagicMock()

        for url in self.valid_urls:
            branch_name = urlparse(url).path.strip("/").split("/")[-1]
            dest = os.path.join('foo', 'fetched',
                                os.path.basename(branch_name))
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                where = self.fh.install(url)
            self.assertEqual(where, dest)
            _mkdir.assert_called_with(where, perms=0o755)

    @patch('charmhelpers.fetch.giturl.mkdir')
    def test_installs_specified_dest(self, _mkdir):
        self.fh.clone = MagicMock()

        for url in self.valid_urls:
            branch_name = urlparse(url).path.strip("/").split("/")[-1]
            dest_repo = os.path.join('/tmp/git/',
                                     os.path.basename(branch_name))
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                where = self.fh.install(url, dest="/tmp/git")
            self.assertEqual(where, dest_repo)
