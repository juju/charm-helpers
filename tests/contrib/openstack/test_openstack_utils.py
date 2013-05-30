from copy import copy
import os
import apt_pkg
import unittest
from testtools import TestCase
from io import BytesIO
import charmhelpers.contrib.openstack.openstack_utils as openstack
import subprocess

from mock import MagicMock, patch, Mock, call

# mocked return of openstack.lsb_release()
FAKE_RELEASE = {
    'DISTRIB_CODENAME': 'precise',
    'DISTRIB_RELEASE': '12.04',
    'DISTRIB_ID': 'Ubuntu',
    'DISTRIB_DESCRIPTION': '"Ubuntu 12.04"'
}

FAKE_REPO = {
    'nova-common': {
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
    'swift-proxy': {
        'pkg_vers': '1.7.7-0ubuntu1',
        'os_release': 'grizzly',
        'os_version': '1.7.7'
    },
    'cinder-common': {
        'pkg_vers': '1:2013.2-0ubuntu1~cloud0',
        'os_release': 'havana',
        'os_version': '2013.2'
    },
    'bad-version': {
        'pkg_vers': '1:2016.1-0ubuntu1.1~cloud0',
        'os_release': None,
        'os_version': None
    }
}


url = 'deb ' + openstack.CLOUD_ARCHIVE_URL
UCA_SOURCES = [
    ('cloud:precise-folsom/proposed', url + ' precise-proposed/folsom main'),
    ('cloud:precise-folsom', url + ' precise-updates/folsom main'),
    ('cloud:precise-folsom/updates', url + ' precise-updates/folsom main'),
    ('cloud:precise-grizzly/proposed', url + ' precise-proposed/grizzly main'),
    ('cloud:precise-grizzly', url + ' precise-updates/grizzly main'),
    ('cloud:precise-grizzly/updates',  url +  ' precise-updates/grizzly main'),
]

class OpenStackHelpersTestCase(TestCase):
    def _apt_cache(self):
        # mocks out the apt cache
        def cache_get(package):
            pkg = MagicMock()
            if package in FAKE_REPO:
                pkg.name = package
                pkg.current_ver.ver_str = FAKE_REPO[package]['pkg_vers']
            else:
                raise
            return pkg
        cache = MagicMock()
        cache.__getitem__.side_effect = cache_get
        return cache

    @patch('charmhelpers.contrib.openstack.openstack_utils.lsb_release')
    def test_os_codename_from_install_source(self, mocked_lsb):
        '''Test mapping install source to OpenStack release name'''
        mocked_lsb.return_value = FAKE_RELEASE

        # the openstack release shipped with respective ubuntu/lsb release.
        self.assertEquals(openstack.get_os_codename_install_source('distro'),
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

    @patch('charmhelpers.contrib.openstack.openstack_utils.lsb_release')
    def test_os_codename_from_bad_install_source(self, mocked_lsb):
        '''Test mapping install source to OpenStack release name'''
        _fake_release = copy(FAKE_RELEASE)
        _fake_release['DISTRIB_CODENAME'] = 'natty'

        mocked_lsb.return_value = _fake_release
        _e = 'charmhelpers.contrib.openstack.openstack_utils.error_out'
        with patch(_e) as mocked_err:
            openstack.get_os_codename_install_source('distro')
            _er = ('Could not derive openstack release for this Ubuntu '
                   'release: natty')
            mocked_err.assert_called_with(_er)

    def test_os_codename_from_version(self):
        '''Test mapping OpenStack numerical versions to code name'''
        self.assertEquals(openstack.get_os_codename_version('2013.1'),
                          'grizzly')

    @patch('charmhelpers.contrib.openstack.openstack_utils.error_out')
    def test_os_codename_from_bad_version(self, mocked_error):
        '''Test mapping a bad OpenStack numerical versions to code name'''
        openstack.get_os_codename_version('2014.5.5')
        expected_err = ('Could not determine OpenStack codename for '
                        'version 2014.5.5')
        mocked_error.assert_called_with(expected_err)

    def test_os_version_from_codename(self):
        '''Test mapping a OpenStack codename to numerical version'''
        self.assertEquals(openstack.get_os_version_codename('folsom'),
                          '2012.2')

    @patch('charmhelpers.contrib.openstack.openstack_utils.error_out')
    def test_os_version_from_bad_codename(self, mocked_error):
        '''Test mapping a bad OpenStack codename to numerical version'''
        openstack.get_os_version_codename('foo')
        expected_err = 'Could not derive OpenStack version for codename: foo'
        mocked_error.assert_called_with(expected_err)

    def test_os_codename_from_package(self):
        '''Test deriving OpenStack codename from an installed package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            for pkg, vers in FAKE_REPO.iteritems():
                if pkg.startswith('bad-'):
                    continue
                self.assertEquals(openstack.get_os_codename_package(pkg),
                                  vers['os_release'])

    @patch('charmhelpers.contrib.openstack.openstack_utils.error_out')
    def test_os_codename_from_bad_package_vrsion(self, mocked_error):
        '''Test deriving OpenStack codename for a poorly versioned package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            openstack.get_os_codename_package('bad-version')
            _e = ('Could not determine OpenStack codename for version 2016.1')
            mocked_error.assert_called_with(_e)

    @patch('charmhelpers.contrib.openstack.openstack_utils.error_out')
    def test_os_codename_from_bad_package(self, mocked_error):
        '''Test deriving OpenStack codename from an uninstalled package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            try:
                openstack.get_os_codename_package('foo')
            except:
                # ignore exceptions that raise when error_out is mocked
                # and doesn't sys.exit(1)
                pass
            _err = 'Could not determine version of installed package: foo'
            mocked_error.assert_called_with(_err)

    @patch('charmhelpers.contrib.openstack.openstack_utils.error_out')
    def test_os_version_from_package(self, mocked_error):
        '''Test deriving OpenStack version from an installed package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            for pkg, vers in FAKE_REPO.iteritems():
                if pkg.startswith('bad-'):
                    continue
                self.assertEquals(openstack.get_os_version_package(pkg),
                                  vers['os_version'])

    @patch('charmhelpers.contrib.openstack.openstack_utils.error_out')
    def test_os_version_from_bad_package(self, mocked_error):
        '''Test deriving OpenStack version from an uninstalled package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            try:
                openstack.get_os_version_package('foo')
            except:
                # ignore exceptions that raise when error_out is mocked
                # and doesn't sys.exit(1)
                pass
            _err = 'Could not determine version of installed package: foo'
            mocked_error.assert_called_with(_err)

    def test_juju_log(self):
        '''Test shelling out to juju-log'''
        with patch('subprocess.check_call') as mocked_subprocess:
            openstack.juju_log('foo')
            mocked_subprocess.assert_called_with(['juju-log', 'foo'])

    @patch('sys.exit')
    def test_error_out(self, mocked_exit):
        '''Test erroring out'''
        with patch('subprocess.check_call') as mocked_subprocess:
            openstack.error_out('Everything broke.')
            _log = ['juju-log', 'FATAL ERROR: Everything broke.']
            mocked_subprocess.assert_called_with(_log)
            mocked_exit.assert_called_with(1)

    def test_configure_install_source_distro(self):
        '''Test configuring installation from distro'''
        self.assertIsNone(openstack.configure_installation_source('distro'))

    def test_configure_install_source_ppa(self):
        '''Test configuring installation source from PPA'''
        with patch('subprocess.check_call') as mock:
            src = 'ppa:gandelman-a/openstack'
            openstack.configure_installation_source(src)
            ex_cmd = ['add-apt-repository', '-y', 'ppa:gandelman-a/openstack']
            mock.assert_called_with(ex_cmd)

    @patch('__builtin__.open')
    @patch('charmhelpers.contrib.openstack.openstack_utils.juju_log')
    @patch('charmhelpers.contrib.openstack.openstack_utils.import_key')
    def test_configure_install_source_deb_url(self, _import, _log, _open):
        '''Test configuring installation source from deb repo url'''
        _file = MagicMock(spec=file)
        _open.return_value = _file
        src = ('deb http://ubuntu-cloud.archive.canonical.com/ubuntu '
               'precise-havana main|KEYID')
        openstack.configure_installation_source(src)
        _import.assert_called_with('KEYID')
        _file.__enter__().write.assert_called_with(src.split('|')[0])
        src = ('deb http://ubuntu-cloud.archive.canonical.com/ubuntu '
               'precise-havana main')
        openstack.configure_installation_source(src)
        _file.__enter__().write.assert_called_with(src)

    @patch('charmhelpers.contrib.openstack.openstack_utils.error_out')
    def test_configure_bad_install_source(self, _error):
        openstack.configure_installation_source('foo')
        _error.assert_called_with('Invalid openstack-release specified: foo')

    @patch('charmhelpers.contrib.openstack.openstack_utils.lsb_release')
    def test_configure_install_source_uca_staging(self, _lsb):
        '''Test configuring installation source from UCA staging sources'''
        _lsb.return_value = FAKE_RELEASE
        # staging pockets are configured as PPAs
        with patch('subprocess.check_call') as _subp:
            src = 'cloud:precise-folsom/staging'
            openstack.configure_installation_source(src)
            cmd = ['add-apt-repository', '-y',
                   'ppa:ubuntu-cloud-archive/folsom-staging']
            _subp.assert_called_with(cmd)

    @patch('__builtin__.open')
    @patch('charmhelpers.contrib.openstack.openstack_utils.import_key')
    @patch('charmhelpers.contrib.openstack.openstack_utils.lsb_release')
    def test_configure_install_source_uca_repos(self, _lsb, _import, _open):
        '''Test configuring installation source from UCA sources'''
        _lsb.return_value = FAKE_RELEASE
        _file = MagicMock(spec=file)
        _open.return_value = _file
        for src, url in UCA_SOURCES:
            openstack.configure_installation_source(src)
            _import.assert_called_with(openstack.CLOUD_ARCHIVE_KEY_ID)
            _open.assert_called_with('/etc/apt/sources.list.d/cloud-archive.list',
                                     'w')
            _file.__enter__().write.assert_called_with(url)

    @patch('charmhelpers.contrib.openstack.openstack_utils.error_out')
    def test_configure_install_source_bad_uca(self, mocked_error):
        '''Test configuring installation source from bad UCA source'''
        try:
            openstack.configure_installation_source('cloud:foo-bar')
        except:
            # ignore exceptions that raise when error_out is mocked
            # and doesn't sys.exit(1)
            pass
        _e = 'Invalid Cloud Archive release specified: foo-bar'
        mocked_error.assert_called_with(_e)

    def test_import_apt_key(self):
        '''Ensure shell out apt-key during key import'''
        with patch('subprocess.check_call') as _subp:
            openstack.import_key('foo')
            cmd = ['apt-key', 'adv', '--keyserver', 'keyserver.ubuntu.com',
                   '--recv-keys', 'foo']
            _subp.assert_called_with(cmd)

    @patch('charmhelpers.contrib.openstack.openstack_utils.error_out')
    def test_import_bad_apt_key(self, mocked_error):
        '''Ensure error when importing apt key fails'''
        with patch('subprocess.check_call') as _subp:
            cmd = ['apt-key', 'adv', '--keyserver', 'keyserver.ubuntu.com',
                   '--recv-keys', 'foo']
            _subp.side_effect = subprocess.CalledProcessError(1, cmd, '')
            openstack.import_key('foo')
            cmd = ['apt-key', 'adv', '--keyserver', 'keyserver.ubuntu.com',
                   '--recv-keys', 'foo']
        mocked_error.assert_called_with('Error importing repo key foo')

    @patch('__builtin__.open')
    def test_save_scriptrc(self, _open):
        '''Test generation of scriptrc from environment'''
        scriptrc = ['#!/bin/bash\n',
                   'export setting1=foo\n',
                   'export setting2=bar\n']
        _file = MagicMock(spec=file)
        _open.return_value = _file
        os.environ['JUJU_UNIT_NAME'] = 'testing-foo/0'
        openstack.save_script_rc(setting1='foo', setting2='bar')
        expected_f = '/var/lib/juju/units/testing-foo-0/charm/scripts/scriptrc'
        _open.assert_called_with(expected_f, 'wb')
        for line in scriptrc:
            _file.__enter__().write.assert_has_calls(call(line))


if __name__ == '__main__':
    unittest.main()
