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

from mock import call
from mock import patch

from unittest import TestCase
from charmhelpers.contrib.hardening.audits import apache
from subprocess import CalledProcessError


class DisabledModuleAuditsTest(TestCase):

    def setup(self):
        super(DisabledModuleAuditsTest, self).setUp()
        self._patch_obj(apache, 'log')

    def _patch_obj(self, obj, method):
        _m = patch.object(obj, method)
        mock = _m.start()
        self.addCleanup(mock.stop)
        setattr(self, method, mock)

    def test_init_string(self):
        audit = apache.DisabledModuleAudit('foo')
        self.assertEqual(['foo'], audit.modules)

    def test_init_list(self):
        audit = apache.DisabledModuleAudit(['foo', 'bar'])
        self.assertEqual(['foo', 'bar'], audit.modules)

    @patch.object(apache.DisabledModuleAudit, '_get_loaded_modules')
    def test_ensure_compliance_no_modules(self, mock_loaded_modules):
        audit = apache.DisabledModuleAudit(None)
        audit.ensure_compliance()
        self.assertFalse(mock_loaded_modules.called)

    @patch.object(apache.DisabledModuleAudit, '_get_loaded_modules')
    @patch.object(apache, 'log', lambda *args, **kwargs: None)
    def test_ensure_compliance_loaded_modules_raises_ex(self,
                                                        mock_loaded_modules):
        mock_loaded_modules.side_effect = CalledProcessError(1, 'test', 'err')
        audit = apache.DisabledModuleAudit('foo')
        audit.ensure_compliance()

    @patch.object(apache.DisabledModuleAudit, '_get_loaded_modules')
    @patch.object(apache.DisabledModuleAudit, '_disable_module')
    @patch.object(apache, 'log', lambda *args, **kwargs: None)
    def test_disabled_modules_not_loaded(self, mock_disable_module,
                                         mock_loaded_modules):
        mock_loaded_modules.return_value = ['foo']
        audit = apache.DisabledModuleAudit('bar')
        audit.ensure_compliance()
        self.assertFalse(mock_disable_module.called)

    @patch.object(apache.DisabledModuleAudit, '_get_loaded_modules')
    @patch.object(apache.DisabledModuleAudit, '_disable_module')
    @patch.object(apache.DisabledModuleAudit, '_restart_apache')
    @patch.object(apache, 'log', lambda *args, **kwargs: None)
    def test_disabled_modules_loaded(self, mock_restart_apache,
                                     mock_disable_module, mock_loaded_modules):
        mock_loaded_modules.return_value = ['foo', 'bar']
        audit = apache.DisabledModuleAudit('bar')
        audit.ensure_compliance()
        mock_disable_module.assert_has_calls([call('bar')])
        mock_restart_apache.assert_has_calls([call()])
