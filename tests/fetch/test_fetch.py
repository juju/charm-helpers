import subprocess
import six
import os
import yaml
import imp
import tempfile

from charmhelpers import osplatform
from tests.helpers import patch_open
from testtools import TestCase
from mock import (
    patch,
    MagicMock,
    call,
    sentinel,
)
from charmhelpers import fetch
from six.moves import StringIO
if six.PY3:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse


FAKE_APT_CACHE = {
    # an installed package
    'vim': {
        'current_ver': '2:7.3.547-6ubuntu5'
    },
    # a uninstalled installation candidate
    'emacs': {
    }
}


def fake_apt_cache(in_memory=True, progress=None):
    def _get(package):
        pkg = MagicMock()
        if package not in FAKE_APT_CACHE:
            raise KeyError
        pkg.name = package
        if 'current_ver' in FAKE_APT_CACHE[package]:
            pkg.current_ver.ver_str = FAKE_APT_CACHE[package]['current_ver']
        else:
            pkg.current_ver = None
        return pkg
    cache = MagicMock()
    cache.__getitem__.side_effect = _get
    return cache


def getenv(update=None):
    # return a copy of os.environ with update applied.
    # this was necessary because some modules modify os.environment directly
    copy = os.environ.copy()
    if update is not None:
        copy.update(update)
    return copy


class FetchTest(TestCase):

    @patch("charmhelpers.fetch.ubuntu.log")
    @patch.object(osplatform, 'get_platform')
    @patch('apt_pkg.Cache')
    def test_filter_packages_missing_ubuntu(self, cache, platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        cache.side_effect = fake_apt_cache
        result = fetch.filter_installed_packages(['vim', 'emacs'])
        self.assertEquals(result, ['emacs'])

    @patch("charmhelpers.fetch.centos.log")
    @patch('yum.YumBase.doPackageLists')
    @patch.object(osplatform, 'get_platform')
    def test_filter_packages_missing_centos(self, platform, yumBase, log):
        platform.return_value = 'centos'
        imp.reload(fetch)

        class MockPackage:
            def __init__(self, name):
                self.base_package_name = name

        yum_dict = {
            'installed': {
                MockPackage('vim')
            },
            'available': {
                MockPackage('vim')
            }
        }
        import yum
        yum.YumBase.return_value.doPackageLists.return_value = yum_dict
        result = fetch.filter_installed_packages(['vim', 'emacs'])
        self.assertEquals(result, ['emacs'])

    @patch("charmhelpers.fetch.ubuntu.log")
    @patch.object(osplatform, 'get_platform')
    @patch('apt_pkg.Cache')
    def test_filter_packages_none_missing_ubuntu(self, cache, platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        cache.side_effect = fake_apt_cache
        result = fetch.filter_installed_packages(['vim'])
        self.assertEquals(result, [])

    @patch("charmhelpers.fetch.centos.log")
    @patch.object(osplatform, 'get_platform')
    def test_filter_packages_none_missing_centos(self, platform, log):
        platform.return_value = 'centos'
        imp.reload(fetch)

        class MockPackage:
            def __init__(self, name):
                self.base_package_name = name

        yum_dict = {
            'installed': {
                MockPackage('vim')
            },
            'available': {
                MockPackage('vim')
            }
        }
        import yum
        yum.yumBase.return_value.doPackageLists.return_value = yum_dict
        result = fetch.filter_installed_packages(['vim'])
        self.assertEquals(result, [])

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('apt_pkg.Cache')
    def test_filter_packages_not_available_ubuntu(self, cache, log, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        cache.side_effect = fake_apt_cache
        result = fetch.filter_installed_packages(['vim', 'joe'])
        self.assertEquals(result, ['joe'])
        log.assert_called_with('Package joe has no installation candidate.',
                               level='WARNING')

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.centos.log')
    @patch('yum.YumBase.doPackageLists')
    def test_filter_packages_not_available_centos(self, yumBase,
                                                  log, platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        class MockPackage:
            def __init__(self, name):
                self.base_package_name = name

        yum_dict = {
            'installed': {
                MockPackage('vim')
            }
        }
        import yum
        yum.YumBase.return_value.doPackageLists.return_value = yum_dict

        result = fetch.filter_installed_packages(['vim', 'joe'])
        self.assertEquals(result, ['joe'])

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_add_source_none_ubuntu(self, log, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        fetch.add_source(source=None)
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.centos.log')
    def test_add_source_none_centos(self, log, platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        fetch.add_source(source=None)
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_ppa(self, check_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "ppa:test-ppa"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_http_ubuntu(self, check_call, platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source])

    @patch('charmhelpers.fetch.centos.log')
    @patch.object(osplatform, 'get_platform')
    @patch('os.listdir')
    def test_add_source_http_centos(self, listdir, platform, log):
        platform.return_value = 'centos'
        imp.reload(fetch)

        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            listdir.assert_called_with('/etc/yum.repos.d/')
            mock_file.write.assert_has_calls([
                call("[archive.ubuntu.com_ubuntu raring-backports main]\n"),
                call("name=archive.ubuntu.com/ubuntu raring-backports main\n"),
                call("baseurl=http://archive.ubuntu.com/ubuntu raring"
                     "-backports main\n\n")])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_https(self, check_call, platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "https://example.com"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_deb(self, check_call, platform, log):
        """add-apt-repository behaves differently when using the deb prefix.

        $ add-apt-repository --yes "http://special.example.com/ubuntu
        precise-special main"
        $ grep special /etc/apt/sources.list
        deb http://special.example.com/ubuntu precise precise-special main
        deb-src http://special.example.com/ubuntu precise precise-special main

        $ add-apt-repository --yes "deb http://special.example.com/ubuntu
        precise-special main"
        $ grep special /etc/apt/sources.list
        deb http://special.example.com/ubuntu precise precise-special main
        deb-src http://special.example.com/ubuntu precise precise-special main
        deb http://special.example.com/ubuntu precise-special main
        deb-src http://special.example.com/ubuntu precise-special main
        """
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "deb http://archive.ubuntu.com/ubuntu raring-backports main"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source])

    @patch.object(osplatform, 'get_platform')
    @patch.object(fetch.ubuntu, 'filter_installed_packages')
    @patch.object(fetch.ubuntu, 'install')
    def test_add_source_cloud_invalid_pocket(self, install,
                                             filter_pkg, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "cloud:havana-updates"
        self.assertRaises(fetch.ubuntu.SourceConfigError,
                          fetch.add_source, source)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch.object(fetch.ubuntu, 'filter_installed_packages')
    @patch.object(fetch.ubuntu, 'install')
    def test_add_source_cloud_pocket_style(self, install, filter_pkg,
                                           platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "cloud:precise-updates/havana"
        result = ('# Ubuntu Cloud Archive\n'
                  'deb http://ubuntu-cloud.archive.canonical.com/ubuntu'
                  ' precise-updates/havana main\n')

        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch.object(fetch.ubuntu, 'filter_installed_packages')
    @patch.object(fetch.ubuntu, 'install')
    def test_add_source_cloud_os_style(self, install, filter_pkg,
                                       platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "cloud:precise-havana"
        result = ('# Ubuntu Cloud Archive\n'
                  'deb http://ubuntu-cloud.archive.canonical.com/ubuntu'
                  ' precise-updates/havana main\n')
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch.object(fetch.ubuntu, 'filter_installed_packages')
    @patch.object(fetch.ubuntu, 'install')
    def test_add_source_cloud_distroless_style(self, install, filter_pkg,
                                               platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "cloud:havana"
        result = ('# Ubuntu Cloud Archive\n'
                  'deb http://ubuntu-cloud.archive.canonical.com/ubuntu'
                  ' precise-updates/havana main\n')
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch.object(fetch.ubuntu, 'lsb_release')
    def test_add_source_proposed(self, lsb_release, platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "proposed"
        result = ('# Proposed\n'
                  'deb http://archive.ubuntu.com/ubuntu precise-proposed'
                  ' main universe multiverse restricted\n')
        lsb_release.return_value = {'DISTRIB_CODENAME': 'precise'}
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_id_ubuntu(self, check_call,
                                               platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key_id = "akey"
        fetch.add_source(source=source, key=key_id)
        check_call.assert_has_calls([
            call(['add-apt-repository', '--yes', source]),
            call(['apt-key', 'adv', '--keyserver',
                  'hkp://keyserver.ubuntu.com:80', '--recv', key_id])
        ])

    @patch('charmhelpers.fetch.centos.log')
    @patch('os.listdir')
    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_id_centos(self, check_call,
                                               platform, listdir, log):
        platform.return_value = 'centos'
        imp.reload(fetch)

        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key_id = "akey"
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source, key=key_id)
            listdir.assert_called_with('/etc/yum.repos.d/')
            mock_file.write.assert_has_calls([
                call("[archive.ubuntu.com_ubuntu raring-backports main]\n"),
                call("name=archive.ubuntu.com/ubuntu raring-backports main\n"),
                call("baseurl=http://archive.ubuntu.com/ubuntu raring"
                     "-backports main\n\n")])
        check_call.assert_called_with(['rpm', '--import', key_id])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_https_and_key_id_ubuntu(self, check_call,
                                                platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "https://USER:PASS@private-ppa.launchpad.net/project/awesome"
        key_id = "GPGPGP"
        fetch.add_source(source=source, key=key_id)
        check_call.assert_has_calls([
            call(['add-apt-repository', '--yes', source]),
            call(['apt-key', 'adv', '--keyserver',
                  'hkp://keyserver.ubuntu.com:80', '--recv', key_id])
        ])

    @patch('charmhelpers.fetch.centos.log')
    @patch('os.listdir')
    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_https_and_key_id_centos(self, check_call,
                                                platform, listdir, log):
        platform.return_value = 'centos'
        imp.reload(fetch)

        source = "https://USER:PASS@private-ppa.launchpad.net/project/awesome"
        key_id = "GPGPGP"
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source, key=key_id)
            listdir.assert_called_with('/etc/yum.repos.d/')
            mock_file.write.assert_has_calls([
                call("[_USER:PASS@private-ppa.launchpad"
                     ".net_project_awesome]\n"),
                call("name=/USER:PASS@private-ppa.launchpad.net"
                     "/project/awesome\n"),
                call("baseurl=https://USER:PASS@private-ppa.launchpad.net"
                     "/project/awesome\n\n")])
        check_call.assert_called_with(['rpm', '--import', key_id])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_ubuntu(self, check_call, platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key = '''
            -----BEGIN PGP PUBLIC KEY BLOCK-----
            [...]
            -----END PGP PUBLIC KEY BLOCK-----
            '''

        received_args = []
        received_key = StringIO()

        def _check_call(arg, stdin=None):
            '''side_effect to store the stdin passed to check_call process.'''
            if stdin is not None:
                received_args.extend(arg)
                received_key.write(stdin.read())

        with patch('subprocess.check_call',
                   side_effect=_check_call) as check_call:
            fetch.add_source(source=source, key=key)
            check_call.assert_any_call(['add-apt-repository', '--yes', source])
            self.assertEqual(['apt-key', 'add', '-'], received_args)
            self.assertEqual(key, received_key.getvalue())

    @patch('charmhelpers.fetch.centos.log')
    @patch.object(tempfile, 'NamedTemporaryFile')
    @patch('os.listdir')
    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_centos(self, check_call, platform,
                                            listdir, temp_file, log):
        platform.return_value = 'centos'
        imp.reload(fetch)

        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key = '''
            -----BEGIN PGP PUBLIC KEY BLOCK-----
            [...]
            -----END PGP PUBLIC KEY BLOCK-----
            '''
        temp_file.return_value.__enter__.return_value = key
        temp_file.return_value.__exit__.return_value = key

        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source, key=key)
            listdir.assert_called_with('/etc/yum.repos.d/')
            self.assertTrue(log.called)
        check_call.assert_called_with(['rpm', '--import', key])

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_add_unparsable_source(self, log_, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "propsed"  # Minor typo
        fetch.add_source(source=source)
        self.assertEqual(1, log_.call_count)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(osplatform, 'get_platform')
    def test_add_distro_source(self, platform, log):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        source = "distro"
        # distro is a noop but test validate no exception is thrown
        fetch.add_source(source=source)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_single_source(self, add_source, config, log):
        config.side_effect = ['source', 'key']
        fetch.configure_sources()
        add_source.assert_called_with('source', 'key')

    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_null_source(self, add_source, config):
        config.side_effect = [None, None]
        fetch.configure_sources()
        self.assertEqual(add_source.call_count, 0)

    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_empty_source(self, add_source, config):
        config.side_effect = ['', '']
        fetch.configure_sources()
        self.assertEqual(add_source.call_count, 0)

    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_single_source_no_key(self, add_source, config):
        config.side_effect = ['source', None]
        fetch.configure_sources()
        add_source.assert_called_with('source', None)

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

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.ubuntu.update')
    @patch.object(fetch, 'config')
    @patch.object(fetch, 'add_source')
    def test_configure_sources_update_called_ubuntu(self, add_source, config,
                                                    update, platform):
        config.side_effect = ['source', 'key']
        fetch.configure_sources(update=True)
        add_source.assert_called_with('source', 'key')
        self.assertTrue(update.called)


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
            "bzr+ssh://example.com/branch-name",
            "bzr+ssh://example.com/branch-name/",
            "lp:branch-name",
            "lp:example/branch-name",
        )
        self.invalid_urls = (
            "git://example.com/foo.tar.gz",
            "http://example.com/foo",
            "http://example.com/foobar=baz&x=y#tar.gz",
            "http://example.com/foobar?h=baz.zip",
            "abc:example",
            "file//example.com/foo.tar.bz2",
            "garbage",
        )

    @patch('charmhelpers.fetch.log')
    @patch('charmhelpers.fetch.plugins')
    def test_installs_remote(self, _plugins, _log):
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

        fetch.install_remote('url', extra_arg=True)
        h2.install.assert_called_with('url', extra_arg=True)

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
        import_.side_effect = (NotImplementedError, NotImplementedError,
                               MagicMock())
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


class AptTests(TestCase):

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_apt_upgrade_non_fatal(self, log, mock_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        options = ['--foo', '--bar']
        fetch.apt_upgrade(options)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'upgrade'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_apt_upgrade_fatal(self, log, mock_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        options = ['--foo', '--bar']
        fetch.apt_upgrade(options, fatal=True)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'upgrade'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_apt_dist_upgrade_fatal(self, log, mock_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        options = ['--foo', '--bar']
        fetch.apt_upgrade(options, fatal=True, dist=True)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'dist-upgrade'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages(self, log, mock_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.apt_install(packages, options)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'install', 'foo', 'bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages_without_options(self, log, mock_call,
                                                   platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = ['foo', 'bar']

        fetch.apt_install(packages)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--option=Dpkg::Options::=--force-confold',
             'install', 'foo', 'bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages_as_string(self, log, mock_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = 'foo bar'
        options = ['--foo', '--bar']

        fetch.apt_install(packages, options)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'install', 'foo bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages_with_possible_errors(self, log,
                                                        check_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.apt_install(packages, options, fatal=True)

        check_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'install', 'foo', 'bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_as_string_fatal(self, log, mock_call,
                                                 platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = 'irrelevant names'
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_fatal(self, log, mock_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = ['irrelevant', 'names']
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_as_string_nofatal(self, log, mock_call,
                                                   platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = 'foo bar'

        fetch.apt_purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-get', '--assume-yes', 'purge', 'foo bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_nofatal(self, log, mock_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = ['foo', 'bar']

        fetch.apt_purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-get', '--assume-yes', 'purge', 'foo', 'bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_as_string_fatal(self, log, mock_call,
                                               platform):
        packages = 'irrelevant names'
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_mark, packages, sentinel.mark,
                          fatal=True)
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_fatal(self, log, mock_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = ['irrelevant', 'names']
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_mark, packages, sentinel.mark,
                          fatal=True)
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_as_string_nofatal(self, log, mock_call,
                                                 platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = 'foo bar'

        fetch.apt_mark(packages, sentinel.mark)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-mark', sentinel.mark, 'foo bar'],
            universal_newlines=True)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_nofatal(self, log, mock_call,
                                       platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = ['foo', 'bar']

        fetch.apt_mark(packages, sentinel.mark)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-mark', sentinel.mark, 'foo', 'bar'],
            universal_newlines=True)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_nofatal_abortonfatal(self, log, mock_call,
                                                    platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        packages = ['foo', 'bar']

        fetch.apt_mark(packages, sentinel.mark, fatal=True)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-mark', sentinel.mark, 'foo', 'bar'],
            universal_newlines=True)

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_hold(self, apt_mark, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        fetch.apt_hold(sentinel.packages)
        apt_mark.assert_called_once_with(sentinel.packages, 'hold',
                                         fatal=False)

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_hold_fatal(self, apt_mark, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        fetch.apt_hold(sentinel.packages, fatal=sentinel.fatal)
        apt_mark.assert_called_once_with(sentinel.packages, 'hold',
                                         fatal=sentinel.fatal)

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_unhold(self, apt_mark, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        fetch.apt_unhold(sentinel.packages)
        apt_mark.assert_called_once_with(sentinel.packages, 'unhold',
                                         fatal=False)

    @patch.object(osplatform, 'get_platform')
    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_unhold_fatal(self, apt_mark, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        fetch.apt_unhold(sentinel.packages, fatal=sentinel.fatal)
        apt_mark.assert_called_once_with(sentinel.packages, 'unhold',
                                         fatal=sentinel.fatal)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_apt_update_fatal(self, check_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        fetch.apt_update(fatal=True)
        check_call.assert_called_with(
            ['apt-get', 'update'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    def test_apt_update_nonfatal(self, call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        fetch.apt_update()
        call.assert_called_with(
            ['apt-get', 'update'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('time.sleep')
    def test_run_apt_command_retries_if_fatal(self, check_call,
                                              sleep, platform):
        """The _run_apt_command function retries the command if it can't get
        the APT lock."""
        platform.return_value = 'ubuntu'
        imp.reload(fetch)

        self.called = False

        def side_effect(*args, **kwargs):
            """
            First, raise an exception (can't acquire lock), then return 0
            (the lock is grabbed).
            """
            if not self.called:
                self.called = True
                raise subprocess.CalledProcessError(
                    returncode=100, cmd="some command")
            else:
                return 0

        check_call.side_effect = side_effect
        check_call.return_value = 0

        from charmhelpers.fetch.ubuntu import _run_apt_command
        _run_apt_command(["some", "command"], fatal=True)
        self.assertTrue(sleep.called)


class YumTests(TestCase):

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_yum_upgrade_non_fatal(self, log, mock_call, platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        options = ['--foo', '--bar']
        fetch.upgrade(options)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      '--foo', '--bar', 'upgrade'],
                                     env=getenv())

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_yum_upgrade_fatal(self, log, mock_call, platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        options = ['--foo', '--bar']
        fetch.upgrade(options, fatal=True)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      '--foo', '--bar', 'upgrade'],
                                     env=getenv())

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_installs_yum_packages(self, log, mock_call, platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.install(packages, options)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      '--foo', '--bar', 'install',
                                      'foo', 'bar'],
                                     env=getenv())

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_installs_yum_packages_without_options(self, log, mock_call,
                                                   platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        packages = ['foo', 'bar']
        fetch.install(packages)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      'install', 'foo', 'bar'],
                                     env=getenv())

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_installs_yum_packages_as_string(self, log, mock_call,
                                             platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        packages = 'foo bar'
        fetch.install(packages)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      'install', 'foo bar'],
                                     env=getenv())

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_installs_yum_packages_with_possible_errors(self, log, mock_call,
                                                        platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.install(packages, options, fatal=True)

        mock_call.assert_called_with(['yum', '--assumeyes',
                                      '--foo', '--bar',
                                      'install', 'foo', 'bar'],
                                     env=getenv())

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.centos.log')
    def test_purges_yum_packages_as_string_fatal(self, log, mock_call,
                                                 platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        packages = 'irrelevant names'
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.centos.log')
    def test_purges_yum_packages_fatal(self, log, mock_call, platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        packages = ['irrelevant', 'names']
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_purges_yum_packages_as_string_nofatal(self, log, mock_call,
                                                   platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        packages = 'foo bar'
        fetch.purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(['yum', '--assumeyes',
                                      'remove', 'foo bar'],
                                     env=getenv())

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.call')
    @patch('charmhelpers.fetch.centos.log')
    def test_purges_yum_packages_nofatal(self, log, mock_call,
                                         platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        packages = ['foo', 'bar']
        fetch.purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(['yum', '--assumeyes',
                                      'remove', 'foo', 'bar'],
                                     env=getenv())

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.centos.log')
    def test_yum_update_fatal(self, log, check_call, platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        fetch.update(fatal=True)
        check_call.assert_called_with(['yum', '--assumeyes', 'update'],
                                      env=getenv())
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_output')
    @patch('charmhelpers.fetch.centos.log')
    def test_yum_search(self, log, check_output, platform):
        platform.return_value = 'centos'
        imp.reload(fetch)

        package = ['irrelevant']

        from charmhelpers.fetch.centos import yum_search
        yum_search(package)
        check_output.assert_called_with(['yum', 'search', 'irrelevant'])
        self.assertTrue(log.called)

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    @patch('time.sleep')
    def test_run_yum_command_retries_if_fatal(self, check_call,
                                              sleep, platform):
        """The _run_yum_command function retries the command if it can't get
        the YUM lock."""
        platform.return_value = 'centos'
        imp.reload(fetch)

        self.called = False

        def side_effect(*args, **kwargs):
            """
            First, raise an exception (can't acquire lock), then return 0
            (the lock is grabbed).
            """
            if not self.called:
                self.called = True
                raise subprocess.CalledProcessError(
                    returncode=1, cmd="some command")
            else:
                return 0

        check_call.side_effect = side_effect
        check_call.return_value = 0
        from charmhelpers.fetch.centos import _run_yum_command
        _run_yum_command(["some", "command"], fatal=True)
        self.assertTrue(sleep.called)

    @patch.object(osplatform, 'get_platform')
    @patch('apt_pkg.Cache')
    def test_get_upstream_version(self, cache, platform):
        platform.return_value = 'ubuntu'
        imp.reload(fetch)
        cache.side_effect = fake_apt_cache
        self.assertEqual(fetch.get_upstream_version('vim'), '7.3.547')
        self.assertEqual(fetch.get_upstream_version('emacs'), None)
        self.assertEqual(fetch.get_upstream_version('unknown'), None)
