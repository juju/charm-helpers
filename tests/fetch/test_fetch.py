import os
from testtools import TestCase
from unittest import skip
from mock import (
    patch,
    MagicMock,
    mock_open
)
from urlparse import urlparse

from charmhelpers import fetch


class InstallTest(TestCase):

    def setUp(self):
        super(InstallTest, self).setUp()
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

    @patch('charmhelpers.fetch.plugins')
    def test_installs_remote(self, _plugins):
        h1 = MagicMock(name="h1")
        h1.can_handle.return_value = "Nope"

        h2 = MagicMock(name="h2")
        h2.can_handle.return_value = True
        h2.install.side_effect = fetch.UnhandledSource()

        h3 = MagicMock(name="h3")
        h3.can_handle.return_value = True
        h3.install.return_value = "foo"

        _plugins.return_value = [h1, h2, h3]
        for url in self.valid_urls:
            result = fetch.install_remote(url)

            h1.can_handle.assert_called_with(url)
            h2.can_handle.assert_called_with(url)
            h3.can_handle.assert_called_with(url)

            h1.install.assert_not_called()
            h2.install.assert_called_with(url)
            h3.install.assert_called_with(url)

            self.assertEqual(result, "foo")

    @patch('charmhelpers.fetch.install_remote')
    @patch('charmhelpers.fetch.config')
    def test_installs_from_config(self, _config, _instrem):
        for url in self.valid_urls:
            _config.return_value = {"foo": url}
            fetch.install_from_config("foo")
            _instrem.assert_called_with(url)


class BaseFetchHandlerTest(TestCase):

    def setUp(self):
        super(BaseFetchHandlerTest, self).setUp()
        self.test_urls = (
            "http://example.com/foo?bar=baz&x=y#blarg",
            "https://example.com/foo",
            "ftp://example.com/foo",
            "file://example.com/foo",
            "git://github.com/foo/bar",
            "bzr+ssh://bazaar.launchpad.net/foo/bar",
            "bzr+http://bazaar.launchpad.net/foo/bar",
            "garbage",
            )
        self.fh = fetch.BaseFetchHandler()

    def test_handles_nothing(self):
        for url in self.test_urls:
            self.assertNotEqual(self.fh.can_handle(url), True)

    def test_install_throws_unhandled(self):
        for url in self.test_urls:
            self.assertRaises(fetch.UnhandledSource, self.fh.install, url)

    def test_parses_urls(self):
        sample_url = "http://example.com/foo?bar=baz&x=y#blarg"
        p = self.fh.parse_url(sample_url)
        self.assertEqual(p, urlparse(sample_url))

    def test_returns_baseurl(self):
        sample_url = "http://example.com/foo?bar=baz&x=y#blarg"
        expected_url = "http://example.com/foo"
        u = self.fh.base_url(sample_url)
        self.assertEqual(u, expected_url)


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
        self.fh = fetch.UrlArchiveFetchHandler()

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
            with patch('charmhelpers.fetch.open', _open, create=True):
                self.fh.download(url, "foo")

            response.read.assert_called_with()
            _open.assert_called_once_with("foo", 'w')
            _open().write.assert_called_with("bar")

    @patch('charmhelpers.fileutils.extract')
    def test_installs(self, _extract):
        self.fh.download = MagicMock()

        for url in self.valid_urls:
            filename = urlparse(url).path
            dest = os.path.join('foo', 'fetched', os.path.basename(filename))
            _extract.return_value = dest
            with patch.dict('os.environ', { 'CHARM_DIR': 'foo' }):
                where = self.fh.install(url)
            self.fh.download.assert_called_with(url, dest)
            _extract.assert_called_with(dest)
            self.assertEqual(where, dest)


class FetchPluginTest(TestCase):

    @patch('charmhelpers.fetch.log')
    @patch('importlib.import_module')
    @patch('os.listdir')
    @patch('os.path.exists')
    def test_load_skips_unimplemented(self, _exists, _listdir, _import, _log):
        _exists.return_value = True
        _listdir.return_value = ['foo']
        not_implemented_mock = MagicMock(spec=[])
        _import.return_value = not_implemented_mock

        plugin_list = fetch.plugins()
        self.assertEqual(len(plugin_list), 1)
        self.assertIsInstance(plugin_list[-1], fetch.UrlArchiveFetchHandler)

    @patch('charmhelpers.fetch.log')
    @patch('importlib.import_module')
    @patch('os.listdir')
    @patch('os.path.exists')
    def test_loads(self, _exists, _listdir, _import, _log):
        _exists.return_value = True
        _listdir.return_value = ['foo','bar','baz']
        _import.return_value = MagicMock()

        plugin_list = fetch.plugins()
        self.assertEqual(len(plugin_list), 4)
        for plugin in plugin_list[0:3]:
            self.assertIsInstance(plugin, MagicMock)
        self.assertIsInstance(plugin_list[-1], fetch.UrlArchiveFetchHandler)
