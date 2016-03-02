# Copyright 2016 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.
from testtools import TestCase

from mock import call
from mock import MagicMock
from mock import patch

from charmhelpers.contrib.hardening.audits import apt


class RestrictedPackagesTestCase(TestCase):
    def setUp(self):
        super(RestrictedPackagesTestCase, self).setUp()

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

    @patch.object(apt, 'apt')
    @patch.object(apt.subprocess, 'check_call')
    @patch.object(apt, 'log', lambda *args, **kwargs: None)
    def test_ensure_compliance(self, mock_check_call, mock_apt):
        pkg = self.create_package('bar')
        mock_apt.apt_pkg.Cache.return_value = {'bar': pkg}

        audit = apt.RestrictedPackages(pkgs=['bar'])
        audit.ensure_compliance()
        cmd = ['apt-get', '--assume-yes', 'purge', pkg.name]
        mock_check_call.assert_has_calls(call(cmd))

    @patch.object(apt, 'apt')
    @patch.object(apt.subprocess, 'check_call')
    @patch.object(apt, 'log', lambda *args, **kwargs: None)
    def test_apt_harden_virtual_package(self, mock_check_call, mock_apt):
        vpkg = self.create_package('virtualfoo', virtual=True)
        mock_apt.apt_pkg.Cache.return_value = {'foo': vpkg}
        audit = apt.RestrictedPackages(pkgs=['foo'])
        audit.ensure_compliance()
        self.assertTrue(mock_apt.apt_pkg.Cache.called)
        cmd1 = ['apt-get', '--assume-yes', 'purge', 'foo']
        cmd2 = ['apt-get', '--assume-yes', 'purge', 'virtualfoo']
        mock_check_call.assert_has_calls([call(cmd1), call(cmd2)])
