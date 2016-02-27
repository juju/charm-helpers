from mock import (
    MagicMock,
    call,
    patch
)
from testtools import TestCase

CONFIG = {'harden': False}


with patch('charmhelpers.core.hookenv.config', lambda key: CONFIG.get('key')):
    from charmhelpers.contrib.hardening.os_hardening import apthardening


class APTTestCase(TestCase):

    def setUp(self):
        super(APTTestCase, self).setUp()

    def create_package(self, name, virtual=False):
        pkg = MagicMock()
        pkg.name = name
        pkg.current_ver = '2.0'
        if virtual:
            pkgver = MagicMock()
            pkgver.parent_pkg = self.create_package('foo')
            pkg.provides_list = [('virtualfoo', None, pkgver)]
            pkg.has_provides = True
            pkg.has_versions = False

        return pkg

    @patch.object(apthardening.utils, 'get_defaults',
                  lambda arg: {'security_packages_clean': True,
                               'security_packages_list': ['foo']})
    @patch.object(apthardening, 'apt')
    @patch.object(apthardening, 'log', lambda *args, **kwargs: None)
    def test_apt_harden(self, mock_apt):
        pm = mock_apt.apt_pkg.PackageManager.return_value
        pkg = self.create_package('foo')
        mock_apt.apt_pkg.Cache.return_value = {'foo': pkg}
        apthardening.apt_harden()
        self.assertTrue(mock_apt.apt_pkg.Cache.called)
        self.assertTrue(mock_apt.apt_pkg.PackageManager.called)
        pm.remove.assert_has_calls([call('foo', purge=True)])

    @patch.object(apthardening.utils, 'get_defaults',
                  lambda arg: {'security_packages_clean': True,
                               'security_packages_list': ['foo']})
    @patch.object(apthardening, 'apt')
    @patch.object(apthardening, 'log', lambda *args, **kwargs: None)
    def test_apt_harden_virtual_package(self, mock_apt):
        pm = mock_apt.apt_pkg.PackageManager.return_value
        vpkg = self.create_package('virtualfoo', virtual=True)
        mock_apt.apt_pkg.Cache.return_value = {'foo': vpkg}
        apthardening.apt_harden()
        self.assertTrue(mock_apt.apt_pkg.Cache.called)
        self.assertTrue(mock_apt.apt_pkg.PackageManager.called)
        pm.remove.assert_has_calls([call('foo', purge=True),
                                    call('virtualfoo', purge=True)])
