from testtools import TestCase
from mock import (
    patch,
    MagicMock,
    call,
)
from urlparse import urlparse
from charmhelpers import fetch


class AptRepoTest(TestCase):

    @patch('charmhelpers.fetch.check_call')
    def test_adds_repo(self, check_call_):
        repos = ["http://example.com", "cloud:example", "ppa:example"]
        for repo in repos:
            fetch.add_source(repo)
        check_call_.assert_has_calls([call('add-apt-repository', repo) for repo in repos])

    @patch('charmhelpers.fetch.check_call')
    def test_adds_repo_with_key(self, check_call_):
        repos = ["http://example.com", "cloud:example", "ppa:example"]
        keys = ["abcdef", "ghijkl", "mnopqr"]
        calls = []
        for i in range(len(repos)):
            fetch.add_source(repos[i], key=keys[i])
            calls.append(call('add-apt-repository', repos[i]))
            calls.append(call('apt-key', 'import', keys[i]))
        check_call_.assert_has_calls(calls)


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
