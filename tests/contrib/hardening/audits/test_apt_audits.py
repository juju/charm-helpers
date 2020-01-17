# Copyright 2016 Canonical Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import TestCase

from mock import call
from mock import MagicMock
from mock import patch

from charmhelpers.contrib.hardening.audits import apt
from charmhelpers.fetch import ubuntu_apt_pkg as apt_pkg
from charmhelpers.core import hookenv


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
            resp = {
                'has_provides': True,
                'has_versions': False,
            }
            pkg.get.side_effect = resp.get

        return pkg

    @patch.object(apt, 'apt_cache')
    @patch.object(apt, 'apt_purge')
    @patch.object(apt, 'log', lambda *args, **kwargs: None)
    def test_ensure_compliance(self, mock_purge, mock_apt_cache):
        pkg = self.create_package('bar')
        mock_apt_cache.return_value = {'bar': pkg}

        audit = apt.RestrictedPackages(pkgs=['bar'])
        audit.ensure_compliance()
        mock_purge.assert_has_calls([call(pkg.name)])

    @patch.object(apt, 'apt_purge')
    @patch.object(apt, 'apt_cache')
    @patch.object(apt, 'log', lambda *args, **kwargs: None)
    def test_apt_harden_virtual_package(self, mock_apt_cache, mock_apt_purge):
        vpkg = self.create_package('virtualfoo', virtual=True)
        mock_apt_cache.return_value = {'foo': vpkg}
        audit = apt.RestrictedPackages(pkgs=['foo'])
        audit.ensure_compliance()
        self.assertTrue(mock_apt_cache.called)
        mock_apt_purge.assert_has_calls([call('foo')])


class AptConfigTestCase(TestCase):

    @patch.object(apt, 'apt_pkg')
    def test_ensure_compliance(self, mock_apt_pkg):
        mock_apt_pkg.init.return_value = None
        mock_apt_pkg.config.side_effect = {}
        mock_apt_pkg.config.get.return_value = None
        audit = apt.AptConfig([{'key': 'APT::Get::AllowUnauthenticated',
                                'expected': 'false'}])
        audit.ensure_compliance()
        self.assertTrue(mock_apt_pkg.config.get.called)

    @patch.object(hookenv, 'log')
    def test_verify_config(self, mock_log):
        cfg = apt_pkg.config
        key, value = list(cfg.items())[0]
        audit = apt.AptConfig([{"key": key, "expected": value}])
        audit.ensure_compliance()
        self.assertFalse(mock_log.called)
