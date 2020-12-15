import mock
import subprocess
import unittest

from charmhelpers.fetch import ubuntu_apt_pkg as apt_pkg


class Test_apt_pkg_Cache(unittest.TestCase):
    """Borrow PatchHelper methods from ``charms.openstack``."""
    def setUp(self):
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch(self, patchee, name=None, **kwargs):
        """Patch a patchable thing.  Uses mock.patch() to do the work.
        Automatically unpatches at the end of the test.

        The mock gets added to the test object (self) using 'name' or the last
        part of the patchee string, after the final dot.

        :param patchee: <string> representing module.object that is to be
            patched.
        :param name: optional <string> name to call the mock.
        :param **kwargs: any other args to pass to mock.patch()
        """
        mocked = mock.patch(patchee, **kwargs)
        if name is None:
            name = patchee.split('.')[-1]
        started = mocked.start()
        self._patches[name] = mocked
        self._patches_start[name] = started
        setattr(self, name, started)

    def patch_object(self, obj, attr, name=None, **kwargs):
        """Patch a patchable thing.  Uses mock.patch.object() to do the work.
        Automatically unpatches at the end of the test.

        The mock gets added to the test object (self) using 'name' or the attr
        passed in the arguments.

        :param obj: an object that needs to have an attribute patched.
        :param attr: <string> that represents the attribute being patched.
        :param name: optional <string> name to call the mock.
        :param **kwargs: any other args to pass to mock.patch()
        """
        mocked = mock.patch.object(obj, attr, **kwargs)
        if name is None:
            name = attr
        started = mocked.start()
        self._patches[name] = mocked
        self._patches_start[name] = started
        setattr(self, name, started)

    def test_apt_cache_show(self):
        self.patch_object(apt_pkg.subprocess, 'check_output')
        apt_cache = apt_pkg.Cache()
        self.check_output.return_value = (
            'Package: dpkg\n'
            'Version: 1.19.0.5ubuntu2.1\n'
            'Bugs: https://bugs.launchpad.net/ubuntu/+filebug\n'
            'Description-en: Debian package management system\n'
            ' Multiline description\n'
            '\n'
            'Package: lsof\n'
            'Architecture: amd64\n'
            'Version: 4.91+dfsg-1ubuntu1\n'
            '\n'
            'N: There is 1 additional record.\n')
        self.assertEquals(
            apt_cache._apt_cache_show(['package']),
            {'dpkg': {
                'package': 'dpkg', 'version': '1.19.0.5ubuntu2.1',
                'bugs': 'https://bugs.launchpad.net/ubuntu/+filebug',
                'description-en': 'Debian package management system\n'
                                  'Multiline description'},
             'lsof': {
                 'package': 'lsof', 'architecture': 'amd64',
                 'version': '4.91+dfsg-1ubuntu1'},
             })
        self.check_output.assert_called_once_with(
            ['apt-cache', 'show', '--no-all-versions', 'package'],
            stderr=subprocess.STDOUT,
            universal_newlines=True)

    def test_dpkg_list(self):
        self.patch_object(apt_pkg.subprocess, 'check_output')
        apt_cache = apt_pkg.Cache()
        self.check_output.return_value = (
            'Desired=Unknown/Install/Remove/Purge/Hold\n'
            '| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/'
            'trig-aWait/Trig-pend\n'
            '|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)\n'
            '||/ Name           Version            Architecture Description\n'
            '+++-=============================-==================-===========-'
            '=================================\n'
            'ii  dpkg                          1.19.0.5ubuntu2.1  amd64       '
            'Debian package management system\n'
            'rc  linux-image-4.15.0-42-generic 4.15.0-42.45       amd64       '
            'Signed kernel image generic\n'
            'ii  lsof                          4.91+dfsg-1ubuntu1 amd64       '
            'utility to list open files\n')
        expect = {
            'dpkg': {
                'name': 'dpkg',
                'version': '1.19.0.5ubuntu2.1',
                'architecture': 'amd64',
                'description': 'Debian package management system'
            },
            'lsof': {
                'name': 'lsof',
                'version': '4.91+dfsg-1ubuntu1',
                'architecture': 'amd64',
                'description': 'utility to list open files'
            },
        }
        self.assertEquals(
            apt_cache._dpkg_list(['package']), expect)
        self.check_output.side_effect = subprocess.CalledProcessError(
            1, '', output=self.check_output.return_value)
        self.assertEquals(apt_cache._dpkg_list(['package']), expect)
        self.check_output.side_effect = subprocess.CalledProcessError(2, '')
        with self.assertRaises(subprocess.CalledProcessError):
            _ = apt_cache._dpkg_list(['package'])

    def test_version_compare(self):
        self.patch_object(apt_pkg.subprocess, 'check_call')
        self.assertEquals(apt_pkg.version_compare('2', '1'), 1)
        self.check_call.assert_called_once_with(
            ['dpkg', '--compare-versions', '2', 'gt', '1'],
            stderr=subprocess.STDOUT,
            universal_newlines=True)
        self.check_call.side_effect = [
            subprocess.CalledProcessError(1, '', ''),
            None,
            None,
        ]
        self.assertEquals(apt_pkg.version_compare('2', '2'), 0)
        self.check_call.side_effect = [
            subprocess.CalledProcessError(1, '', ''),
            subprocess.CalledProcessError(1, '', ''),
            None,
        ]
        self.assertEquals(apt_pkg.version_compare('1', '2'), -1)
        self.check_call.side_effect = subprocess.CalledProcessError(2, '', '')
        self.assertRaises(subprocess.CalledProcessError,
                          apt_pkg.version_compare, '2', '2')

    def test_apt_cache(self):
        self.patch_object(apt_pkg.subprocess, 'check_output')
        apt_cache = apt_pkg.Cache()
        self.check_output.side_effect = [
            ('Package: dpkg\n'
             'Version: 1.19.0.6ubuntu0\n'
             'Bugs: https://bugs.launchpad.net/ubuntu/+filebug\n'
             'Description-en: Debian package management system\n'
             ' Multiline description\n'
             '\n'
             'Package: lsof\n'
             'Architecture: amd64\n'
             'Version: 4.91+dfsg-1ubuntu1\n'
             '\n'
             'N: There is 1 additional record.\n'),
            ('Desired=Unknown/Install/Remove/Purge/Hold\n'
             '| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/'
             'trig-aWait/Trig-pend\n'
             '|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)\n'
             '||/ Name           Version            Architecture Description\n'
             '+++-=============================-==================-===========-'
             '=================================\n'
             'ii  dpkg                          1.19.0.5ubuntu2.1  amd64       '
             'Debian package management system\n'
             'rc  linux-image-4.15.0-42-generic 4.15.0-42.45       amd64       '
             'Signed kernel image generic\n'
             'ii  lsof                          4.91+dfsg-1ubuntu1 amd64       '
             'utility to list open files\n'),
        ]
        pkg = apt_cache['dpkg']
        self.assertEquals(pkg.name, 'dpkg')
        self.assertEquals(pkg.current_ver.ver_str, '1.19.0.5ubuntu2.1')
        self.assertEquals(pkg.architecture, 'amd64')
        self.check_output.side_effect = [
            subprocess.CalledProcessError(100, ''),
            subprocess.CalledProcessError(1, ''),
        ]
        with self.assertRaises(KeyError):
            pkg = apt_cache['nonexistent']
        self.check_output.side_effect = [
            ('Package: dpkg\n'
             'Version: 1.19.0.6ubuntu0\n'
             'Bugs: https://bugs.launchpad.net/ubuntu/+filebug\n'
             'Description-en: Debian package management system\n'
             ' Multiline description\n'
             '\n'
             'Package: lsof\n'
             'Architecture: amd64\n'
             'Version: 4.91+dfsg-1ubuntu1\n'
             '\n'
             'N: There is 1 additional record.\n'),
            subprocess.CalledProcessError(42, ''),
        ]
        with self.assertRaises(subprocess.CalledProcessError):
            # System error occurs while making dpkg inquiry
            pkg = apt_cache['dpkg']
        self.check_output.side_effect = [
            subprocess.CalledProcessError(42, ''),
            subprocess.CalledProcessError(1, ''),
        ]
        with self.assertRaises(subprocess.CalledProcessError):
            pkg = apt_cache['system-error-occurs-while-making-apt-inquiry']


class Test_apt_pkg_PkgVersion(unittest.TestCase):

    def test_PkgVersion(self):
        self.assertTrue(
            apt_pkg.PkgVersion('2:20.4.0') <
            apt_pkg.PkgVersion('2:20.4.1'))
        self.assertFalse(
            apt_pkg.PkgVersion('2:20.4.1') <
            apt_pkg.PkgVersion('2:20.4.0'))

        self.assertTrue(
            apt_pkg.PkgVersion('2:20.4.0') <=
            apt_pkg.PkgVersion('2:20.4.1'))
        self.assertTrue(
            apt_pkg.PkgVersion('2:20.4.0') <=
            apt_pkg.PkgVersion('2:20.4.0'))
        self.assertFalse(
            apt_pkg.PkgVersion('2:20.4.1') <=
            apt_pkg.PkgVersion('2:20.4.0'))

        self.assertTrue(
            apt_pkg.PkgVersion('2:20.4.1') >
            apt_pkg.PkgVersion('2:20.4.0'))
        self.assertFalse(
            apt_pkg.PkgVersion('2:20.4.0') >
            apt_pkg.PkgVersion('2:20.4.1'))

        self.assertTrue(
            apt_pkg.PkgVersion('2:20.4.1') >=
            apt_pkg.PkgVersion('2:20.4.0'))
        self.assertTrue(
            apt_pkg.PkgVersion('2:20.4.0') >=
            apt_pkg.PkgVersion('2:20.4.0'))
        self.assertFalse(
            apt_pkg.PkgVersion('2:20.4.0') >=
            apt_pkg.PkgVersion('2:20.4.1'))

        self.assertTrue(
            apt_pkg.PkgVersion('2:20.4.0') ==
            apt_pkg.PkgVersion('2:20.4.0'))
        self.assertFalse(
            apt_pkg.PkgVersion('2:20.4.0') ==
            apt_pkg.PkgVersion('2:20.4.1'))

        self.assertTrue(
            apt_pkg.PkgVersion('2:20.4.0') !=
            apt_pkg.PkgVersion('2:20.4.1'))
        self.assertFalse(
            apt_pkg.PkgVersion('2:20.4.0') !=
            apt_pkg.PkgVersion('2:20.4.0'))

        pkgs = [apt_pkg.PkgVersion('2:20.4.0'),
                apt_pkg.PkgVersion('2:21.4.0'),
                apt_pkg.PkgVersion('2:17.4.0')]
        pkgs.sort()
        self.assertEqual(
            pkgs,
            [apt_pkg.PkgVersion('2:17.4.0'),
             apt_pkg.PkgVersion('2:20.4.0'),
             apt_pkg.PkgVersion('2:21.4.0')])
