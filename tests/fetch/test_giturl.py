import os
import shutil
import subprocess
import tempfile
from testtools import TestCase
from mock import (
    MagicMock,
    patch,
)
from charmhelpers.core.host import chdir

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

    @patch.object(giturl, 'check_output')
    def test_clone(self, check_output):
        dest_path = "/destination/path"
        branch = "master"
        for url in self.valid_urls:
            self.fh.remote_branch = MagicMock()
            self.fh.load_plugins = MagicMock()
            self.fh.clone(url, dest_path, branch, None)

            check_output.assert_called_with(
                ['git', 'clone', url, dest_path, '--branch', branch], stderr=-2)

        for url in self.invalid_urls:
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                self.assertRaises(UnhandledSource, self.fh.clone, url,
                                  dest_path, None,
                                  branch)

    def test_clone_functional(self):
        src = None
        dst = None
        try:
            src = tempfile.mkdtemp()
            with chdir(src):
                subprocess.check_output(['git', 'init'])
                subprocess.check_output(['git', 'config', 'user.name', 'Joe'])
                subprocess.check_output(
                    ['git', 'config', 'user.email', 'joe@test.com'])
                subprocess.check_output(['touch', 'foo'])
                subprocess.check_output(['git', 'add', 'foo'])
                subprocess.check_output(['git', 'commit', '-m', 'test'])
            dst = tempfile.mkdtemp()
            os.rmdir(dst)
            self.fh.clone(src, dst)
            assert os.path.exists(os.path.join(dst, '.git'))
            self.fh.clone(src, dst)  # idempotent
            assert os.path.exists(os.path.join(dst, '.git'))
        finally:
            if src:
                shutil.rmtree(src, ignore_errors=True)
            if dst:
                shutil.rmtree(dst, ignore_errors=True)

    def test_installs(self):
        self.fh.clone = MagicMock()

        for url in self.valid_urls:
            branch_name = urlparse(url).path.strip("/").split("/")[-1]
            dest = os.path.join('foo', 'fetched',
                                os.path.basename(branch_name))
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                where = self.fh.install(url)
            self.assertEqual(where, dest)

    def test_installs_specified_dest(self):
        self.fh.clone = MagicMock()

        for url in self.valid_urls:
            branch_name = urlparse(url).path.strip("/").split("/")[-1]
            dest_repo = os.path.join('/tmp/git/',
                                     os.path.basename(branch_name))
            with patch.dict('os.environ', {'CHARM_DIR': 'foo'}):
                where = self.fh.install(url, dest="/tmp/git")
            self.assertEqual(where, dest_repo)
