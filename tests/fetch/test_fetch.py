from contextlib import contextmanager
from testtools import TestCase
from mock import (
    patch,
    MagicMock,
    call,
)
from urlparse import urlparse
from charmhelpers import fetch
import yaml


@contextmanager
def patch_open():
    '''Patch open() to allow mocking both open() itself and the file that is
    yielded.

    Yields the mock for "open" and "file", respectively.'''
    mock_open = MagicMock(spec=open)
    mock_file = MagicMock(spec=file)

    @contextmanager
    def stub_open(*args, **kwargs):
        mock_open(*args, **kwargs)
        yield mock_file

    with patch('__builtin__.open', stub_open):
        yield mock_open, mock_file


class FetchTest(TestCase):
    @patch('subprocess.check_call')
    def test_add_source_ppa(self, check_call):
        source = "ppa:test-ppa"
        fetch.add_source(source=source)
        check_call.assert_called_with(['add-apt-repository',
                                       source])

    @patch('subprocess.check_call')
    def test_add_source_http(self, check_call):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        fetch.add_source(source=source)
        check_call.assert_called_with(['add-apt-repository',
                                       source])

    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    def test_add_source_cloud(self, apt_install, filter_pkg):
        source = "cloud:havana-updates"
        result = '''# Ubuntu Cloud Archive
deb http://ubuntu-cloud.archive.canonical.com/ubuntu havana-updates main
'''
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('subprocess.check_call')
    def test_add_source_http_and_key(self, check_call):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key = "akey"
        fetch.add_source(source=source, key=key)
        check_call.assert_has_calls([
            call(['add-apt-repository', source]),
            call(['apt-key', 'import', key])
        ])

    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_single_source(self, add_source, config):
        config.side_effect = ['source', 'key']
        fetch.configure_sources()
        add_source.assert_called_with('source', 'key')

    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_multiple_sources(self, add_source, config):
        sources = ["sourcea", "sourceb"]
        keys = ["keya", None]
        config.side_effect = [
            yaml.dump(sources),
            yaml.dump(keys)
        ]
        fetch.configure_sources()
        add_source.assert_has_calls([
            call('sourcea', 'keya'),
            call('sourceb', None)
        ])

    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_missing_keys(self, add_source, config):
        sources = ["sourcea", "sourceb"]
        keys = ["keya"]  # Second key is missing
        config.side_effect = [
            yaml.dump(sources),
            yaml.dump(keys)
        ]
        self.assertRaises(fetch.SourceConfigError, fetch.configure_sources)

    @patch.object(fetch, 'apt_update')
    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_apt_update_called(self, add_source, config,
                                                 apt_update):
        config.side_effect = ['source', 'key']
        fetch.configure_sources(update=True)
        add_source.assert_called_with('source', 'key')
        apt_update.assertCalled()


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


class PluginTest(TestCase):
    @patch('charmhelpers.fetch.importlib.import_module')
    def test_imports_plugins(self, import_):
        fetch_handlers = ['a.foo', 'b.foo', 'c.foo']
        module = MagicMock()
        import_.return_value = module
        plugins = fetch.plugins(fetch_handlers)

        self.assertEqual(len(fetch_handlers), len(plugins))
        module.foo.assert_has_calls(([call()] * len(fetch_handlers)))

    @patch('charmhelpers.fetch.importlib.import_module')
    def test_imports_plugins_default(self, import_):
        module = MagicMock()
        import_.return_value = module
        plugins = fetch.plugins()

        self.assertEqual(len(fetch.FETCH_HANDLERS), len(plugins))
        for handler in fetch.FETCH_HANDLERS:
            classname = handler.rsplit('.', 1)[-1]
            getattr(module, classname).assert_called_with()

    @patch('charmhelpers.fetch.log')
    @patch('charmhelpers.fetch.importlib.import_module')
    def test_skips_and_logs_missing_plugins(self, import_, log_):
        fetch_handlers = ['a.foo', 'b.foo', 'c.foo']
        import_.side_effect = (ImportError, AttributeError, MagicMock())
        plugins = fetch.plugins(fetch_handlers)

        self.assertEqual(1, len(plugins))
        self.assertEqual(2, log_.call_count)

    @patch('charmhelpers.fetch.log')
    def test_plugins_are_valid(self, log_):
        plugins = fetch.plugins()
        self.assertEqual(len(fetch.FETCH_HANDLERS), len(plugins))


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
