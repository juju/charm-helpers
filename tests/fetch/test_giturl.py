import os
from testtools import TestCase
from urlparse import urlparse
from mock import (
    MagicMock,
    patch,
)
from charmhelpers.fetch import (
    giturl,
    UnhandledSource,
)


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
            self.fh.clone(url, dest_path, branch)

            _clone_from.assert_called_with(url, dest_path)

        for url in self.invalid_urls:
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                self.assertRaises(UnhandledSource, self.fh.clone, url,
                                  dest_path,
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
