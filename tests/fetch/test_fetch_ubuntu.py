import six
import subprocess
import io
import os
import tempfile

from tests.helpers import patch_open
from testtools import TestCase
from mock import (
    patch,
    MagicMock,
    call,
    sentinel,
    ANY,
)
from charmhelpers.fetch import ubuntu as fetch

if six.PY3:
    builtin_open = 'builtins.open'
else:
    builtin_open = '__builtin__.open'

# mocked return of openstack.lsb_release()
FAKE_RELEASE = {
    'DISTRIB_CODENAME': 'precise',
    'DISTRIB_RELEASE': '12.04',
    'DISTRIB_ID': 'Ubuntu',
    'DISTRIB_DESCRIPTION': '"Ubuntu 12.04"'
}

url = 'deb ' + fetch.CLOUD_ARCHIVE_URL
UCA_SOURCES = [
    ('cloud:precise-folsom/proposed', url + ' precise-proposed/folsom main'),
    ('cloud:precise-folsom', url + ' precise-updates/folsom main'),
    ('cloud:precise-folsom/updates', url + ' precise-updates/folsom main'),
    ('cloud:precise-grizzly/proposed', url + ' precise-proposed/grizzly main'),
    ('cloud:precise-grizzly', url + ' precise-updates/grizzly main'),
    ('cloud:precise-grizzly/updates', url + ' precise-updates/grizzly main'),
    ('cloud:precise-havana/proposed', url + ' precise-proposed/havana main'),
    ('cloud:precise-havana', url + ' precise-updates/havana main'),
    ('cloud:precise-havana/updates', url + ' precise-updates/havana main'),
    ('cloud:precise-icehouse/proposed',
     url + ' precise-proposed/icehouse main'),
    ('cloud:precise-icehouse', url + ' precise-updates/icehouse main'),
    ('cloud:precise-icehouse/updates', url + ' precise-updates/icehouse main'),
]

PGP_KEY_ASCII_ARMOR = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: SKS 1.1.5
Comment: Hostname: keyserver.ubuntu.com

mI0EUCEyTAEEAMuUxyfiegCCwn4J/c0nw5PUTSJdn5FqiUTq6iMfij65xf1vl0g/Mxqw0gfg
AJIsCDvO9N9dloLAwF6FUBMg5My7WyhRPTAKF505TKJboyX3Pp4J1fU1LV8QFVOp87vUh1Rz
B6GU7cSglhnbL85gmbJTllkzkb3h4Yw7W+edjcQ/ABEBAAG0K0xhdW5jaHBhZCBQUEEgZm9y
IFVidW50dSBDbG91ZCBBcmNoaXZlIFRlYW2IuAQTAQIAIgUCUCEyTAIbAwYLCQgHAwIGFQgC
CQoLBBYCAwECHgECF4AACgkQimhEop9oEE7kJAP/eTBgq3Mhbvo0d8elMOuqZx3nmU7gSyPh
ep0zYIRZ5TJWl/7PRtvp0CJA6N6ZywYTQ/4ANHhpibcHZkh8K0AzUvsGXnJRSFoJeqyDbD91
EhoO+4ZfHs2HvRBQEDZILMa2OyuB497E5Mmyua3HDEOrG2cVLllsUZzpTFCx8NgeMHk=
=jLBm
-----END PGP PUBLIC KEY BLOCK-----
"""

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
    @patch('apt_pkg.Cache')
    def test_filter_packages_missing_ubuntu(self, cache, log):
        cache.side_effect = fake_apt_cache
        result = fetch.filter_installed_packages(['vim', 'emacs'])
        self.assertEquals(result, ['emacs'])

    @patch("charmhelpers.fetch.ubuntu.log")
    @patch('apt_pkg.Cache')
    def test_filter_packages_none_missing_ubuntu(self, cache, log):
        cache.side_effect = fake_apt_cache
        result = fetch.filter_installed_packages(['vim'])
        self.assertEquals(result, [])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('apt_pkg.Cache')
    def test_filter_packages_not_available_ubuntu(self, cache, log):
        cache.side_effect = fake_apt_cache
        result = fetch.filter_installed_packages(['vim', 'joe'])
        self.assertEquals(result, ['joe'])
        log.assert_called_with('Package joe has no installation candidate.',
                               level='WARNING')

    @patch('charmhelpers.fetch.ubuntu.filter_installed_packages')
    def test_filter_missing_packages(self, filter_installed_packages):
        filter_installed_packages.return_value = ['pkga']
        self.assertEqual(['pkgb'],
                         fetch.filter_missing_packages(['pkga', 'pkgb']))

    @patch.object(fetch, 'log', lambda *args, **kwargs: None)
    def test_import_apt_key_radix(self):
        """Ensure shell out apt-key during key import"""
        with patch('subprocess.check_call') as _subp:
            fetch.import_key('foo')
            cmd = ['apt-key', 'adv', '--keyserver',
                   'hkp://keyserver.ubuntu.com:80', '--recv-keys', 'foo']
            _subp.assert_called_with(cmd)

    @patch.object(fetch, 'log', lambda *args, **kwargs: None)
    def test_import_apt_key_ascii_armor(self):
        with tempfile.NamedTemporaryFile() as tmp:
            with patch.object(fetch, 'NamedTemporaryFile') as mock_tmpfile:
                tmpfile = mock_tmpfile.return_value
                tmpfile.__enter__.return_value = tmpfile
                tmpfile.name = tmp.name
                with patch('subprocess.check_call') as _subp:
                    fetch.import_key(PGP_KEY_ASCII_ARMOR)
                    cmd = ['apt-key', 'add', tmp.name]
                    _subp.assert_called_with(cmd)
                with open(tmp.name, 'r') as f:
                    self.assertEqual(PGP_KEY_ASCII_ARMOR, f.read())

    @patch.object(fetch, 'log', lambda *args, **kwargs: None)
    def test_import_bad_apt_key(self):
        """Ensure error when importing apt key fails"""
        with patch('subprocess.check_call') as _subp:
            cmd = ['apt-key', 'adv', '--keyserver',
                   'hkp://keyserver.ubuntu.com:80', '--recv-keys', 'foo']
            _subp.side_effect = subprocess.CalledProcessError(1, cmd, '')
            try:
                fetch.import_key('foo')
                assert False
            except fetch.GPGKeyError as e:
                self.assertEqual(str(e), "Error importing PGP key 'foo'")

    @patch('charmhelpers.fetch.ubuntu.log')
    def test_add_source_none_ubuntu(self, log):
        fetch.add_source(source=None)
        self.assertTrue(log.called)

    @patch('subprocess.check_call')
    def test_add_source_ppa(self, check_call):
        source = "ppa:test-ppa"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source])

    @patch("charmhelpers.fetch.ubuntu.log")
    @patch('subprocess.check_call')
    @patch('time.sleep')
    def test_add_source_ppa_retries_30_times(self, sleep, check_call, log):
        self.call_count = 0

        def side_effect(*args, **kwargs):
            """Raise an 3 times, then return 0 """
            self.call_count += 1
            if self.call_count <= fetch.CMD_RETRY_COUNT:
                raise subprocess.CalledProcessError(
                    returncode=1, cmd="some add-apt-repository command")
            else:
                return 0
        check_call.side_effect = side_effect

        source = "ppa:test-ppa"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source])
        sleep.assert_called_with(10)
        self.assertTrue(fetch.CMD_RETRY_COUNT, sleep.call_count)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_http_ubuntu(self, check_call, log):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_https(self, check_call, log):
        source = "https://example.com"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_deb(self, check_call, log):
        """add-apt-repository behaves differently when using the deb prefix.

        $ add-apt-repository --yes \
            "http://special.example.com/ubuntu precise-special main"
        $ grep special /etc/apt/sources.list
        deb http://special.example.com/ubuntu precise precise-special main
        deb-src http://special.example.com/ubuntu precise precise-special main

        $ add-apt-repository --yes \
            "deb http://special.example.com/ubuntu precise-special main"
        $ grep special /etc/apt/sources.list
        deb http://special.example.com/ubuntu precise precise-special main
        deb-src http://special.example.com/ubuntu precise precise-special main
        deb http://special.example.com/ubuntu precise-special main
        deb-src http://special.example.com/ubuntu precise-special main
        """
        source = "deb http://archive.ubuntu.com/ubuntu raring-backports main"
        fetch.add_source(source=source)
        check_call.assert_called_with(
            ['add-apt-repository', '--yes', source])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_id(self, check_call, log):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key_id = "akey"
        check_call.return_value = 0  # Successful exit code
        fetch.add_source(source=source, key=key_id)
        check_call.assert_has_calls([
            call(['add-apt-repository', '--yes', source]),
            call(['apt-key', 'adv', '--keyserver',
                  'hkp://keyserver.ubuntu.com:80', '--recv-keys', key_id])
        ])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_https_and_key_id(self, check_call, log):
        source = "https://USER:PASS@private-ppa.launchpad.net/project/awesome"
        key_id = "GPGPGP"
        check_call.return_value = 0  # Success from both calls
        fetch.add_source(source=source, key=key_id)
        check_call.assert_has_calls([
            call(['add-apt-repository', '--yes', source]),
            call(['apt-key', 'adv', '--keyserver',
                  'hkp://keyserver.ubuntu.com:80', '--recv-keys', key_id])
        ])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key(self, check_call, log):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key = '''
            -----BEGIN PGP PUBLIC KEY BLOCK-----
            [...]
            -----END PGP PUBLIC KEY BLOCK-----
            '''
        with patch('subprocess.check_call') as check_call:
            check_call.return_value = 0
            fetch.add_source(source=source, key=key)
            check_call.assert_any_call(['add-apt-repository', '--yes', source])
            check_call.assert_any_call(['apt-key', 'add', ANY])

    def test_add_source_cloud_invalid_pocket(self):
        source = "cloud:havana-updates"
        self.assertRaises(fetch.SourceConfigError,
                          fetch.add_source, source)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    @patch.object(fetch, 'lsb_release')
    def test_add_source_cloud_pocket_style(self, lsb_release, apt_install,
                                           filter_pkg, log):
        source = "cloud:precise-updates/havana"
        lsb_release.return_value = {'DISTRIB_CODENAME': 'precise'}
        result = ('# Ubuntu Cloud Archive\n'
                  'deb http://ubuntu-cloud.archive.canonical.com/ubuntu'
                  ' precise-updates/havana main\n')

        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    @patch.object(fetch, 'lsb_release')
    def test_add_source_cloud_os_style(self, lsb_release, apt_install,
                                       filter_pkg, log):
        source = "cloud:precise-havana"
        lsb_release.return_value = {'DISTRIB_CODENAME': 'precise'}
        result = ('# Ubuntu Cloud Archive\n'
                  'deb http://ubuntu-cloud.archive.canonical.com/ubuntu'
                  ' precise-updates/havana main\n')
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    def test_add_source_cloud_distroless_style(self, apt_install,
                                               filter_pkg, log):
        source = "cloud:havana"
        result = ('# Ubuntu Cloud Archive\n'
                  'deb http://ubuntu-cloud.archive.canonical.com/ubuntu'
                  ' precise-updates/havana main\n')
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'lsb_release')
    @patch('platform.machine')
    def test_add_source_proposed_x86_64(self, _machine, lsb_release, log):
        source = "proposed"
        result = ('# Proposed\n'
                  'deb http://archive.ubuntu.com/ubuntu precise-proposed'
                  ' main universe multiverse restricted\n')
        lsb_release.return_value = {'DISTRIB_CODENAME': 'precise'}
        _machine.return_value = 'x86_64'
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch.object(fetch, 'lsb_release')
    @patch('platform.machine')
    def test_add_source_proposed_ppc64le(self, _machine, lsb_release, log):
        source = "proposed"
        result = (
            "# Proposed\n"
            "deb http://ports.ubuntu.com/ubuntu-ports precise-proposed main "
            "universe multiverse restricted\n")
        lsb_release.return_value = {'DISTRIB_CODENAME': 'precise'}
        _machine.return_value = 'ppc64le'
        with patch_open() as (mock_open, mock_file):
            fetch.add_source(source=source)
            mock_file.write.assert_called_with(result)

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_id_ubuntu(self, check_call, log):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key_id = "akey"
        fetch.add_source(source=source, key=key_id)
        check_call.assert_any_call(['add-apt-repository', '--yes', source]),
        check_call.assert_any_call([
            'apt-key', 'adv', '--keyserver',
            'hkp://keyserver.ubuntu.com:80', '--recv-keys', key_id])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_https_and_key_id_ubuntu(self, check_call, log):
        source = "https://USER:PASS@private-ppa.launchpad.net/project/awesome"
        key_id = "GPGPGP"
        fetch.add_source(source=source, key=key_id)
        check_call.assert_any_call(['add-apt-repository', '--yes', source]),
        check_call.assert_any_call([
            'apt-key', 'adv', '--keyserver',
            'hkp://keyserver.ubuntu.com:80', '--recv-keys', key_id])

    @patch('charmhelpers.fetch.ubuntu.log')
    @patch('subprocess.check_call')
    def test_add_source_http_and_key_ubuntu(self, check_call, log):
        source = "http://archive.ubuntu.com/ubuntu raring-backports main"
        key = '''
            -----BEGIN PGP PUBLIC KEY BLOCK-----
            [...]
            -----END PGP PUBLIC KEY BLOCK-----
            '''
        fetch.add_source(source=source, key=key)
        check_call.assert_any_call(['add-apt-repository', '--yes', source])
        check_call.assert_any_call(['apt-key', 'add', ANY])

    @patch('charmhelpers.fetch.ubuntu.log')
    def test_configure_bad_install_source(self, log):
        try:
            fetch.add_source('foo', fail_invalid=True)
            self.fail("Calling add_source('foo') should fail")
        except fetch.SourceConfigError as e:
            self.assertEqual(str(e), "Unknown source: 'foo'")

    @patch('charmhelpers.fetch.ubuntu.lsb_release')
    def test_configure_install_source_uca_staging(self, _lsb):
        """Test configuring installation source from UCA staging sources"""
        _lsb.return_value = FAKE_RELEASE
        # staging pockets are configured as PPAs
        with patch('subprocess.check_call') as _subp:
            src = 'cloud:precise-folsom/staging'
            fetch.add_source(src)
            cmd = ['add-apt-repository', '-y',
                   'ppa:ubuntu-cloud-archive/folsom-staging']
            _subp.assert_called_with(cmd)

    @patch(builtin_open)
    @patch('charmhelpers.fetch.ubuntu.apt_install')
    @patch('charmhelpers.fetch.ubuntu.lsb_release')
    @patch('charmhelpers.fetch.ubuntu.filter_installed_packages')
    def test_configure_install_source_uca_repos(
            self, _fip, _lsb, _install, _open):
        """Test configuring installation source from UCA sources"""
        _lsb.return_value = FAKE_RELEASE
        _file = MagicMock(spec=io.FileIO)
        _open.return_value = _file
        _fip.side_effect = lambda x: x
        for src, url in UCA_SOURCES:
            actual_url = "# Ubuntu Cloud Archive\n{}\n".format(url)
            fetch.add_source(src)
            _install.assert_called_with(['ubuntu-cloud-keyring'],
                                        fatal=True)
            _open.assert_called_with(
                '/etc/apt/sources.list.d/cloud-archive.list',
                'w'
            )
            _file.__enter__().write.assert_called_with(actual_url)

    def test_configure_install_source_bad_uca(self):
        """Test configuring installation source from bad UCA source"""
        try:
            fetch.add_source('cloud:foo-bar', fail_invalid=True)
            self.fail("add_source('cloud:foo-bar') should fail")
        except fetch.SourceConfigError as e:
            _e = ('Invalid Cloud Archive release specified: foo-bar'
                  ' on this Ubuntuversion')
            self.assertTrue(str(e).startswith(_e))

    @patch('charmhelpers.fetch.ubuntu.log')
    def test_add_unparsable_source(self, log_):
        source = "propsed"  # Minor typo
        fetch.add_source(source=source)
        self.assertEqual(1, log_.call_count)

    @patch('charmhelpers.fetch.ubuntu.log')
    def test_add_distro_source(self, log):
        source = "distro"
        # distro is a noop but test validate no exception is thrown
        fetch.add_source(source=source)


class AptTests(TestCase):

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_apt_upgrade_non_fatal(self, log, mock_call):
        options = ['--foo', '--bar']
        fetch.apt_upgrade(options)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'upgrade'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_apt_upgrade_fatal(self, log, mock_call):
        options = ['--foo', '--bar']
        fetch.apt_upgrade(options, fatal=True)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'upgrade'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_apt_dist_upgrade_fatal(self, log, mock_call):
        options = ['--foo', '--bar']
        fetch.apt_upgrade(options, fatal=True, dist=True)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'dist-upgrade'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages(self, log, mock_call):
        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.apt_install(packages, options)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'install', 'foo', 'bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages_without_options(self, log, mock_call):
        packages = ['foo', 'bar']

        fetch.apt_install(packages)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--option=Dpkg::Options::=--force-confold',
             'install', 'foo', 'bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages_as_string(self, log, mock_call):
        packages = 'foo bar'
        options = ['--foo', '--bar']

        fetch.apt_install(packages, options)

        mock_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'install', 'foo bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_installs_apt_packages_with_possible_errors(self, log,
                                                        check_call):
        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        fetch.apt_install(packages, options, fatal=True)

        check_call.assert_called_with(
            ['apt-get', '--assume-yes',
             '--foo', '--bar', 'install', 'foo', 'bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_as_string_fatal(self, log, mock_call):
        packages = 'irrelevant names'
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_fatal(self, log, mock_call):
        packages = ['irrelevant', 'names']
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_purge, packages, fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_as_string_nofatal(self, log, mock_call):
        packages = 'foo bar'

        fetch.apt_purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-get', '--assume-yes', 'purge', 'foo bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_purges_apt_packages_nofatal(self, log, mock_call):
        packages = ['foo', 'bar']

        fetch.apt_purge(packages)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-get', '--assume-yes', 'purge', 'foo', 'bar'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_as_string_fatal(self, log, mock_call):
        packages = 'irrelevant names'
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_mark, packages, sentinel.mark,
                          fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_fatal(self, log, mock_call):
        packages = ['irrelevant', 'names']
        mock_call.side_effect = OSError('fail')

        self.assertRaises(OSError, fetch.apt_mark, packages, sentinel.mark,
                          fatal=True)
        self.assertTrue(log.called)

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_as_string_nofatal(self, log, mock_call):
        packages = 'foo bar'

        fetch.apt_mark(packages, sentinel.mark)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-mark', sentinel.mark, 'foo bar'],
            universal_newlines=True)

    @patch('subprocess.call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_nofatal(self, log, mock_call):
        packages = ['foo', 'bar']

        fetch.apt_mark(packages, sentinel.mark)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-mark', sentinel.mark, 'foo', 'bar'],
            universal_newlines=True)

    @patch('subprocess.check_call')
    @patch('charmhelpers.fetch.ubuntu.log')
    def test_mark_apt_packages_nofatal_abortonfatal(self, log, mock_call):
        packages = ['foo', 'bar']

        fetch.apt_mark(packages, sentinel.mark, fatal=True)

        self.assertTrue(log.called)
        mock_call.assert_called_with(
            ['apt-mark', sentinel.mark, 'foo', 'bar'],
            universal_newlines=True)

    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_hold(self, apt_mark):
        fetch.apt_hold(sentinel.packages)
        apt_mark.assert_called_once_with(sentinel.packages, 'hold',
                                         fatal=False)

    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_hold_fatal(self, apt_mark):
        fetch.apt_hold(sentinel.packages, fatal=sentinel.fatal)
        apt_mark.assert_called_once_with(sentinel.packages, 'hold',
                                         fatal=sentinel.fatal)

    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_unhold(self, apt_mark):
        fetch.apt_unhold(sentinel.packages)
        apt_mark.assert_called_once_with(sentinel.packages, 'unhold',
                                         fatal=False)

    @patch('charmhelpers.fetch.ubuntu.apt_mark')
    def test_apt_unhold_fatal(self, apt_mark):
        fetch.apt_unhold(sentinel.packages, fatal=sentinel.fatal)
        apt_mark.assert_called_once_with(sentinel.packages, 'unhold',
                                         fatal=sentinel.fatal)

    @patch('subprocess.check_call')
    def test_apt_update_fatal(self, check_call):
        fetch.apt_update(fatal=True)
        check_call.assert_called_with(
            ['apt-get', 'update'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.call')
    def test_apt_update_nonfatal(self, call):
        fetch.apt_update()
        call.assert_called_with(
            ['apt-get', 'update'],
            env=getenv({'DEBIAN_FRONTEND': 'noninteractive'}))

    @patch('subprocess.check_call')
    @patch('time.sleep')
    def test_run_apt_command_retries_if_fatal(self, check_call, sleep):
        """The _run_apt_command function retries the command if it can't get
        the APT lock."""
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

    @patch('apt_pkg.Cache')
    def test_get_upstream_version(self, cache):
        cache.side_effect = fake_apt_cache
        self.assertEqual(fetch.get_upstream_version('vim'), '7.3.547')
        self.assertEqual(fetch.get_upstream_version('emacs'), None)
        self.assertEqual(fetch.get_upstream_version('unknown'), None)

    @patch('charmhelpers.fetch.ubuntu._run_apt_command')
    def test_apt_autoremove_fatal(self, run_apt_command):
        fetch.apt_autoremove(purge=True, fatal=True)
        run_apt_command.assert_called_with(
            ['apt-get', '--assume-yes', 'autoremove', '--purge'],
            True
        )

    @patch('charmhelpers.fetch.ubuntu._run_apt_command')
    def test_apt_autoremove_nonfatal(self, run_apt_command):
        fetch.apt_autoremove(purge=False, fatal=False)
        run_apt_command.assert_called_with(
            ['apt-get', '--assume-yes', 'autoremove'],
            False
        )
