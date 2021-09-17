import io
import os
import unittest
from copy import copy
from tests.helpers import patch_open, FakeRelation

from testtools import TestCase
from mock import MagicMock, patch, call

from charmhelpers.fetch import ubuntu as fetch
from charmhelpers.core.hookenv import WORKLOAD_STATES, flush

import charmhelpers.contrib.openstack.utils as openstack
import charmhelpers.contrib.openstack.deferred_events as deferred_events
from charmhelpers.contrib.openstack.exceptions import ServiceActionError
import contextlib

import six

if not six.PY3:
    builtin_open = '__builtin__.open'
    builtin_import = '__builtin__.__import__'
else:
    builtin_open = 'builtins.open'
    builtin_import = 'builtins.__import__'

FAKE_CODENAME = 'precise'
# mocked return of openstack.lsb_release()
FAKE_RELEASE = {
    'DISTRIB_CODENAME': 'precise',
    'DISTRIB_RELEASE': '12.04',
    'DISTRIB_ID': 'Ubuntu',
    'DISTRIB_DESCRIPTION': '"Ubuntu 12.04"'
}

FAKE_REPO = {
    # liberty patch release
    'neutron-common': {
        'pkg_vers': '2:7.0.1-0ubuntu1',
        'os_release': 'liberty',
        'os_version': '2015.2'
    },
    # liberty release version
    'nova-common': {
        'pkg_vers': '2:12.0.0~b1-0ubuntu1',
        'os_release': 'liberty',
        'os_version': '2015.2'
    },
    'nova': {
        'pkg_vers': '2012.2.3-0ubuntu2.1',
        'os_release': 'folsom',
        'os_version': '2012.2'
    },
    'glance-common': {
        'pkg_vers': '2012.1.3+stable-20130423-74b067df-0ubuntu1',
        'os_release': 'essex',
        'os_version': '2012.1'
    },
    'keystone-common': {
        'pkg_vers': '1:2013.1-0ubuntu1.1~cloud0',
        'os_release': 'grizzly',
        'os_version': '2013.1'
    },
    # Exercise swift version detection
    'swift-storage': {
        'pkg_vers': '1.8.0-0ubuntu1',
        'os_release': 'grizzly',
        'os_version': '1.8.0'
    },
    'swift-proxy': {
        'pkg_vers': '1.13.1-0ubuntu1',
        'os_release': 'icehouse',
        'os_version': '1.13.1'
    },
    'swift-common': {
        'pkg_vers': '1.10.0~rc1-0ubuntu1',
        'os_release': 'havana',
        'os_version': '1.10.0'
    },
    'swift-mitaka-dev': {
        'pkg_vers': '2.7.1.dev8.201605111703.trusty-0ubuntu1',
        'os_release': 'mitaka',
        'os_version': '2.7.0'
    },
    # a package that's available in the cache but is not installed
    'cinder-common': {
        'os_release': 'havana',
        'os_version': '2013.2'
    },
    # poorly formed openstack version
    'bad-version': {
        'pkg_vers': '1:2200.1-0ubuntu1.1~cloud0',
        'os_release': None,
        'os_version': None
    }
}

MOUNTS = [
    ['/mnt', '/dev/vdb']
]

url = 'deb ' + openstack.CLOUD_ARCHIVE_URL
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

# Mock python-dnspython resolver used by get_host_ip()


class FakeAnswer(object):

    def __init__(self, ip):
        self.ip = ip

    def __str__(self):
        return self.ip


class FakeResolver(object):

    def __init__(self, ip):
        self.ip = ip

    def query(self, hostname, query_type):
        if self.ip == '':
            return []
        else:
            return [FakeAnswer(self.ip)]


class FakeReverse(object):

    def from_address(self, address):
        return '156.94.189.91.in-addr.arpa'


class FakeDNSName(object):

    def __init__(self, dnsname):
        pass


class FakeDNS(object):

    def __init__(self, ip):
        self.resolver = FakeResolver(ip)
        self.reversename = FakeReverse()
        self.name = MagicMock()
        self.name.Name = FakeDNSName


class OpenStackHelpersTestCase(TestCase):

    def setUp(self):
        super(OpenStackHelpersTestCase, self).setUp()
        self.patch(fetch, 'get_apt_dpkg_env', lambda: {})
        # Make sleep() and log() into noops for testing
        for funcname in ('charmhelpers.core.decorators.log', 'charmhelpers.core.decorators.time.sleep'):
            patcher = patch(funcname, return_value=None)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _apt_cache(self):
        # mocks out the apt cache
        def cache_get(package):
            pkg = MagicMock()
            if package in FAKE_REPO and 'pkg_vers' in FAKE_REPO[package]:
                pkg.name = package
                pkg.current_ver.ver_str = FAKE_REPO[package]['pkg_vers']
            elif (package in FAKE_REPO and
                  'pkg_vers' not in FAKE_REPO[package]):
                pkg.name = package
                pkg.current_ver = None
            else:
                raise KeyError
            return pkg
        cache = MagicMock()
        cache.__getitem__.side_effect = cache_get
        return cache

    @patch.object(openstack, 'filter_missing_packages')
    def test_get_installed_semantic_versioned_packages(self, mock_filter):
        def _filter_missing_packages(pkgs):
            return [x for x in pkgs if x in ['cinder-common']]
        mock_filter.side_effect = _filter_missing_packages
        self.assertEquals(
            openstack.get_installed_semantic_versioned_packages(),
            ['cinder-common'])

    @patch('charmhelpers.contrib.openstack.utils.lsb_release')
    def test_os_codename_from_install_source(self, mocked_lsb):
        """Test mapping install source to OpenStack release name"""
        mocked_lsb.return_value = FAKE_RELEASE

        # the openstack release shipped with respective ubuntu/lsb release.
        self.assertEquals(openstack.get_os_codename_install_source('distro'),
                          'essex')
        # proposed pocket
        self.assertEquals(openstack.get_os_codename_install_source(
            'distro-proposed'),
            'essex')
        self.assertEquals(openstack.get_os_codename_install_source(
            'proposed'),
            'essex')

        # various cloud archive pockets
        src = 'cloud:precise-grizzly'
        self.assertEquals(openstack.get_os_codename_install_source(src),
                          'grizzly')
        src = 'cloud:precise-grizzly/proposed'
        self.assertEquals(openstack.get_os_codename_install_source(src),
                          'grizzly')

        # ppas and full repo urls.
        src = 'ppa:openstack-ubuntu-testing/havana-trunk-testing'
        self.assertEquals(openstack.get_os_codename_install_source(src),
                          'havana')
        src = ('deb http://ubuntu-cloud.archive.canonical.com/ubuntu '
               'precise-havana main')
        self.assertEquals(openstack.get_os_codename_install_source(src),
                          'havana')
        self.assertEquals(openstack.get_os_codename_install_source(None),
                          '')

    @patch.object(openstack, 'get_os_version_codename')
    @patch.object(openstack, 'get_os_codename_install_source')
    def test_os_version_from_install_source(self, codename, version):
        codename.return_value = 'grizzly'
        openstack.get_os_version_install_source('cloud:precise-grizzly')
        version.assert_called_with('grizzly')

    @patch('charmhelpers.contrib.openstack.utils.lsb_release')
    def test_os_codename_from_bad_install_source(self, mocked_lsb):
        """Test mapping install source to OpenStack release name"""
        _fake_release = copy(FAKE_RELEASE)
        _fake_release['DISTRIB_CODENAME'] = 'natty'

        mocked_lsb.return_value = _fake_release
        _e = 'charmhelpers.contrib.openstack.utils.error_out'
        with patch(_e) as mocked_err:
            openstack.get_os_codename_install_source('distro')
            _er = ('Could not derive openstack release for this Ubuntu '
                   'release: natty')
            mocked_err.assert_called_with(_er)

    def test_os_codename_from_version(self):
        """Test mapping OpenStack numerical versions to code name"""
        self.assertEquals(openstack.get_os_codename_version('2013.1'),
                          'grizzly')

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_codename_from_bad_version(self, mocked_error):
        """Test mapping a bad OpenStack numerical versions to code name"""
        openstack.get_os_codename_version('2014.5.5')
        expected_err = ('Could not determine OpenStack codename for '
                        'version 2014.5.5')
        mocked_error.assert_called_with(expected_err)

    def test_os_version_from_codename(self):
        """Test mapping a OpenStack codename to numerical version"""
        self.assertEquals(openstack.get_os_version_codename('folsom'),
                          '2012.2')

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_version_from_bad_codename(self, mocked_error):
        """Test mapping a bad OpenStack codename to numerical version"""
        openstack.get_os_version_codename('foo')
        expected_err = 'Could not derive OpenStack version for codename: foo'
        mocked_error.assert_called_with(expected_err)

    def test_os_version_swift_from_codename(self):
        """Test mapping a swift codename to numerical version"""
        self.assertEquals(openstack.get_os_version_codename_swift('liberty'),
                          '2.5.0')

    def test_get_swift_codename_single_version_kilo(self):
        self.assertEquals(openstack.get_swift_codename('2.2.2'), 'kilo')

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_version_swift_from_bad_codename(self, mocked_error):
        """Test mapping a bad swift codename to numerical version"""
        openstack.get_os_version_codename_swift('foo')
        expected_err = 'Could not derive swift version for codename: foo'
        mocked_error.assert_called_with(expected_err)

    def test_get_swift_codename_multiple_versions_liberty(self):
        with patch('subprocess.check_output') as _subp:
            _subp.return_value = b"... trusty-updates/liberty/main ..."
            self.assertEquals(openstack.get_swift_codename('2.5.0'), 'liberty')

    def test_get_swift_codename_multiple_versions_mitaka(self):
        with patch('subprocess.check_output') as _subp:
            _subp.return_value = b"... trusty-updates/mitaka/main ..."
            self.assertEquals(openstack.get_swift_codename('2.5.0'), 'mitaka')

    def test_get_swift_codename_none(self):
        self.assertEquals(openstack.get_swift_codename('1.2.3'), None)

    @patch("charmhelpers.core.hookenv.cache", new={})
    @patch.object(openstack, 'openstack_release')
    @patch.object(openstack, 'filter_installed_packages')
    @patch.object(openstack, 'apt_install')
    def test_get_installed_os_version_no_package(self, mock_apt_install,
                                                 mock_filter_installed_packages,
                                                 mock_openstack_release):
        mock_openstack_release.return_value = {}
        self.assertEquals(
            openstack.get_installed_os_version(), None)

    @patch("charmhelpers.core.hookenv.cache", new={})
    @patch.object(openstack, 'openstack_release')
    @patch.object(openstack, 'filter_installed_packages')
    @patch.object(openstack, 'apt_install')
    def test_get_installed_os_version_with_package(self, mock_apt_install,
                                                   mock_filter_installed_packages,
                                                   mock_openstack_release):
        mock_openstack_release.return_value = {'OPENSTACK_CODENAME': 'wallaby'}
        self.assertEquals(
            openstack.get_installed_os_version(), 'wallaby')

    @patch.object(openstack, 'get_installed_os_version')
    @patch.object(openstack, 'snap_install_requested')
    def test_os_codename_from_package(self, mock_snap_install_requested,
                                      mock_get_installed_os_version):
        """Test deriving OpenStack codename from an installed package"""
        mock_snap_install_requested.return_value = False
        mock_get_installed_os_version.return_value = None
        with patch.object(openstack, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            for pkg, vers in six.iteritems(FAKE_REPO):
                # test fake repo for all "installed" packages
                if pkg.startswith('bad-'):
                    continue
                if 'pkg_vers' not in vers:
                    continue
                self.assertEquals(openstack.get_os_codename_package(pkg),
                                  vers['os_release'])

    @patch.object(openstack, 'get_installed_os_version')
    @patch.object(openstack, 'snap_install_requested')
    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_codename_from_bad_package_version(self, mocked_error,
                                                  mock_snap_install_requested,
                                                  mock_get_installed_os_version):
        """Test deriving OpenStack codename for a poorly versioned package"""
        mock_snap_install_requested.return_value = False
        mock_get_installed_os_version.return_value = None
        with patch.object(openstack, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            openstack.get_os_codename_package('bad-version')
            _e = ('Could not determine OpenStack codename for version 2200.1')
            mocked_error.assert_called_with(_e)

    @patch.object(openstack, 'get_installed_os_version')
    @patch.object(openstack, 'snap_install_requested')
    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_codename_from_bad_package(self, mocked_error,
                                          mock_snap_install_requested,
                                          mock_get_installed_os_version):
        """Test deriving OpenStack codename from an unavailable package"""
        mock_snap_install_requested.return_value = False
        mock_get_installed_os_version.return_value = None
        with patch.object(openstack, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            try:
                openstack.get_os_codename_package('foo')
            except Exception:
                # ignore exceptions that raise when error_out is mocked
                # and doesn't sys.exit(1)
                pass
            e = 'Could not determine version of package with no installation '\
                'candidate: foo'
            mocked_error.assert_called_with(e)

    @patch.object(openstack, 'get_installed_os_version')
    @patch.object(openstack, 'snap_install_requested')
    def test_os_codename_from_bad_package_nonfatal(
            self, mock_snap_install_requested,
            mock_get_installed_os_version):
        """Test OpenStack codename from an unavailable package is non-fatal"""
        mock_snap_install_requested.return_value = False
        mock_get_installed_os_version.return_value = None
        with patch.object(openstack, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            self.assertEquals(
                None,
                openstack.get_os_codename_package('foo', fatal=False)
            )

    @patch.object(openstack, 'get_installed_os_version')
    @patch.object(openstack, 'snap_install_requested')
    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_codename_from_uninstalled_package(self, mock_error,
                                                  mock_snap_install_requested,
                                                  mock_get_installed_os_version):
        """Test OpenStack codename from an available but uninstalled pkg"""
        mock_snap_install_requested.return_value = False
        mock_get_installed_os_version.return_value = None
        with patch.object(openstack, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            try:
                openstack.get_os_codename_package('cinder-common', fatal=True)
            except Exception:
                pass
            e = ('Could not determine version of uninstalled package: '
                 'cinder-common')
            mock_error.assert_called_with(e)

    @patch.object(openstack, 'get_installed_os_version')
    @patch.object(openstack, 'snap_install_requested')
    def test_os_codename_from_uninstalled_package_nonfatal(
            self, mock_snap_install_requested,
            mock_get_installed_os_version):
        """Test OpenStack codename from avail uninstalled pkg is non fatal"""
        mock_snap_install_requested.return_value = False
        mock_get_installed_os_version.return_value = None
        with patch.object(openstack, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            self.assertEquals(
                None,
                openstack.get_os_codename_package('cinder-common', fatal=False)
            )

    @patch.object(openstack, 'get_installed_os_version')
    @patch.object(openstack, 'snap_install_requested')
    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_version_from_package(self, mocked_error,
                                     mock_snap_install_requested,
                                     mock_get_installed_os_version):
        """Test deriving OpenStack version from an installed package"""
        mock_snap_install_requested.return_value = False
        mock_get_installed_os_version.return_value = None
        with patch.object(openstack, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            for pkg, vers in six.iteritems(FAKE_REPO):
                if pkg.startswith('bad-'):
                    continue
                if 'pkg_vers' not in vers:
                    continue
                self.assertEquals(openstack.get_os_version_package(pkg),
                                  vers['os_version'])

    @patch.object(openstack, 'get_installed_os_version')
    @patch.object(openstack, 'snap_install_requested')
    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_version_from_bad_package(self, mocked_error,
                                         mock_snap_install_requested,
                                         mock_get_installed_os_version):
        """Test deriving OpenStack version from an uninstalled package"""
        mock_snap_install_requested.return_value = False
        mock_get_installed_os_version.return_value = None
        with patch.object(openstack, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            try:
                openstack.get_os_version_package('foo')
            except Exception:
                # ignore exceptions that raise when error_out is mocked
                # and doesn't sys.exit(1)
                pass
            e = 'Could not determine version of package with no installation '\
                'candidate: foo'
            mocked_error.assert_called_with(e)

    @patch.object(openstack, 'get_installed_os_version')
    @patch.object(openstack, 'snap_install_requested')
    def test_os_version_from_bad_package_nonfatal(
            self, mock_snap_install_requested,
            mock_get_installed_os_version):
        """Test OpenStack version from an uninstalled package is non-fatal"""
        mock_snap_install_requested.return_value = False
        mock_get_installed_os_version.return_value = None
        with patch.object(openstack, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            self.assertEquals(
                None,
                openstack.get_os_version_package('foo', fatal=False)
            )

    @patch.object(openstack, 'lsb_release')
    @patch.object(openstack, 'get_os_codename_package')
    @patch('charmhelpers.contrib.openstack.utils.config')
    def test_os_release_uncached(self, config, get_cn, mock_lsb_release):
        openstack._os_rel = None
        get_cn.return_value = 'folsom'
        mock_lsb_release.return_value = {
            'DISTRIB_CODENAME': 'bionic',
        }
        self.assertEquals('folsom', openstack.os_release('nova-common'))

    @patch.object(openstack, 'lsb_release')
    def test_os_release_cached(self, mock_lsb_release):
        openstack._os_rel = 'foo'
        mock_lsb_release.return_value = {
            'DISTRIB_CODENAME': 'bionic',
        }
        self.assertEquals('foo', openstack.os_release('nova-common'))

    @patch.object(openstack, 'juju_log')
    @patch('sys.exit')
    def test_error_out(self, mocked_exit, juju_log):
        """Test erroring out"""
        openstack.error_out('Everything broke.')
        _log = 'FATAL ERROR: Everything broke.'
        juju_log.assert_called_with(_log, level='ERROR')
        mocked_exit.assert_called_with(1)

    def test_get_source_and_pgp_key(self):
        tests = {
            "source|key": ('source', 'key'),
            "source|": ('source', None),
            "|key": ('', 'key'),
            "source": ('source', None),
        }
        for k, v in six.iteritems(tests):
            self.assertEqual(openstack.get_source_and_pgp_key(k), v)

    # These should still work, even though the bulk of the functionality has
    # moved to charmhelpers.fetch.add_source()
    def test_configure_install_source_distro(self):
        """Test configuring installation from distro"""
        self.assertIsNone(openstack.configure_installation_source('distro'))

    def test_configure_install_source_ppa(self):
        """Test configuring installation source from PPA"""
        with patch('subprocess.check_call') as mock:
            src = 'ppa:gandelman-a/openstack'
            openstack.configure_installation_source(src)
            ex_cmd = [
                'add-apt-repository', '--yes', 'ppa:gandelman-a/openstack']
            mock.assert_called_with(ex_cmd, env={})

    @patch('subprocess.check_call')
    @patch.object(fetch, 'import_key')
    def test_configure_install_source_deb_url(self, _import, _spcc):
        """Test configuring installation source from deb repo url"""
        src = ('deb http://ubuntu-cloud.archive.canonical.com/ubuntu '
               'precise-havana main|KEYID')
        openstack.configure_installation_source(src)
        _import.assert_called_with('KEYID')
        _spcc.assert_called_once_with(
            ['add-apt-repository', '--yes',
             'deb http://ubuntu-cloud.archive.canonical.com/ubuntu '
             'precise-havana main'], env={})

    @patch.object(fetch, 'get_distrib_codename')
    @patch(builtin_open)
    @patch('subprocess.check_call')
    def test_configure_install_source_distro_proposed(
            self, _spcc, _open, _lsb):
        """Test configuring installation source from deb repo url"""
        _lsb.return_value = FAKE_CODENAME
        _file = MagicMock(spec=io.FileIO)
        _open.return_value = _file
        openstack.configure_installation_source('distro-proposed')
        _file.__enter__().write.assert_called_once_with(
            '# Proposed\ndeb http://archive.ubuntu.com/ubuntu '
            'precise-proposed main universe multiverse restricted\n')
        src = ('deb http://archive.ubuntu.com/ubuntu/ precise-proposed '
               'restricted main multiverse universe')
        openstack.configure_installation_source(src)
        _spcc.assert_called_once_with(
            ['add-apt-repository', '--yes',
             'deb http://archive.ubuntu.com/ubuntu/ precise-proposed '
             'restricted main multiverse universe'], env={})

    @patch('charmhelpers.fetch.filter_installed_packages')
    @patch('charmhelpers.fetch.apt_install')
    @patch.object(openstack, 'error_out')
    @patch.object(openstack, 'juju_log')
    def test_add_source_cloud_invalid_pocket(self, _log, _out,
                                             apt_install, filter_pkg):
        openstack.configure_installation_source("cloud:havana-updates")
        _e = ('Invalid Cloud Archive release specified: '
              'havana-updates on this Ubuntuversion')
        _s = _out.call_args[0][0]
        self.assertTrue(_s.startswith(_e))

    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    @patch.object(fetch, 'get_distrib_codename')
    def test_add_source_cloud_pocket_style(self, get_distrib_codename,
                                           apt_install, filter_pkg):
        source = "cloud:precise-updates/havana"
        get_distrib_codename.return_value = 'precise'
        result = (
            "# Ubuntu Cloud Archive\n"
            "deb http://ubuntu-cloud.archive.canonical.com/ubuntu "
            "precise-updates/havana main\n")
        with patch_open() as (mock_open, mock_file):
            openstack.configure_installation_source(source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    @patch.object(fetch, 'get_distrib_codename')
    def test_add_source_cloud_os_style(self, get_distrib_codename,
                                       apt_install, filter_pkg):
        source = "cloud:precise-havana"
        get_distrib_codename.return_value = 'precise'
        result = (
            "# Ubuntu Cloud Archive\n"
            "deb http://ubuntu-cloud.archive.canonical.com/ubuntu "
            "precise-updates/havana main\n")
        with patch_open() as (mock_open, mock_file):
            openstack.configure_installation_source(source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch.object(fetch, 'filter_installed_packages')
    @patch.object(fetch, 'apt_install')
    def test_add_source_cloud_distroless_style(self, apt_install, filter_pkg):
        source = "cloud:havana"
        result = (
            "# Ubuntu Cloud Archive\n"
            "deb http://ubuntu-cloud.archive.canonical.com/ubuntu "
            "precise-updates/havana main\n")
        with patch_open() as (mock_open, mock_file):
            openstack.configure_installation_source(source)
            mock_file.write.assert_called_with(result)
        filter_pkg.assert_called_with(['ubuntu-cloud-keyring'])

    @patch('charmhelpers.fetch.ubuntu.log', lambda *args, **kwargs: None)
    @patch('charmhelpers.contrib.openstack.utils.juju_log',
           lambda *args, **kwargs: None)
    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_configure_bad_install_source(self, _error):
        openstack.configure_installation_source('foo')
        _error.assert_called_with("Unknown source: 'foo'")

    @patch.object(fetch, 'get_distrib_codename')
    def test_configure_install_source_uca_staging(self, _lsb):
        """Test configuring installation source from UCA staging sources"""
        _lsb.return_value = FAKE_CODENAME
        # staging pockets are configured as PPAs
        with patch('subprocess.check_call') as _subp:
            src = 'cloud:precise-folsom/staging'
            openstack.configure_installation_source(src)
            cmd = ['add-apt-repository', '-y',
                   'ppa:ubuntu-cloud-archive/folsom-staging']
            _subp.assert_called_with(cmd, env={})

    @patch(builtin_open)
    @patch.object(fetch, 'apt_install')
    @patch.object(fetch, 'get_distrib_codename')
    @patch.object(fetch, 'filter_installed_packages')
    def test_configure_install_source_uca_repos(
            self, _fip, _lsb, _install, _open):
        """Test configuring installation source from UCA sources"""
        _lsb.return_value = FAKE_CODENAME
        _file = MagicMock(spec=io.FileIO)
        _open.return_value = _file
        _fip.side_effect = lambda x: x
        for src, url in UCA_SOURCES:
            actual_url = "# Ubuntu Cloud Archive\n{}\n".format(url)
            openstack.configure_installation_source(src)
            _install.assert_called_with(['ubuntu-cloud-keyring'],
                                        fatal=True)
            _open.assert_called_with(
                '/etc/apt/sources.list.d/cloud-archive.list',
                'w'
            )
            _file.__enter__().write.assert_called_with(actual_url)

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_configure_install_source_bad_uca(self, mocked_error):
        """Test configuring installation source from bad UCA source"""
        try:
            openstack.configure_installation_source('cloud:foo-bar')
        except Exception:
            # ignore exceptions that raise when error_out is mocked
            # and doesn't sys.exit(1)
            pass
        _e = ('Invalid Cloud Archive release specified: foo-bar'
              ' on this Ubuntuversion')
        _s = mocked_error.call_args[0][0]
        self.assertTrue(_s.startswith(_e))

    @patch.object(openstack, 'fetch_import_key')
    def test_import_key_calls_fetch_import_key(self, fetch_import_key):
        openstack.import_key('random-string')
        fetch_import_key.assert_called_once_with('random-string')

    @patch.object(openstack, 'juju_log', lambda *args, **kwargs: None)
    @patch.object(openstack, 'fetch_import_key')
    @patch.object(openstack, 'sys')
    def test_import_key_calls_sys_exit_on_error(self, mock_sys,
                                                fetch_import_key):

        def raiser(_):
            raise openstack.GPGKeyError("an error occurred")
        fetch_import_key.side_effect = raiser
        openstack.import_key('random failure')
        mock_sys.exit.assert_called_once_with(1)

    @patch('os.mkdir')
    @patch('os.path.exists')
    @patch('charmhelpers.contrib.openstack.utils.charm_dir')
    @patch(builtin_open)
    def test_save_scriptrc(self, _open, _charm_dir, _exists, _mkdir):
        """Test generation of scriptrc from environment"""
        scriptrc = ['#!/bin/bash\n',
                    'export setting1=foo\n',
                    'export setting2=bar\n']
        _file = MagicMock(spec=io.FileIO)
        _open.return_value = _file
        _charm_dir.return_value = '/var/lib/juju/units/testing-foo-0/charm'
        _exists.return_value = False
        os.environ['JUJU_UNIT_NAME'] = 'testing-foo/0'
        openstack.save_script_rc(setting1='foo', setting2='bar')
        rcdir = '/var/lib/juju/units/testing-foo-0/charm/scripts'
        _mkdir.assert_called_with(rcdir)
        expected_f = '/var/lib/juju/units/testing-foo-0/charm/scripts/scriptrc'
        _open.assert_called_with(expected_f, 'wt')
        _mkdir.assert_called_with(os.path.dirname(expected_f))
        _file.__enter__().write.assert_has_calls(
            list(call(line) for line in scriptrc), any_order=True)

    @patch.object(openstack, 'lsb_release')
    @patch.object(openstack, 'get_os_version_package')
    @patch.object(openstack, 'get_os_version_codename_swift')
    @patch.object(openstack, 'config')
    def test_openstack_upgrade_detection_true(self, config, vers_swift,
                                              vers_pkg, lsb):
        """Test it detects when an openstack package has available upgrade"""
        lsb.return_value = FAKE_RELEASE
        config.return_value = 'cloud:precise-havana'
        vers_pkg.return_value = '2013.1.1'
        self.assertTrue(openstack.openstack_upgrade_available('nova-common'))
        # milestone to major release detection
        vers_pkg.return_value = '2013.2~b1'
        self.assertTrue(openstack.openstack_upgrade_available('nova-common'))
        vers_pkg.return_value = '1.9.0'
        vers_swift.return_value = '2.5.0'
        self.assertTrue(openstack.openstack_upgrade_available('swift-proxy'))
        vers_pkg.return_value = '2.5.0'
        vers_swift.return_value = '2.10.0'
        self.assertTrue(openstack.openstack_upgrade_available('swift-proxy'))

    @patch.object(openstack, 'lsb_release')
    @patch.object(openstack, 'get_os_version_package')
    @patch.object(openstack, 'config')
    def test_openstack_upgrade_detection_false(self, config, vers_pkg, lsb):
        """Test it detects when an openstack upgrade is not necessary"""
        lsb.return_value = FAKE_RELEASE
        config.return_value = 'cloud:precise-folsom'
        vers_pkg.return_value = '2013.1.1'
        self.assertFalse(openstack.openstack_upgrade_available('nova-common'))
        # milestone to majro release detection
        vers_pkg.return_value = '2013.1~b1'
        self.assertFalse(openstack.openstack_upgrade_available('nova-common'))
        # ugly duckling testing
        config.return_value = 'cloud:precise-havana'
        vers_pkg.return_value = '1.10.0'
        self.assertFalse(openstack.openstack_upgrade_available('swift-proxy'))

    @patch.object(openstack, 'is_block_device')
    @patch.object(openstack, 'error_out')
    def test_ensure_block_device_bad_config(self, err, is_bd):
        """Test it doesn't prepare storage with bad config"""
        openstack.ensure_block_device(block_device='none')
        self.assertTrue(err.called)

    @patch.object(openstack, 'is_block_device')
    @patch.object(openstack, 'ensure_loopback_device')
    def test_ensure_block_device_loopback(self, ensure_loopback, is_bd):
        """Test it ensures loopback device when checking block device"""
        defsize = openstack.DEFAULT_LOOPBACK_SIZE
        is_bd.return_value = True

        ensure_loopback.return_value = '/tmp/cinder.img'
        result = openstack.ensure_block_device('/tmp/cinder.img')
        ensure_loopback.assert_called_with('/tmp/cinder.img', defsize)
        self.assertEquals(result, '/tmp/cinder.img')

        ensure_loopback.return_value = '/tmp/cinder-2.img'
        result = openstack.ensure_block_device('/tmp/cinder-2.img|15G')
        ensure_loopback.assert_called_with('/tmp/cinder-2.img', '15G')
        self.assertEquals(result, '/tmp/cinder-2.img')

    @patch.object(openstack, 'is_block_device')
    def test_ensure_standard_block_device(self, is_bd):
        """Test it looks for storage at both relative and full device path"""
        for dev in ['vdb', '/dev/vdb']:
            openstack.ensure_block_device(dev)
            is_bd.assert_called_with('/dev/vdb')

    @patch.object(openstack, 'is_block_device')
    @patch.object(openstack, 'error_out')
    def test_ensure_nonexistent_block_device(self, error_out, is_bd):
        """Test it will not ensure a non-existent block device"""
        is_bd.return_value = False
        openstack.ensure_block_device(block_device='foo')
        self.assertTrue(error_out.called)

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'umount')
    @patch.object(openstack, 'mounts')
    @patch.object(openstack, 'zap_disk')
    @patch.object(openstack, 'is_lvm_physical_volume')
    def test_clean_storage_unmount(self, is_pv, zap_disk, mounts, umount, log):
        """Test it unmounts block device when cleaning storage"""
        is_pv.return_value = False
        zap_disk.return_value = True
        mounts.return_value = MOUNTS
        openstack.clean_storage('/dev/vdb')
        umount.called_with('/dev/vdb', True)

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'remove_lvm_physical_volume')
    @patch.object(openstack, 'deactivate_lvm_volume_group')
    @patch.object(openstack, 'mounts')
    @patch.object(openstack, 'is_lvm_physical_volume')
    def test_clean_storage_lvm_wipe(self, is_pv, mounts, rm_lv, rm_vg, log):
        """Test it removes traces of LVM when cleaning storage"""
        mounts.return_value = []
        is_pv.return_value = True
        openstack.clean_storage('/dev/vdb')
        rm_lv.assert_called_with('/dev/vdb')
        rm_vg .assert_called_with('/dev/vdb')

    @patch.object(openstack, 'zap_disk')
    @patch.object(openstack, 'is_lvm_physical_volume')
    @patch.object(openstack, 'mounts')
    def test_clean_storage_zap_disk(self, mounts, is_pv, zap_disk):
        """It removes traces of LVM when cleaning storage"""
        mounts.return_value = []
        is_pv.return_value = False
        openstack.clean_storage('/dev/vdb')
        zap_disk.assert_called_with('/dev/vdb')

    @patch('os.path.isfile')
    @patch(builtin_open)
    def test_get_matchmaker_map(self, _open, _isfile):
        _isfile.return_value = True
        mm_data = """
        {
           "cinder-scheduler": [
             "juju-t-machine-4"
            ]
        }
        """
        fh = _open.return_value.__enter__.return_value
        fh.read.return_value = mm_data
        self.assertEqual(
            openstack.get_matchmaker_map(),
            {'cinder-scheduler': ['juju-t-machine-4']}
        )

    @patch('os.path.isfile')
    @patch(builtin_open)
    def test_get_matchmaker_map_nofile(self, _open, _isfile):
        _isfile.return_value = False
        self.assertEqual(
            openstack.get_matchmaker_map(),
            {}
        )

    def test_incomplete_relation_data(self):
        configs = MagicMock()
        configs.complete_contexts.return_value = ['pgsql-db', 'amqp']
        required_interfaces = {
            'database': ['shared-db', 'pgsql-db'],
            'message': ['amqp', 'zeromq-configuration'],
            'identity': ['identity-service']}
        expected_result = 'identity'

        result = openstack.incomplete_relation_data(
            configs, required_interfaces)
        self.assertTrue(expected_result in result.keys())

    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_complete(
            self, is_unit_paused_set, status_set, log):
        configs = MagicMock()
        configs.complete_contexts.return_value = ['shared-db',
                                                  'amqp',
                                                  'identity-service']
        required_interfaces = {
            'database': ['shared-db', 'pgsql-db'],
            'message': ['amqp', 'zeromq-configuration'],
            'identity': ['identity-service']}

        openstack.set_os_workload_status(configs, required_interfaces)
        status_set.assert_called_with('active', 'Unit is ready')

    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.incomplete_relation_data',
           return_value={'identity': {'identity-service': {'related': True}}})
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_related_incomplete(
            self, is_unit_paused_set, status_set,
            incomplete_relation_data, log):
        configs = MagicMock()
        configs.complete_contexts.return_value = ['shared-db', 'amqp']
        required_interfaces = {
            'database': ['shared-db', 'pgsql-db'],
            'message': ['amqp', 'zeromq-configuration'],
            'identity': ['identity-service']}

        openstack.set_os_workload_status(configs, required_interfaces)
        status_set.assert_called_with('waiting',
                                      "Incomplete relations: identity")

    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.incomplete_relation_data',
           return_value={'identity': {'identity-service': {'related': False}}})
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_absent(
            self, is_unit_paused_set, status_set,
            incomplete_relation_data, log):
        configs = MagicMock()
        configs.complete_contexts.return_value = ['shared-db', 'amqp']
        required_interfaces = {
            'database': ['shared-db', 'pgsql-db'],
            'message': ['amqp', 'zeromq-configuration'],
            'identity': ['identity-service']}

        openstack.set_os_workload_status(configs, required_interfaces)
        status_set.assert_called_with('blocked',
                                      'Missing relations: identity')

    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.hook_name',
           return_value='identity-service-relation-broken')
    @patch('charmhelpers.contrib.openstack.utils.incomplete_relation_data',
           return_value={'identity': {'identity-service': {'related': True}}})
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_related_broken(
            self, is_unit_paused_set, status_set,
            incomplete_relation_data, hook_name, log):
        configs = MagicMock()
        configs.complete_contexts.return_value = ['shared-db', 'amqp']
        required_interfaces = {
            'database': ['shared-db', 'pgsql-db'],
            'message': ['amqp', 'zeromq-configuration'],
            'identity': ['identity-service']}

        openstack.set_os_workload_status(configs, required_interfaces)
        status_set.assert_called_with('blocked',
                                      "Missing relations: identity")

    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.incomplete_relation_data',
           return_value={'identity':
                         {'identity-service': {'related': True}},

                         'message':
                         {'amqp': {'missing_data': ['rabbitmq-password'],
                                   'related': True}},

                         'database':
                         {'shared-db': {'related': False}}
                         })
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_mixed(
            self, is_unit_paused_set, status_set,
            incomplete_relation_data, log):
        configs = MagicMock()
        configs.complete_contexts.return_value = ['shared-db', 'amqp']
        required_interfaces = {
            'database': ['shared-db', 'pgsql-db'],
            'message': ['amqp', 'zeromq-configuration'],
            'identity': ['identity-service']}

        openstack.set_os_workload_status(configs, required_interfaces)

        args = status_set.call_args
        actual_parm1 = args[0][0]
        actual_parm2 = args[0][1]
        expected1 = ("Missing relations: database; incomplete relations: "
                     "identity, message")
        expected2 = ("Missing relations: database; incomplete relations: "
                     "message, identity")
        self.assertTrue(actual_parm1 == 'blocked')
        self.assertTrue(actual_parm2 == expected1 or actual_parm2 == expected2)

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_complete_with_services_list(
            self, is_unit_paused_set, status_set, log,
            port_has_listener, service_running):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        services = ['database', 'identity']
        # Assume that the service and ports are open.
        port_has_listener.return_value = True
        service_running.return_value = True

        openstack.set_os_workload_status(
            configs, required_interfaces, services=services)
        status_set.assert_called_with('active', 'Unit is ready')

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_complete_services_list_not_running(
            self, is_unit_paused_set, status_set, log,
            port_has_listener, service_running):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        services = ['database', 'identity']
        port_has_listener.return_value = True
        # Fail the identity service
        service_running.side_effect = [True, False]

        openstack.set_os_workload_status(
            configs, required_interfaces, services=services)
        status_set.assert_called_with(
            'blocked',
            'Services not running that should be: identity')

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_complete_with_services(
            self, is_unit_paused_set, status_set, log,
            port_has_listener, service_running):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        services = [
            {'service': 'database', 'ports': [10, 20]},
            {'service': 'identity', 'ports': [30]},
        ]
        # Assume that the service and ports are open.
        port_has_listener.return_value = True
        service_running.return_value = True

        openstack.set_os_workload_status(
            configs, required_interfaces, services=services)
        status_set.assert_called_with('active', 'Unit is ready')

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_complete_service_not_running(
            self, is_unit_paused_set, status_set, log,
            port_has_listener, service_running):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        services = [
            {'service': 'database', 'ports': [10, 20]},
            {'service': 'identity', 'ports': [30]},
        ]
        port_has_listener.return_value = True
        # Fail the identity service
        service_running.side_effect = [True, False]

        openstack.set_os_workload_status(
            configs, required_interfaces, services=services)
        status_set.assert_called_with(
            'blocked',
            'Services not running that should be: identity')

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_complete_port_not_open(
            self, is_unit_paused_set, status_set, log,
            port_has_listener, service_running):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        services = [
            {'service': 'database', 'ports': [10, 20]},
            {'service': 'identity', 'ports': [30]},
        ]
        port_has_listener.side_effect = [True, False, True]
        # Fail the identity service
        service_running.return_value = True

        openstack.set_os_workload_status(
            configs, required_interfaces, services=services)
        status_set.assert_called_with(
            'blocked',
            'Services with ports not open that should be:'
            ' database: [20]')

    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=False)
    def test_set_os_workload_status_complete_ports_not_open(
            self, is_unit_paused_set, status_set, log, port_has_listener):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        ports = [50, 60, 70]
        port_has_listener.side_effect = [True, False, True]

        openstack.set_os_workload_status(
            configs, required_interfaces, ports=ports)
        status_set.assert_called_with(
            'blocked',
            'Ports which should be open, but are not: 60')

    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=True)
    def test_set_os_workload_status_paused_simple(
            self, is_unit_paused_set, status_set, log):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        openstack.set_os_workload_status(configs, required_interfaces)
        status_set.assert_called_with(
            'maintenance',
            "Paused. Use 'resume' action to resume normal service.")

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=True)
    def test_set_os_workload_status_paused_services_check(
            self, is_unit_paused_set, status_set, log,
            port_has_listener, service_running):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        services = [
            {'service': 'database', 'ports': [10, 20]},
            {'service': 'identity', 'ports': [30]},
        ]
        port_has_listener.return_value = False
        service_running.side_effect = [False, False]

        openstack.set_os_workload_status(
            configs, required_interfaces, services=services)
        status_set.assert_called_with(
            'maintenance',
            "Paused. Use 'resume' action to resume normal service.")

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=True)
    def test_set_os_workload_status_paused_services_fail(
            self, is_unit_paused_set, status_set, log,
            port_has_listener, service_running):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        services = [
            {'service': 'database', 'ports': [10, 20]},
            {'service': 'identity', 'ports': [30]},
        ]
        port_has_listener.return_value = False
        # Fail the identity service
        service_running.side_effect = [False, True]

        openstack.set_os_workload_status(
            configs, required_interfaces, services=services)
        status_set.assert_called_with(
            'blocked',
            "Services should be paused but these services running: identity")

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=True)
    def test_set_os_workload_status_paused_services_ports_fail(
            self, is_unit_paused_set, status_set, log,
            port_has_listener, service_running):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        services = [
            {'service': 'database', 'ports': [10, 20]},
            {'service': 'identity', 'ports': [30]},
        ]
        # make the service 20 port be still listening.
        port_has_listener.side_effect = [False, True, False]
        service_running.return_value = False

        openstack.set_os_workload_status(
            configs, required_interfaces, services=services)
        status_set.assert_called_with(
            'blocked',
            "Services should be paused but these service:ports are open:"
            " database: [20]")

    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=True)
    def test_set_os_workload_status_paused_ports_check(
            self, is_unit_paused_set, status_set, log,
            port_has_listener):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        ports = [50, 60, 70]
        port_has_listener.side_effect = [False, False, False]

        openstack.set_os_workload_status(
            configs, required_interfaces, ports=ports)
        status_set.assert_called_with(
            'maintenance',
            "Paused. Use 'resume' action to resume normal service.")

    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    @patch.object(openstack, 'juju_log')
    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.is_unit_paused_set',
           return_value=True)
    def test_set_os_workload_status_paused_ports_fail(
            self, is_unit_paused_set, status_set, log,
            port_has_listener):
        configs = MagicMock()
        configs.complete_contexts.return_value = []
        required_interfaces = {}

        # fail port 70 to make it seem to be running
        ports = [50, 60, 70]
        port_has_listener.side_effect = [False, False, True]

        openstack.set_os_workload_status(
            configs, required_interfaces, ports=ports)
        status_set.assert_called_with(
            'blocked',
            "Services should be paused but "
            "these ports which should be closed, but are open: 70")

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    def test_check_actually_paused_simple_services(
            self, port_has_listener, service_running):
        services = ['database', 'identity']
        port_has_listener.return_value = False
        service_running.return_value = False

        state, message = openstack.check_actually_paused(
            services)
        self.assertEquals(state, None)
        self.assertEquals(message, None)

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    def test_check_actually_paused_simple_services_fail(
            self, port_has_listener, service_running):
        services = ['database', 'identity']
        port_has_listener.return_value = False
        service_running.side_effect = [False, True]

        state, message = openstack.check_actually_paused(
            services)
        self.assertEquals(state, 'blocked')
        self.assertEquals(
            message,
            "Services should be paused but these services running: identity")

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    def test_check_actually_paused_services_dict(
            self, port_has_listener, service_running):
        services = [
            {'service': 'database', 'ports': [10, 20]},
            {'service': 'identity', 'ports': [30]},
        ]
        # Assume that the service and ports are open.
        port_has_listener.return_value = False
        service_running.return_value = False

        state, message = openstack.check_actually_paused(
            services)
        self.assertEquals(state, None)
        self.assertEquals(message, None)

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    def test_check_actually_paused_services_dict_fail(
            self, port_has_listener, service_running):
        services = [
            {'service': 'database', 'ports': [10, 20]},
            {'service': 'identity', 'ports': [30]},
        ]
        # Assume that the service and ports are open.
        port_has_listener.return_value = False
        service_running.side_effect = [False, True]

        state, message = openstack.check_actually_paused(
            services)
        self.assertEquals(state, 'blocked')
        self.assertEquals(
            message,
            "Services should be paused but these services running: identity")

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    def test_check_actually_paused_services_dict_ports_fail(
            self, port_has_listener, service_running):
        services = [
            {'service': 'database', 'ports': [10, 20]},
            {'service': 'identity', 'ports': [30]},
        ]
        # Assume that the service and ports are open.
        port_has_listener.side_effect = [False, True, False]
        service_running.return_value = False

        state, message = openstack.check_actually_paused(
            services)
        self.assertEquals(state, 'blocked')
        self.assertEquals(message,
                          'Services should be paused but these service:ports'
                          ' are open: database: [20]')

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    def test_check_actually_paused_ports_okay(
            self, port_has_listener, service_running):
        port_has_listener.side_effect = [False, False, False]
        service_running.return_value = False
        ports = [50, 60, 70]

        state, message = openstack.check_actually_paused(
            ports=ports)
        self.assertEquals(state, None)
        self.assertEquals(state, None)

    @patch('charmhelpers.contrib.openstack.utils.service_running')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    def test_check_actually_paused_ports_fail(
            self, port_has_listener, service_running):
        port_has_listener.side_effect = [False, True, False]
        service_running.return_value = False
        ports = [50, 60, 70]

        state, message = openstack.check_actually_paused(
            ports=ports)
        self.assertEquals(state, 'blocked')
        self.assertEquals(message,
                          'Services should be paused but these ports '
                          'which should be closed, but are open: 60')

    @staticmethod
    def _unit_paused_helper(hook_data_mock):
        # HookData()() returns a tuple (kv, delta_config, delta_relation)
        # but we only want kv in the test.
        kv = MagicMock()

        @contextlib.contextmanager
        def hook_data__call__():
            yield (kv, True, False)

        hook_data__call__.return_value = (kv, True, False)
        hook_data_mock.return_value = hook_data__call__
        return kv

    @patch('charmhelpers.contrib.openstack.utils.unitdata.HookData')
    def test_set_unit_paused(self, hook_data):
        kv = self._unit_paused_helper(hook_data)
        openstack.set_unit_paused()
        kv.set.assert_called_once_with('unit-paused', True)

    @patch('charmhelpers.contrib.openstack.utils.unitdata.HookData')
    def test_set_unit_upgrading(self, hook_data):
        kv = self._unit_paused_helper(hook_data)
        openstack.set_unit_upgrading()
        kv.set.assert_called_once_with('unit-upgrading', True)

    @patch('charmhelpers.contrib.openstack.utils.unitdata.HookData')
    def test_clear_unit_paused(self, hook_data):
        kv = self._unit_paused_helper(hook_data)
        openstack.clear_unit_paused()
        kv.set.assert_called_once_with('unit-paused', False)

    @patch('charmhelpers.contrib.openstack.utils.unitdata.HookData')
    def test_clear_unit_upgrading(self, hook_data):
        kv = self._unit_paused_helper(hook_data)
        openstack.clear_unit_upgrading()
        kv.set.assert_called_once_with('unit-upgrading', False)

    @patch('charmhelpers.contrib.openstack.utils.unitdata.HookData')
    def test_is_unit_paused_set(self, hook_data):
        kv = self._unit_paused_helper(hook_data)
        kv.get.return_value = True
        r = openstack.is_unit_paused_set()
        kv.get.assert_called_once_with('unit-paused')
        self.assertEquals(r, True)
        kv.get.return_value = False
        r = openstack.is_unit_paused_set()
        self.assertEquals(r, False)

    @patch('charmhelpers.contrib.openstack.utils.unitdata.HookData')
    def test_is_unit_upgrading_set(self, hook_data):
        kv = self._unit_paused_helper(hook_data)
        kv.get.return_value = True
        r = openstack.is_unit_upgrading_set()
        kv.get.assert_called_once_with('unit-upgrading')
        self.assertEquals(r, True)
        kv.get.return_value = False
        r = openstack.is_unit_upgrading_set()
        self.assertEquals(r, False)

    @patch.object(openstack, 'config')
    @patch.object(openstack, 'is_unit_paused_set')
    @patch.object(openstack.deferred_events, 'is_restart_permitted')
    @patch.object(openstack.deferred_events, 'set_deferred_hook')
    @patch.object(openstack.deferred_events, 'clear_deferred_hook')
    def test_is_hook_allowed(self, clear_deferred_hook, set_deferred_hook,
                             is_restart_permitted, is_unit_paused_set, config):
        # Test unit not paused and not checking whether restarts are allowed
        is_unit_paused_set.return_value = False
        self.assertEqual(
            openstack.is_hook_allowed(
                'config-changed',
                check_deferred_restarts=False),
            (True, ''))
        self.assertFalse(clear_deferred_hook.called)

        # Test unit paused and not checking whether restarts are allowed
        is_unit_paused_set.return_value = True
        self.assertEqual(
            openstack.is_hook_allowed(
                'config-changed',
                check_deferred_restarts=False),
            (False, 'Unit is pause or upgrading. Skipping config-changed'))

        # Test unit not paused and restarts allowed
        clear_deferred_hook.reset_mock()
        is_unit_paused_set.return_value = False
        is_restart_permitted.return_value = True
        self.assertEqual(
            openstack.is_hook_allowed(
                'config-changed',
                check_deferred_restarts=True),
            (True, ''))
        clear_deferred_hook.assert_called_once_with('config-changed')

        # Test unit not paused and restarts not allowed
        # enable-auto-restarts not enabled as part of this hook
        clear_deferred_hook.reset_mock()
        set_deferred_hook.reset_mock()
        is_unit_paused_set.return_value = False
        is_restart_permitted.return_value = False
        config().changed.return_value = False
        self.assertEqual(
            openstack.is_hook_allowed(
                'config-changed',
                check_deferred_restarts=True),
            (False, 'auto restarts are disabled'))
        self.assertFalse(clear_deferred_hook.called)
        set_deferred_hook.assert_called_once_with('config-changed')

        # Test unit not paused and restarts not allowed.
        # enable-auto-restarts enabled as part of this hook
        clear_deferred_hook.reset_mock()
        set_deferred_hook.reset_mock()
        is_unit_paused_set.return_value = False
        is_restart_permitted.return_value = False
        config().changed.return_value = True
        self.assertEqual(
            openstack.is_hook_allowed(
                'config-changed',
                check_deferred_restarts=True),
            (False, 'auto restarts are disabled'))
        self.assertFalse(clear_deferred_hook.called)

        # Test unit paused and restarts not allowed
        # enable-auto-restarts not enabled as part of this hook
        clear_deferred_hook.reset_mock()
        set_deferred_hook.reset_mock()
        is_unit_paused_set.return_value = True
        is_restart_permitted.return_value = False
        config().changed.return_value = False
        self.assertEqual(
            openstack.is_hook_allowed(
                'config-changed',
                check_deferred_restarts=True),
            (False, 'Unit is pause or upgrading. Skipping config-changed and '
                    'auto restarts are disabled'))
        self.assertFalse(clear_deferred_hook.called)
        set_deferred_hook.assert_called_once_with('config-changed')

    @patch('charmhelpers.contrib.openstack.utils.service_stop')
    def test_manage_payload_services_ok(self, service_stop):
        services = ['service1', 'service2']
        service_stop.side_effect = [True, True]
        self.assertEqual(
            openstack.manage_payload_services('stop', services=services),
            (True, []))

    @patch('charmhelpers.contrib.openstack.utils.service_stop')
    def test_manage_payload_services_fails(self, service_stop):
        services = ['service1', 'service2']
        service_stop.side_effect = [True, False]
        self.assertEqual(
            openstack.manage_payload_services('stop', services=services),
            (False, ["service2 didn't stop cleanly."]))

    @patch('charmhelpers.contrib.openstack.utils.service_stop')
    def test_manage_payload_services_charm_func(self, service_stop):
        bespoke_func = MagicMock()
        bespoke_func.return_value = None
        services = ['service1', 'service2']
        service_stop.side_effect = [True, True]
        self.assertEqual(
            openstack.manage_payload_services('stop', services=services,
                                              charm_func=bespoke_func),
            (True, []))
        bespoke_func.assert_called_once_with()

    @patch('charmhelpers.contrib.openstack.utils.service_stop')
    def test_manage_payload_services_charm_func_msg(self, service_stop):
        bespoke_func = MagicMock()
        bespoke_func.return_value = 'it worked'
        services = ['service1', 'service2']
        service_stop.side_effect = [True, True]
        self.assertEqual(
            openstack.manage_payload_services('stop', services=services,
                                              charm_func=bespoke_func),
            (True, ['it worked']))
        bespoke_func.assert_called_once_with()

    @patch('charmhelpers.contrib.openstack.utils.service_stop')
    def test_manage_payload_services_charm_func_fails(self, service_stop):
        bespoke_func = MagicMock()
        bespoke_func.side_effect = Exception('it failed')
        services = ['service1', 'service2']
        service_stop.side_effect = [True, True]
        self.assertEqual(
            openstack.manage_payload_services('stop', services=services,
                                              charm_func=bespoke_func),
            (False, ['it failed']))
        bespoke_func.assert_called_once_with()

    def test_manage_payload_services_wrong_action(self):
        self.assertRaises(
            RuntimeError,
            openstack.manage_payload_services,
            'mangle')

    @patch('charmhelpers.contrib.openstack.utils.service_pause')
    @patch('charmhelpers.contrib.openstack.utils.set_unit_paused')
    def test_pause_unit_okay(self, set_unit_paused, service_pause):
        services = ['service1', 'service2']
        service_pause.side_effect = [True, True]
        openstack.pause_unit(None, services=services)
        set_unit_paused.assert_called_once_with()
        self.assertEquals(service_pause.call_count, 2)

    @patch('charmhelpers.contrib.openstack.utils.service_pause')
    @patch('charmhelpers.contrib.openstack.utils.set_unit_paused')
    def test_pause_unit_service_fails(self, set_unit_paused, service_pause):
        services = ['service1', 'service2']
        service_pause.side_effect = [True, True]
        openstack.pause_unit(None, services=services)
        set_unit_paused.assert_called_once_with()
        self.assertEquals(service_pause.call_count, 2)
        # Fail the 2nd service
        service_pause.side_effect = [True, False]
        try:
            openstack.pause_unit(None, services=services)
            raise Exception("pause_unit should have raised Exception")
        except Exception as e:
            self.assertEquals(e.args[0],
                              "Couldn't pause: service2 didn't pause cleanly.")

    @patch('charmhelpers.contrib.openstack.utils.service_pause')
    @patch('charmhelpers.contrib.openstack.utils.set_unit_paused')
    def test_pause_unit_service_charm_func(
            self, set_unit_paused, service_pause):
        services = ['service1', 'service2']
        service_pause.return_value = True
        charm_func = MagicMock()
        charm_func.return_value = None
        openstack.pause_unit(None, services=services, charm_func=charm_func)
        charm_func.assert_called_once_with()
        # fail the charm_func
        charm_func.return_value = "Custom charm failed"
        try:
            openstack.pause_unit(
                None, services=services, charm_func=charm_func)
            raise Exception("pause_unit should have raised Exception")
        except Exception as e:
            self.assertEquals(e.args[0],
                              "Couldn't pause: Custom charm failed")

    @patch('charmhelpers.contrib.openstack.utils.service_pause')
    @patch('charmhelpers.contrib.openstack.utils.set_unit_paused')
    def test_pause_unit_assess_status_func(
            self, set_unit_paused, service_pause):
        services = ['service1', 'service2']
        service_pause.return_value = True
        assess_status_func = MagicMock()
        assess_status_func.return_value = None
        openstack.pause_unit(assess_status_func, services=services)
        assess_status_func.assert_called_once_with()
        # fail the assess_status_func
        assess_status_func.return_value = "assess_status_func failed"
        try:
            openstack.pause_unit(assess_status_func, services=services)
            raise Exception("pause_unit should have raised Exception")
        except Exception as e:
            self.assertEquals(e.args[0],
                              "Couldn't pause: assess_status_func failed")

    @patch('charmhelpers.contrib.openstack.utils.service_pause')
    @patch('charmhelpers.contrib.openstack.utils.set_unit_paused')
    @patch('charmhelpers.contrib.openstack.utils.port_has_listener')
    def test_pause_unit_retry_port_check_retries(
            self, port_has_listener, set_unit_paused, service_pause):
        service_pause.return_value = True
        port_has_listener.side_effect = [True, False]
        wait_for_ports_func = openstack.make_wait_for_ports_barrier([77])
        openstack.pause_unit(None, services=['service1'], ports=[77], charm_func=wait_for_ports_func)
        port_has_listener.assert_has_calls([call('0.0.0.0', 77), call('0.0.0.0', 77)])

    @patch('charmhelpers.contrib.openstack.utils.service_resume')
    @patch('charmhelpers.contrib.openstack.utils.clear_unit_paused')
    def test_resume_unit_okay(self, clear_unit_paused, service_resume):
        services = ['service1', 'service2']
        service_resume.side_effect = [True, True]
        openstack.resume_unit(None, services=services)
        clear_unit_paused.assert_called_once_with()
        self.assertEquals(service_resume.call_count, 2)

    @patch('charmhelpers.contrib.openstack.utils.service_resume')
    @patch('charmhelpers.contrib.openstack.utils.clear_unit_paused')
    def test_resume_unit_service_fails(
            self, clear_unit_paused, service_resume):
        services = ['service1', 'service2']
        service_resume.side_effect = [True, True]
        openstack.resume_unit(None, services=services)
        clear_unit_paused.assert_called_once_with()
        self.assertEquals(service_resume.call_count, 2)
        # Fail the 2nd service
        service_resume.side_effect = [True, False]
        try:
            openstack.resume_unit(None, services=services)
            raise Exception("resume_unit should have raised Exception")
        except Exception as e:
            self.assertEquals(
                e.args[0], "Couldn't resume: service2 didn't resume cleanly.")

    @patch('charmhelpers.contrib.openstack.utils.service_resume')
    @patch('charmhelpers.contrib.openstack.utils.clear_unit_paused')
    def test_resume_unit_service_charm_func(
            self, clear_unit_paused, service_resume):
        services = ['service1', 'service2']
        service_resume.return_value = True
        charm_func = MagicMock()
        charm_func.return_value = None
        openstack.resume_unit(None, services=services, charm_func=charm_func)
        charm_func.assert_called_once_with()
        # fail the charm_func
        charm_func.return_value = "Custom charm failed"
        try:
            openstack.resume_unit(
                None, services=services, charm_func=charm_func)
            raise Exception("resume_unit should have raised Exception")
        except Exception as e:
            self.assertEquals(e.args[0],
                              "Couldn't resume: Custom charm failed")

    @patch('charmhelpers.contrib.openstack.utils.service_resume')
    @patch('charmhelpers.contrib.openstack.utils.clear_unit_paused')
    def test_resume_unit_assess_status_func(
            self, clear_unit_paused, service_resume):
        services = ['service1', 'service2']
        service_resume.return_value = True
        assess_status_func = MagicMock()
        assess_status_func.return_value = None
        openstack.resume_unit(assess_status_func, services=services)
        assess_status_func.assert_called_once_with()
        # fail the assess_status_func
        assess_status_func.return_value = "assess_status_func failed"
        try:
            openstack.resume_unit(assess_status_func, services=services)
            raise Exception("resume_unit should have raised Exception")
        except Exception as e:
            self.assertEquals(e.args[0],
                              "Couldn't resume: assess_status_func failed")

    @patch('charmhelpers.contrib.openstack.utils.status_set')
    @patch('charmhelpers.contrib.openstack.utils.'
           '_determine_os_workload_status')
    def test_make_assess_status_func(self, _determine_os_workload_status,
                                     status_set):
        _determine_os_workload_status.return_value = ('active', 'fine')
        f = openstack.make_assess_status_func('one', 'two', three='three')
        r = f()
        self.assertEquals(r, None)
        _determine_os_workload_status.assert_called_once_with(
            'one', 'two', three='three')
        status_set.assert_called_once_with('active', 'fine')
        # return something other than 'active' or 'maintenance'
        _determine_os_workload_status.return_value = ('broken', 'damaged')
        r = f()
        self.assertEquals(r, 'damaged')

    # TODO(ajkavanagh) -- there should be a test for
    # _determine_os_workload_status() as the policyd override code has changed
    # it, but there wasn't a test previously.

    @patch.object(openstack, 'restart_on_change_helper')
    @patch.object(openstack, 'is_unit_paused_set')
    def test_pausable_restart_on_change(
            self, is_unit_paused_set, restart_on_change_helper):
        @openstack.pausable_restart_on_change({})
        def test_func():
            pass

        # test with pause: restart_on_change_helper should not be called.
        is_unit_paused_set.return_value = True
        test_func()
        self.assertEquals(restart_on_change_helper.call_count, 0)

        # test without pause: restart_on_change_helper should be called.
        is_unit_paused_set.return_value = False
        test_func()
        self.assertEquals(restart_on_change_helper.call_count, 1)

    @patch.object(openstack, 'restart_on_change_helper')
    @patch.object(openstack, 'is_unit_paused_set')
    def test_pausable_restart_on_change_with_callable(
            self, is_unit_paused_set, restart_on_change_helper):
        mock_test = MagicMock()
        mock_test.called_set = False

        def _restart_map():
            mock_test.called_set = True
            return {"a": "b"}

        @openstack.pausable_restart_on_change(_restart_map)
        def test_func():
            pass

        self.assertFalse(mock_test.called_set)
        is_unit_paused_set.return_value = False
        test_func()
        self.assertEquals(restart_on_change_helper.call_count, 1)
        self.assertTrue(mock_test.called_set)

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'action_set')
    @patch.object(openstack, 'action_fail')
    @patch.object(openstack, 'openstack_upgrade_available')
    @patch('charmhelpers.contrib.openstack.utils.config')
    def test_openstack_upgrade(self, config, openstack_upgrade_available,
                               action_fail, action_set, log):
        def do_openstack_upgrade(configs):
            pass

        openstack_upgrade_available.return_value = True

        # action-managed-upgrade=True
        config.side_effect = [True]

        openstack.do_action_openstack_upgrade('package-xyz',
                                              do_openstack_upgrade,
                                              None)

        self.assertTrue(openstack_upgrade_available.called)
        msg = ('success, upgrade completed.')
        action_set.assert_called_with({'outcome': msg})
        self.assertFalse(action_fail.called)

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'action_set')
    @patch.object(openstack, 'action_fail')
    @patch.object(openstack, 'openstack_upgrade_available')
    @patch('charmhelpers.contrib.openstack.utils.config')
    def test_openstack_upgrade_not_avail(self, config,
                                         openstack_upgrade_available,
                                         action_fail, action_set, log):
        def do_openstack_upgrade(configs):
            pass

        openstack_upgrade_available.return_value = False

        openstack.do_action_openstack_upgrade('package-xyz',
                                              do_openstack_upgrade,
                                              None)

        self.assertTrue(openstack_upgrade_available.called)
        msg = ('no upgrade available.')
        action_set.assert_called_with({'outcome': msg})
        self.assertFalse(action_fail.called)

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'action_set')
    @patch.object(openstack, 'action_fail')
    @patch.object(openstack, 'openstack_upgrade_available')
    @patch('charmhelpers.contrib.openstack.utils.config')
    def test_openstack_upgrade_config_false(self, config,
                                            openstack_upgrade_available,
                                            action_fail, action_set, log):
        def do_openstack_upgrade(configs):
            pass

        openstack_upgrade_available.return_value = True

        # action-managed-upgrade=False
        config.side_effect = [False]

        openstack.do_action_openstack_upgrade('package-xyz',
                                              do_openstack_upgrade,
                                              None)

        self.assertTrue(openstack_upgrade_available.called)
        msg = ('action-managed-upgrade config is False, skipped upgrade.')
        action_set.assert_called_with({'outcome': msg})
        self.assertFalse(action_fail.called)

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'action_set')
    @patch.object(openstack, 'action_fail')
    @patch.object(openstack, 'openstack_upgrade_available')
    @patch('traceback.format_exc')
    @patch('charmhelpers.contrib.openstack.utils.config')
    def test_openstack_upgrade_traceback(self, config, traceback,
                                         openstack_upgrade_available,
                                         action_fail, action_set, log):
        def do_openstack_upgrade(configs):
            oops()  # noqa

        openstack_upgrade_available.return_value = True

        # action-managed-upgrade=False
        config.side_effect = [True]

        openstack.do_action_openstack_upgrade('package-xyz',
                                              do_openstack_upgrade,
                                              None)

        self.assertTrue(openstack_upgrade_available.called)
        msg = 'do_openstack_upgrade resulted in an unexpected error'
        action_fail.assert_called_with(msg)
        self.assertTrue(action_set.called)
        self.assertTrue(traceback.called)

    @patch.object(openstack, 'os_release')
    @patch.object(openstack, 'application_version_set')
    def test_os_application_version_set(self,
                                        mock_application_version_set,
                                        mock_os_release):
        with patch.object(fetch, 'apt_cache') as cache:
            cache.return_value = self._apt_cache()
            mock_os_release.return_value = 'mitaka'
            openstack.os_application_version_set('neutron-common')
            mock_application_version_set.assert_called_with('7.0.1')
            openstack.os_application_version_set('cinder-common')
            mock_application_version_set.assert_called_with('mitaka')

    @patch.object(openstack, 'valid_snap_channel')
    @patch('charmhelpers.contrib.openstack.utils.config')
    def test_snap_install_requested(self, config, valid_snap_channel):
        valid_snap_channel.return_value = True
        # Expect True
        flush('snap_install_requested')
        config.return_value = 'snap:ocata/edge'
        self.assertTrue(openstack.snap_install_requested())
        valid_snap_channel.assert_called_with('edge')
        flush('snap_install_requested')
        config.return_value = 'snap:pike'
        self.assertTrue(openstack.snap_install_requested())
        valid_snap_channel.assert_called_with('stable')
        flush('snap_install_requested')
        config.return_value = 'snap:pike/stable/jamespage'
        self.assertTrue(openstack.snap_install_requested())
        valid_snap_channel.assert_called_with('stable')
        # Expect False
        flush('snap_install_requested')
        config.return_value = 'cloud:xenial-ocata'
        self.assertFalse(openstack.snap_install_requested())

    def test_get_snaps_install_info_from_origin(self):
        snaps = ['os_project']
        mode = 'jailmode'

        # snap:track/channel
        src = 'snap:ocata/beta'
        expected = {snaps[0]: {'mode': mode,
                               'channel': '--channel=ocata/beta'}}
        self.assertEqual(
            expected,
            openstack.get_snaps_install_info_from_origin(snaps, src,
                                                         mode=mode))

        # snap:track/channel/branch
        src = 'snap:ocata/beta/jamespage'
        expected = {snaps[0]: {'mode': mode,
                               'channel': '--channel=ocata/beta/jamespage'}}
        self.assertEqual(
            expected,
            openstack.get_snaps_install_info_from_origin(snaps, src,
                                                         mode=mode))
        # snap:track
        src = 'snap:pike'
        expected = {snaps[0]: {'mode': mode,
                               'channel': '--channel=pike'}}
        self.assertEqual(
            expected,
            openstack.get_snaps_install_info_from_origin(snaps, src,
                                                         mode=mode))

    @patch.object(openstack, 'snap_install')
    def test_install_os_snaps(self, mock_snap_install):
        snaps = ['os_project']
        mode = 'jailmode'

        # snap:track/channel
        src = 'snap:ocata/beta'
        openstack.install_os_snaps(
            openstack.get_snaps_install_info_from_origin(
                snaps, src, mode=mode))
        mock_snap_install.assert_called_with(
            'os_project', '--channel=ocata/beta', '--jailmode')

        # snap:track
        src = 'snap:pike'
        openstack.install_os_snaps(
            openstack.get_snaps_install_info_from_origin(
                snaps, src, mode=mode))
        mock_snap_install.assert_called_with(
            'os_project', '--channel=pike', '--jailmode')

    @patch.object(openstack, 'set_unit_upgrading')
    @patch.object(openstack, 'is_unit_paused_set')
    def test_series_upgrade_prepare(
            self, is_unit_paused_set, set_unit_upgrading):
        is_unit_paused_set.return_value = False
        fake_pause_helper = MagicMock()
        fake_configs = MagicMock()
        openstack.series_upgrade_prepare(fake_pause_helper, fake_configs)
        set_unit_upgrading.assert_called_once()
        fake_pause_helper.assert_called_once_with(fake_configs)

    @patch.object(openstack, 'set_unit_upgrading')
    @patch.object(openstack, 'is_unit_paused_set')
    def test_series_upgrade_prepare_no_pause(
            self, is_unit_paused_set, set_unit_upgrading):
        is_unit_paused_set.return_value = True
        fake_pause_helper = MagicMock()
        fake_configs = MagicMock()
        openstack.series_upgrade_prepare(fake_pause_helper, fake_configs)
        set_unit_upgrading.assert_called_once()
        fake_pause_helper.assert_not_called()

    @patch.object(openstack, 'clear_unit_upgrading')
    @patch.object(openstack, 'clear_unit_paused')
    def test_series_upgrade_complete(
            self, clear_unit_paused, clear_unit_upgrading):
        fake_resume_helper = MagicMock()
        fake_configs = MagicMock()
        openstack.series_upgrade_complete(fake_resume_helper, fake_configs)
        clear_unit_upgrading.assert_called_once()
        clear_unit_paused.assert_called_once()
        fake_configs.write_all.assert_called_once()
        fake_resume_helper.assert_called_once_with(fake_configs)

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'leader_get')
    def test_is_db_initialised(self, leader_get, juju_log):
        leader_get.return_value = 'True'
        self.assertTrue(openstack.is_db_initialised())
        leader_get.return_value = 'False'
        self.assertFalse(openstack.is_db_initialised())
        leader_get.return_value = None
        self.assertFalse(openstack.is_db_initialised())

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'leader_set')
    def test_set_db_initialised(self, leader_set, juju_log):
        openstack.set_db_initialised()
        leader_set.assert_called_once_with({'db-initialised': True})

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'relation_ids')
    @patch.object(openstack, 'related_units')
    @patch.object(openstack, 'relation_get')
    def test_is_db_maintenance_mode(self, relation_get, related_units,
                                    relation_ids, juju_log):
        relation_ids.return_value = ['rid:1']
        related_units.return_value = ['unit/0', 'unit/2']
        rsettings = {
            'rid:1': {
                'unit/0': {
                    'private-ip': '1.2.3.4',
                    'cluster-series-upgrading': 'True'},
                'unit/2': {
                    'private-ip': '1.2.3.5'}}}
        relation_get.side_effect = lambda unit, rid: rsettings[rid][unit]
        self.assertTrue(openstack.is_db_maintenance_mode())
        rsettings = {
            'rid:1': {
                'unit/0': {
                    'private-ip': '1.2.3.4'},
                'unit/2': {
                    'private-ip': '1.2.3.5'}}}
        self.assertFalse(openstack.is_db_maintenance_mode())
        rsettings = {
            'rid:1': {
                'unit/0': {
                    'private-ip': '1.2.3.4',
                    'cluster-series-upgrading': 'False'},
                'unit/2': {
                    'private-ip': '1.2.3.5'}}}
        self.assertFalse(openstack.is_db_maintenance_mode())
        rsettings = {
            'rid:1': {
                'unit/0': {
                    'private-ip': '1.2.3.4',
                    'cluster-series-upgrading': 'lskjfsd'},
                'unit/2': {
                    'private-ip': '1.2.3.5'}}}
        self.assertFalse(openstack.is_db_maintenance_mode())

    def test_get_endpoint_key(self):
        self.assertEqual(
            openstack.get_endpoint_key('placement', 'is:2', 'keystone/0'),
            'placement-is_2-keystone_0')

    @patch.object(openstack, 'relation_get')
    @patch.object(openstack, 'related_units')
    @patch.object(openstack, 'relation_ids')
    def test_get_endpoint_notifications(self, relation_ids, related_units,
                                        relation_get):
        id_svc_rel_units = {
            'identity-service:3': ['keystone/0', 'keystone/1', 'keystone/2']
        }

        def _related_units(relid):
            return id_svc_rel_units[relid]

        id_svc_rel_data = {
            'keystone/0': {
                'ep_changed': '{"placement": "d5c3"}'},
            'keystone/1': {
                'ep_changed': '{"nova": "4d06", "neutron": "2aa6"}'},
            'keystone/2': {}}

        def _relation_get(unit, rid, attribute):
            return id_svc_rel_data[unit].get(attribute)

        relation_ids.return_value = id_svc_rel_units.keys()
        related_units.side_effect = _related_units
        relation_get.side_effect = _relation_get
        self.assertEqual(
            openstack.get_endpoint_notifications(['neutron']),
            {
                'neutron-identity-service_3-keystone_1': '2aa6'})
        self.assertEqual(
            openstack.get_endpoint_notifications(['placement', 'neutron']),
            {
                'neutron-identity-service_3-keystone_1': '2aa6',
                'placement-identity-service_3-keystone_0': 'd5c3'})

    @patch.object(openstack, 'get_endpoint_notifications')
    @patch.object(openstack.unitdata, 'HookData')
    def test_endpoint_changed(self, HookData, get_endpoint_notifications):
        self.kv_data = {}

        def _kv_get(key):
            return self.kv_data.get(key)
        kv = self._unit_paused_helper(HookData)
        kv.get.side_effect = _kv_get
        # Check endpoint_changed returns True when there are new notifications.
        get_endpoint_notifications.return_value = {
            'neutron-identity-service_3-keystone_1': '2aa6',
            'placement-identity-service_3-keystone_0': 'd5c3'}
        self.assertTrue(openstack.endpoint_changed('placement'))
        # Check endpoint_changed returns False when there are new
        # notifications but they are not the ones being looked for.
        self.assertTrue(openstack.endpoint_changed('nova'))
        # Check endpoint_changed returns False if the notification
        # has already been seen
        get_endpoint_notifications.return_value = {
            'placement-identity-service_3-keystone_0': 'd5c3'}
        self.kv_data = {
            'placement-identity-service_3-keystone_0': 'd5c3'}
        self.assertFalse(openstack.endpoint_changed('placement'))

    @patch.object(openstack, 'get_endpoint_notifications')
    @patch.object(openstack.unitdata, 'HookData')
    def test_save_endpoint_changed_triggers(self, HookData,
                                            get_endpoint_notifications):
        kv = self._unit_paused_helper(HookData)
        get_endpoint_notifications.return_value = {
            'neutron-identity-service_3-keystone_1': '2aa6',
            'placement-identity-service_3-keystone_0': 'd5c3'}
        openstack.save_endpoint_changed_triggers(['neutron', 'placement'])
        kv_set_calls = [
            call('neutron-identity-service_3-keystone_1', '2aa6'),
            call('placement-identity-service_3-keystone_0', 'd5c3')]
        kv.set.assert_has_calls(kv_set_calls, any_order=True)


class OpenStackUtilsAdditionalTests(TestCase):
    SHARED_DB_RELATIONS = {
        'shared-db:8': {
            'mysql-svc1/0': {
                'allowed_units': 'client/0',
            },
            'mysql-svc1/1': {},
            'mysql-svc1/2': {
                'allowed_units': 'client/0 client/1',
            },
        },
        'shared-db:12': {
            'mysql-svc2/0': {
                'allowed_units': 'client/1',
            },
            'mysql-svc2/1': {
                'allowed_units': 'client/3',
            },
            'mysql-svc2/2': {
                'allowed_units': {},
            },
        }
    }
    SCALE_RELATIONS = {
        'cluster:2': {
            'keystone/1': {},
            'keystone/2': {}},
        'shared-db:12': {
            'mysql-svc2/0': {
                'allowed_units': 'client/1',
            },
            'mysql-svc2/1': {
                'allowed_units': 'client/3',
            },
            'mysql-svc2/2': {
                'allowed_units': {},
            }},
    }
    SCALE_RELATIONS_HA = {
        'cluster:2': {
            'keystone/1': {'unit-state-keystone-1': 'READY'},
            'keystone/2': {}},
        'shared-db:12': {
            'mysql-svc2/0': {
                'allowed_units': 'client/1',
            },
            'mysql-svc2/1': {
                'allowed_units': 'client/3',
            },
            'mysql-svc2/2': {
                'allowed_units': {},
            }},
        'ha:32': {
            'hacluster-keystone/1': {}}
    }
    All_PEERS_READY = {
        'cluster:2': {
            'keystone/1': {'unit-state-keystone-1': 'READY'},
            'keystone/2': {'unit-state-keystone-2': 'READY'}}}
    PEERS_NOT_READY = {
        'cluster:2': {
            'keystone/1': {'unit-state-keystone-1': 'READY'},
            'keystone/2': {}}}

    def setUp(self):
        super(OpenStackUtilsAdditionalTests, self).setUp()
        [self._patch(m) for m in [
            'expect_ha',
            'expected_peer_units',
            'expected_related_units',
            'juju_log',
            'metadata',
            'related_units',
            'relation_get',
            'relation_id',
            'relation_ids',
            'relation_set',
            'local_unit',
        ]]

    def _patch(self, method):
        _m = patch.object(openstack, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def setup_relation(self, relation_map):
        relation = FakeRelation(relation_map)
        self.relation_id.side_effect = relation.relation_id
        self.relation_get.side_effect = relation.get
        self.relation_ids.side_effect = relation.relation_ids
        self.related_units.side_effect = relation.related_units
        return relation

    def test_is_db_ready(self):
        relation = self.setup_relation(self.SHARED_DB_RELATIONS)

        # Check unit allowed in 1st relation
        self.local_unit.return_value = 'client/0'
        self.assertTrue(openstack.is_db_ready())

        # Check unit allowed in 2nd relation
        self.local_unit.return_value = 'client/3'
        self.assertTrue(openstack.is_db_ready())

        # Check unit not allowed in any list
        self.local_unit.return_value = 'client/5'
        self.assertFalse(openstack.is_db_ready())

        # Check call with an invalid relation
        self.local_unit.return_value = 'client/3'
        # None returned if not in a relation context (eg update-status)
        relation.clear_relation_context()
        self.assertRaises(
            Exception,
            openstack.is_db_ready,
            use_current_context=True)

        # Check unit allowed using current relation context
        relation.set_relation_context('mysql-svc2/0', 'shared-db:12')
        self.local_unit.return_value = 'client/1'
        self.assertTrue(openstack.is_db_ready(use_current_context=True))

        # Check unit not allowed using current relation context
        relation.set_relation_context('mysql-svc2/0', 'shared-db:12')
        self.local_unit.return_value = 'client/0'
        self.assertFalse(openstack.is_db_ready(use_current_context=True))

    @patch.object(openstack, 'container_scoped_relations')
    def test_is_expected_scale_noha(self, container_scoped_relations):
        self.setup_relation(self.SCALE_RELATIONS)
        self.expect_ha.return_value = False
        eru = {
            'shared-db': ['mysql/0', 'mysql/1', 'mysql/2']}

        def _expected_related_units(reltype):
            return eru[reltype]
        self.expected_related_units.side_effect = _expected_related_units
        container_scoped_relations.return_value = ['ha', 'domain-backend']

        # All peer and db units are present
        self.expected_peer_units.return_value = ['keystone/0', 'keystone/2']
        self.assertTrue(openstack.is_expected_scale())

        # db units are present but a peer is missing
        self.expected_peer_units.return_value = ['keystone/0', 'keystone/2', 'keystone/3']
        self.assertFalse(openstack.is_expected_scale())

        # peer units are present but a db unit is missing
        eru['shared-db'].append('mysql/3')
        self.expected_peer_units.return_value = ['keystone/0', 'keystone/2']
        self.assertFalse(openstack.is_expected_scale())
        eru['shared-db'].remove('mysql/3')

        # Expect ha but ha unit is missing
        self.expect_ha.return_value = True
        self.expected_peer_units.return_value = ['keystone/0', 'keystone/2']
        self.assertFalse(openstack.is_expected_scale())

    @patch.object(openstack, 'container_scoped_relations')
    def test_is_expected_scale_ha(self, container_scoped_relations):
        self.setup_relation(self.SCALE_RELATIONS_HA)
        eru = {
            'shared-db': ['mysql/0', 'mysql/1', 'mysql/2']}

        def _expected_related_units(reltype):
            return eru[reltype]
        self.expected_related_units.side_effect = _expected_related_units
        container_scoped_relations.return_value = ['ha', 'domain-backend']
        self.expect_ha.return_value = True
        self.expected_peer_units.return_value = ['keystone/0', 'keystone/2']
        self.assertTrue(openstack.is_expected_scale())

    def test_container_scoped_relations(self):
        _metadata = {
            'provides': {
                'amqp': {'interface': 'rabbitmq'},
                'identity-service': {'interface': 'keystone'},
                'ha': {
                    'interface': 'hacluster',
                    'scope': 'container'}},
            'peers': {
                'cluster': {'interface': 'openstack-ha'}}}
        self.metadata.return_value = _metadata
        self.assertEqual(openstack.container_scoped_relations(), ['ha'])

    def test_get_peer_key(self):
        self.assertEqual(
            openstack.get_peer_key('cinder/0'),
            'unit-state-cinder-0')

    def test_inform_peers_unit_state(self):
        self.local_unit.return_value = 'client/0'
        self.setup_relation(self.All_PEERS_READY)
        openstack.inform_peers_unit_state('READY')
        self.relation_set.assert_called_once_with(
            relation_id='cluster:2',
            relation_settings={'unit-state-client-0': 'READY'})

    def test_get_peers_unit_state(self):
        self.setup_relation(self.All_PEERS_READY)
        self.assertEqual(
            openstack.get_peers_unit_state(),
            {'keystone/1': 'READY', 'keystone/2': 'READY'})
        self.setup_relation(self.PEERS_NOT_READY)
        self.assertEqual(
            openstack.get_peers_unit_state(),
            {'keystone/1': 'READY', 'keystone/2': 'UNKNOWN'})

    def test_are_peers_ready(self):
        self.setup_relation(self.All_PEERS_READY)
        self.assertTrue(openstack.are_peers_ready())
        self.setup_relation(self.PEERS_NOT_READY)
        self.assertFalse(openstack.are_peers_ready())

    @patch.object(openstack, 'inform_peers_unit_state')
    def test_inform_peers_if_ready(self, inform_peers_unit_state):
        self.setup_relation(self.All_PEERS_READY)

        def _not_ready():
            return False, "Its all gone wrong"

        def _ready():
            return True, "Hurray!"
        openstack.inform_peers_if_ready(_not_ready)
        inform_peers_unit_state.assert_called_once_with('NOTREADY', 'cluster')
        inform_peers_unit_state.reset_mock()
        openstack.inform_peers_if_ready(_ready)
        inform_peers_unit_state.assert_called_once_with('READY', 'cluster')

    @patch.object(openstack, 'is_expected_scale')
    @patch.object(openstack, 'is_db_initialised')
    @patch.object(openstack, 'is_db_ready')
    @patch.object(openstack, 'is_unit_paused_set')
    @patch.object(openstack, 'is_db_maintenance_mode')
    def test_check_api_unit_ready(self, is_db_maintenance_mode,
                                  is_unit_paused_set, is_db_ready,
                                  is_db_initialised, is_expected_scale):
        is_db_maintenance_mode.return_value = True
        self.assertFalse(openstack.check_api_unit_ready()[0])

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = True
        self.assertFalse(openstack.check_api_unit_ready()[0])

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = False
        is_db_ready.return_value = False
        self.assertFalse(openstack.check_api_unit_ready()[0])

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = False
        is_db_ready.return_value = True
        is_db_initialised.return_value = False
        self.assertFalse(openstack.check_api_unit_ready()[0])

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = False
        is_db_ready.return_value = True
        is_db_initialised.return_value = True
        is_expected_scale.return_value = False
        self.assertFalse(openstack.check_api_unit_ready()[0])

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = False
        is_db_ready.return_value = True
        is_db_initialised.return_value = True
        is_expected_scale.return_value = True
        self.assertTrue(openstack.check_api_unit_ready()[0])

    @patch.object(openstack, 'is_expected_scale')
    @patch.object(openstack, 'is_db_initialised')
    @patch.object(openstack, 'is_db_ready')
    @patch.object(openstack, 'is_unit_paused_set')
    @patch.object(openstack, 'is_db_maintenance_mode')
    def test_get_api_unit_status(self, is_db_maintenance_mode,
                                 is_unit_paused_set, is_db_ready,
                                 is_db_initialised, is_expected_scale):
        is_db_maintenance_mode.return_value = True
        self.assertEqual(
            openstack.get_api_unit_status()[0].value,
            'maintenance')

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = True
        self.assertEqual(
            openstack.get_api_unit_status()[0].value,
            'blocked')

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = False
        is_db_ready.return_value = False
        self.assertEqual(
            openstack.get_api_unit_status()[0].value,
            'waiting')

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = False
        is_db_ready.return_value = True
        is_db_initialised.return_value = False
        self.assertEqual(
            openstack.get_api_unit_status()[0].value,
            'waiting')

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = False
        is_db_ready.return_value = True
        is_db_initialised.return_value = True
        is_expected_scale.return_value = False
        self.assertEqual(
            openstack.get_api_unit_status()[0].value,
            'waiting')

        is_db_maintenance_mode.return_value = False
        is_unit_paused_set.return_value = False
        is_db_ready.return_value = True
        is_db_initialised.return_value = True
        is_expected_scale.return_value = True
        self.assertEqual(
            openstack.get_api_unit_status()[0].value,
            'active')

    @patch.object(openstack, 'get_api_unit_status')
    def test_check_api_application_ready(self, get_api_unit_status):
        get_api_unit_status.return_value = (WORKLOAD_STATES.ACTIVE, 'Hurray')
        self.assertTrue(openstack.check_api_application_ready()[0])
        get_api_unit_status.return_value = (WORKLOAD_STATES.BLOCKED, ':-(')
        self.assertFalse(openstack.check_api_application_ready()[0])

    @patch.object(openstack, 'get_api_unit_status')
    def test_get_api_application_status(self, get_api_unit_status):
        get_api_unit_status.return_value = (WORKLOAD_STATES.ACTIVE, 'Hurray')
        self.assertEqual(
            openstack.get_api_application_status()[0].value,
            'active')
        get_api_unit_status.return_value = (WORKLOAD_STATES.BLOCKED, ':-(')
        self.assertEqual(
            openstack.get_api_application_status()[0].value,
            'blocked')

    @patch.object(openstack.deferred_events, 'clear_deferred_restarts')
    @patch.object(openstack, 'manage_payload_services')
    @patch.object(openstack.deferred_events, 'get_deferred_restarts')
    def test_restart_services_action(self, get_deferred_restarts,
                                     manage_payload_services,
                                     clear_deferred_restarts):
        deferred_restarts = [
            deferred_events.ServiceEvent(
                timestamp=123,
                service='svcA',
                reason='ReasonA',
                action='restart')]
        get_deferred_restarts.return_value = deferred_restarts
        manage_payload_services.return_value = (None, None)
        openstack.restart_services_action(deferred_only=True)
        manage_payload_services.assert_has_calls([
            call('stop', services=['svcA'], charm_func=None),
            call('start', services=['svcA'])])
        clear_deferred_restarts.assert_called_once_with(['svcA'])
        self.assertRaises(
            ValueError,
            openstack.restart_services_action,
            ['svcA'],
            deferred_only=True)

        manage_payload_services.return_value = (None, 'something went wrong')
        self.assertRaises(
            ServiceActionError,
            openstack.restart_services_action,
            ['svcA'])


if __name__ == '__main__':
    unittest.main()
