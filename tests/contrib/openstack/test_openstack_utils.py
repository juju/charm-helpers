import os
import subprocess
import unittest

from copy import copy
from testtools import TestCase
from mock import MagicMock, patch, call

import charmhelpers.contrib.openstack.utils as openstack


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
    'swift-proxy': {
        'pkg_vers': '1.9.0-0ubuntu1',
        'os_release': 'havana',
        'os_version': '1.9.0'
    },
    'swift-proxy': {
        'pkg_vers': '1.10.0~rc1-0ubuntu1',
        'os_release': 'havana',
        'os_version': '1.10.0'
    },
    # a package thats available in the cache but is not installed
    'cinder-common': {
        'os_release': 'havana',
        'os_version': '2013.2'
    },
    # poorly formed openstack version
    'bad-version': {
        'pkg_vers': '1:2016.1-0ubuntu1.1~cloud0',
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
        return [FakeAnswer(self.ip)]


class FakeReverse(object):
    def from_address(self, address):
        return '156.94.189.91.in-addr.arpa'


class FakeDNS(object):
    def __init__(self, ip):
        self.resolver = FakeResolver(ip)
        self.reversename = FakeReverse()
        self.name = MagicMock()
        self.name.Name = basestring


class OpenStackHelpersTestCase(TestCase):
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

    @patch('charmhelpers.contrib.openstack.utils.lsb_release')
    def test_os_codename_from_install_source(self, mocked_lsb):
        '''Test mapping install source to OpenStack release name'''
        mocked_lsb.return_value = FAKE_RELEASE

        # the openstack release shipped with respective ubuntu/lsb release.
        self.assertEquals(openstack.get_os_codename_install_source('distro'),
                          'essex')
        # proposed pocket
        self.assertEquals(openstack.get_os_codename_install_source('distro-proposed'),
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

    @patch.object(openstack, 'get_os_version_codename')
    @patch.object(openstack, 'get_os_codename_install_source')
    def test_os_version_from_install_source(self, codename, version):
        codename.return_value = 'grizzly'
        openstack.get_os_version_install_source('cloud:precise-grizzly')
        version.assert_called_with('grizzly')

    @patch('charmhelpers.contrib.openstack.utils.lsb_release')
    def test_os_codename_from_bad_install_source(self, mocked_lsb):
        '''Test mapping install source to OpenStack release name'''
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
        '''Test mapping OpenStack numerical versions to code name'''
        self.assertEquals(openstack.get_os_codename_version('2013.1'),
                          'grizzly')

    @patch('charmhelpers.contrib.openstack.utils.error_out')
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

    @patch('charmhelpers.contrib.openstack.utils.error_out')
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
                # test fake repo for all "installed" packages
                if pkg.startswith('bad-'):
                    continue
                if 'pkg_vers' not in vers:
                    continue
                self.assertEquals(openstack.get_os_codename_package(pkg),
                                  vers['os_release'])

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_codename_from_bad_package_version(self, mocked_error):
        '''Test deriving OpenStack codename for a poorly versioned package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            openstack.get_os_codename_package('bad-version')
            _e = ('Could not determine OpenStack codename for version 2016.1')
            mocked_error.assert_called_with(_e)

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_codename_from_bad_package(self, mocked_error):
        '''Test deriving OpenStack codename from an unavailable package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            try:
                openstack.get_os_codename_package('foo')
            except:
                # ignore exceptions that raise when error_out is mocked
                # and doesn't sys.exit(1)
                pass
            e = 'Could not determine version of package with no installation '\
                'candidate: foo'
            mocked_error.assert_called_with(e)

    def test_os_codename_from_bad_package_nonfatal(self):
        '''Test OpenStack codename from an unavailable package is non-fatal'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            self.assertEquals(
                None,
                openstack.get_os_codename_package('foo', fatal=False)
            )

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_codename_from_uninstalled_package(self, mock_error):
        '''Test OpenStack codename from an available but uninstalled pkg'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            try:
                openstack.get_os_codename_package('cinder-common', fatal=True)
            except:
                pass
            e = ('Could not determine version of uninstalled package: '
                 'cinder-common')
            mock_error.assert_called_with(e)

    def test_os_codename_from_uninstalled_package_nonfatal(self):
        '''Test OpenStack codename from avail uninstalled pkg is non fatal'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            self.assertEquals(
                None,
                openstack.get_os_codename_package('cinder-common', fatal=False)
            )

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_os_version_from_package(self, mocked_error):
        '''Test deriving OpenStack version from an installed package'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            for pkg, vers in FAKE_REPO.iteritems():
                if pkg.startswith('bad-'):
                    continue
                if 'pkg_vers' not in vers:
                    continue
                self.assertEquals(openstack.get_os_version_package(pkg),
                                  vers['os_version'])

    @patch('charmhelpers.contrib.openstack.utils.error_out')
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
            e = 'Could not determine version of package with no installation '\
                'candidate: foo'
            mocked_error.assert_called_with(e)

    def test_os_version_from_bad_package_nonfatal(self):
        '''Test OpenStack version from an uninstalled package is non-fatal'''
        with patch('apt_pkg.Cache') as cache:
            cache.return_value = self._apt_cache()
            self.assertEquals(
                None,
                openstack.get_os_version_package('foo', fatal=False)
            )

    @patch.object(openstack, 'get_os_codename_package')
    def test_os_release_uncached(self, get_cn):
        openstack.os_rel = None
        get_cn.return_value = 'folsom'
        self.assertEquals('folsom', openstack.os_release('nova-common'))

    def test_os_release_cached(self):
        openstack.os_rel = 'foo'
        self.assertEquals('foo', openstack.os_release('nova-common'))

    @patch.object(openstack, 'juju_log')
    @patch('sys.exit')
    def test_error_out(self, mocked_exit, juju_log):
        '''Test erroring out'''
        openstack.error_out('Everything broke.')
        _log = 'FATAL ERROR: Everything broke.'
        juju_log.assert_called_with(_log, level='ERROR')
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
    @patch('charmhelpers.contrib.openstack.utils.juju_log')
    @patch('charmhelpers.contrib.openstack.utils.import_key')
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

    @patch('charmhelpers.contrib.openstack.utils.lsb_release')
    @patch('__builtin__.open')
    @patch('charmhelpers.contrib.openstack.utils.juju_log')
    def test_configure_install_source_distro_proposed(self, _log, _open, _lsb):
        '''Test configuring installation source from deb repo url'''
        _lsb.return_value = FAKE_RELEASE
        _file = MagicMock(spec=file)
        _open.return_value = _file
        openstack.configure_installation_source('distro-proposed')
        src = ('deb http://archive.ubuntu.com/ubuntu/ precise-proposed '
               'restricted main multiverse universe')
        openstack.configure_installation_source(src)
        _file.__enter__().write.assert_called_with(src)

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_configure_bad_install_source(self, _error):
        openstack.configure_installation_source('foo')
        _error.assert_called_with('Invalid openstack-release specified: foo')

    @patch('charmhelpers.contrib.openstack.utils.lsb_release')
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
    @patch('charmhelpers.contrib.openstack.utils.apt_install')
    @patch('charmhelpers.contrib.openstack.utils.lsb_release')
    def test_configure_install_source_uca_repos(self, _lsb, _install, _open):
        '''Test configuring installation source from UCA sources'''
        _lsb.return_value = FAKE_RELEASE
        _file = MagicMock(spec=file)
        _open.return_value = _file
        for src, url in UCA_SOURCES:
            openstack.configure_installation_source(src)
            _install.assert_called_with('ubuntu-cloud-keyring',
                                        fatal=True)
            _open.assert_called_with(
                '/etc/apt/sources.list.d/cloud-archive.list',
                'w'
            )
            _file.__enter__().write.assert_called_with(url)

    @patch('charmhelpers.contrib.openstack.utils.error_out')
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
            cmd = ['apt-key', 'adv', '--keyserver', 'hkp://keyserver.ubuntu.com:80',
                   '--recv-keys', 'foo']
            _subp.assert_called_with(cmd)

    @patch('charmhelpers.contrib.openstack.utils.error_out')
    def test_import_bad_apt_key(self, mocked_error):
        '''Ensure error when importing apt key fails'''
        with patch('subprocess.check_call') as _subp:
            cmd = ['apt-key', 'adv', '--keyserver', 'hkp://keyserver.ubuntu.com:80',
                   '--recv-keys', 'foo']
            _subp.side_effect = subprocess.CalledProcessError(1, cmd, '')
            openstack.import_key('foo')
            cmd = ['apt-key', 'adv', '--keyserver', 'hkp://keyserver.ubuntu.com:80',
                   '--recv-keys', 'foo']
        mocked_error.assert_called_with('Error importing repo key foo')

    @patch('os.mkdir')
    @patch('os.path.exists')
    @patch('charmhelpers.contrib.openstack.utils.charm_dir')
    @patch('__builtin__.open')
    def test_save_scriptrc(self, _open, _charm_dir, _exists, _mkdir):
        '''Test generation of scriptrc from environment'''
        scriptrc = ['#!/bin/bash\n',
                    'export setting1=foo\n',
                    'export setting2=bar\n']
        _file = MagicMock(spec=file)
        _open.return_value = _file
        _charm_dir.return_value = '/var/lib/juju/units/testing-foo-0/charm'
        _exists.return_value = False
        os.environ['JUJU_UNIT_NAME'] = 'testing-foo/0'
        openstack.save_script_rc(setting1='foo', setting2='bar')
        rcdir = '/var/lib/juju/units/testing-foo-0/charm/scripts'
        _mkdir.assert_called_with(rcdir)
        expected_f = '/var/lib/juju/units/testing-foo-0/charm/scripts/scriptrc'
        _open.assert_called_with(expected_f, 'wb')
        _mkdir.assert_called_with(os.path.dirname(expected_f))
        for line in scriptrc:
            _file.__enter__().write.assert_has_calls(call(line))

    @patch.object(openstack, 'lsb_release')
    @patch.object(openstack, 'get_os_version_package')
    @patch.object(openstack, 'config')
    def test_openstack_upgrade_detection_true(self, config, vers_pkg, lsb):
        """Test it detects when an openstack package has available upgrade"""
        lsb.return_value = FAKE_RELEASE
        config.return_value = 'cloud:precise-havana'
        vers_pkg.return_value = '2013.1.1'
        self.assertTrue(openstack.openstack_upgrade_available('nova-common'))
        # milestone to major release detection
        vers_pkg.return_value = '2013.2~b1'
        self.assertTrue(openstack.openstack_upgrade_available('nova-common'))

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

    @patch.object(openstack, 'is_block_device')
    @patch.object(openstack, 'error_out')
    def test_ensure_block_device_bad_config(self, err, is_bd):
        '''Test it doesn't prepare storage with bad config'''
        openstack.ensure_block_device(block_device='none')
        self.assertTrue(err.called)

    @patch.object(openstack, 'is_block_device')
    @patch.object(openstack, 'ensure_loopback_device')
    def test_ensure_block_device_loopback(self, ensure_loopback, is_bd):
        '''Test it ensures loopback device when checking block device'''
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
        '''Test it looks for storage at both relative and full device path'''
        for dev in ['vdb', '/dev/vdb']:
            openstack.ensure_block_device(dev)
            is_bd.assert_called_with('/dev/vdb')

    @patch.object(openstack, 'is_block_device')
    @patch.object(openstack, 'error_out')
    def test_ensure_nonexistent_block_device(self, error_out, is_bd):
        '''Test it will not ensure a non-existant block device'''
        is_bd.return_value = False
        openstack.ensure_block_device(block_device='foo')
        self.assertTrue(error_out.called)

    @patch.object(openstack, 'juju_log')
    @patch.object(openstack, 'umount')
    @patch.object(openstack, 'mounts')
    @patch.object(openstack, 'zap_disk')
    @patch.object(openstack, 'is_lvm_physical_volume')
    def test_clean_storage_unmount(self, is_pv, zap_disk, mounts, umount, log):
        '''Test it unmounts block device when cleaning storage'''
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
        '''Test it removes traces of LVM when cleaning storage'''
        mounts.return_value = []
        is_pv.return_value = True
        openstack.clean_storage('/dev/vdb')
        rm_lv.assert_called_with('/dev/vdb')
        rm_vg .assert_called_with('/dev/vdb')

    @patch.object(openstack, 'zap_disk')
    @patch.object(openstack, 'is_lvm_physical_volume')
    @patch.object(openstack, 'mounts')
    def test_clean_storage_zap_disk(self, mounts, is_pv, zap_disk):
        '''It removes traces of LVM when cleaning storage'''
        mounts.return_value = []
        is_pv.return_value = False
        openstack.clean_storage('/dev/vdb')
        zap_disk.assert_called_with('/dev/vdb')

    def test_is_ip(self):
        self.assertTrue(openstack.is_ip('10.0.0.1'))
        self.assertFalse(openstack.is_ip('www.ubuntu.com'))

    @patch.object(openstack, 'apt_install')
    def test_get_host_ip_with_hostname(self, apt_install):
        fake_dns = FakeDNS('10.0.0.1')
        with patch('__builtin__.__import__', side_effect=[fake_dns]):
            ip = openstack.get_host_ip('www.ubuntu.com')
        self.assertEquals(ip, '10.0.0.1')

    @patch.object(openstack, 'apt_install')
    def test_get_host_ip_with_ip(self, apt_install):
        fake_dns = FakeDNS('5.5.5.5')
        with patch('__builtin__.__import__', side_effect=[fake_dns]):
            ip = openstack.get_host_ip('4.2.2.1')
        self.assertEquals(ip, '4.2.2.1')

    @patch.object(openstack, 'apt_install')
    def test_get_hostname_with_ip(self, apt_install):
        fake_dns = FakeDNS('www.ubuntu.com')
        with patch('__builtin__.__import__', side_effect=[fake_dns, fake_dns]):
            hn = openstack.get_hostname('4.2.2.1')
        self.assertEquals(hn, 'www.ubuntu.com')

    @patch.object(openstack, 'apt_install')
    def test_get_hostname_with_hostname(self, apt_install):
        fake_dns = FakeDNS('5.5.5.5')
        with patch('__builtin__.__import__', side_effect=[fake_dns]):
            hn = openstack.get_hostname('www.ubuntu.com')
        self.assertEquals(hn, 'www.ubuntu.com')


if __name__ == '__main__':
    unittest.main()
