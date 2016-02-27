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
    @patch.object(apthardening.subprocess, 'check_call')
    @patch.object(apthardening, 'log', lambda *args, **kwargs: None)
    def test_apt_harden(self, mock_check_call, mock_apt):
        pkg = self.create_package('foo')
        mock_apt.Cache.return_value = {'foo': pkg}
        apthardening.apt_harden()
        self.assertTrue(mock_apt.Cache.called)
        cmd = ['apt-get', '--assume-yes', 'purge', pkg.name]
        mock_check_call.assert_has_calls([call(cmd)])

    @patch.object(apthardening.utils, 'get_defaults',
                  lambda arg: {'security_packages_clean': True,
                               'security_packages_list': ['foo']})
    @patch.object(apthardening, 'apt')
    @patch.object(apthardening.subprocess, 'check_call')
    @patch.object(apthardening, 'log', lambda *args, **kwargs: None)
    def test_apt_harden_virtual_package(self, mock_check_call, mock_apt):
        vpkg = self.create_package('virtualfoo', virtual=True)
        mock_apt.Cache.return_value = {'foo': vpkg}
        apthardening.apt_harden()
        self.assertTrue(mock_apt.Cache.called)
        cmd1 = ['apt-get', '--assume-yes', 'purge', 'foo']
        cmd2 = ['apt-get', '--assume-yes', 'purge', 'virtualfoo']
        mock_check_call.assert_has_calls([call(cmd1), call(cmd2)])
