from copy import copy
import apt_pkg
import unittest
from testtools import TestCase

import charmhelpers.contrib.openstackhelpers.openstack_utils as openstack

from mock import MagicMock, patch, Mock

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

    @patch('charmhelpers.contrib.openstackhelpers.openstack_utils.lsb_release')
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

    @patch('charmhelpers.contrib.openstackhelpers.openstack_utils.lsb_release')
    def test_os_codename_from_bad_install_source(self, mocked_lsb):
        '''Test mapping install source to OpenStack release name'''
        _fake_release = copy(FAKE_RELEASE)
        _fake_release['DISTRIB_CODENAME'] = 'natty'

        mocked_lsb.return_value = _fake_release
        _e = 'charmhelpers.contrib.openstackhelpers.openstack_utils.error_out'
        with patch(_e) as mocked_err:
            openstack.get_os_codename_install_source('distro')
            _er = ('Could not derive openstack release for this Ubuntu '
                   'release: natty')
            mocked_err.assert_called_with(_er)

    def test_os_codename_from_version(self):
        '''Test mapping OpenStack numerical versions to code name'''
        self.assertEquals(openstack.get_os_codename_version('2013.1'),
                          'grizzly')

    @patch('charmhelpers.contrib.openstackhelpers.openstack_utils.error_out')
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

    @patch('charmhelpers.contrib.openstackhelpers.openstack_utils.error_out')
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

    @patch('charmhelpers.contrib.openstackhelpers.openstack_utils.error_out')
    def test_os_codename_from_bad_package_vrsion(self, mocked_error):
        '''Test deriving OpenStack codename for a poorly versioned package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            openstack.get_os_codename_package('bad-version')
            _e = ('Could not determine OpenStack codename for version 2016.1')
            mocked_error.assert_called_with(_e)

    @patch('charmhelpers.contrib.openstackhelpers.openstack_utils.error_out')
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

    @patch('charmhelpers.contrib.openstackhelpers.openstack_utils.error_out')
    def test_os_version_from_package(self, mocked_error):
        '''Test deriving OpenStack version from an installed package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            for pkg, vers in FAKE_REPO.iteritems():
                if pkg.startswith('bad-'):
                    continue
                self.assertEquals(openstack.get_os_version_package(pkg),
                                  vers['os_version'])

    @patch('charmhelpers.contrib.openstackhelpers.openstack_utils.error_out')
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


if __name__ == '__main__':
    unittest.main()
