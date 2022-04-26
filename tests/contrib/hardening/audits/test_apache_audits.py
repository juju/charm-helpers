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

    @patch('subprocess.check_output')
    def test_get_loaded_modules(self, mock_check_output):
        mock_check_output.return_value = (b'Loaded Modules:\n'
                                          b' foo_module (static)\n'
                                          b' bar_module (shared)\n')
        audit = apache.DisabledModuleAudit('bar')
        result = audit._get_loaded_modules()
        self.assertEqual(['foo', 'bar'], result)

    @patch('subprocess.check_output')
    def test_is_ssl_enabled(self, mock_check_output):
        mock_check_output.return_value = (b'Loaded Modules:\n'
                                          b' foo_module (static)\n'
                                          b' bar_module (shared)\n'
                                          b' ssl_module (shared)\n')
        audit = apache.DisabledModuleAudit('bar')
        result = audit._get_loaded_modules()
        self.assertEqual(['foo', 'bar', 'ssl'], result)
        self.assertTrue(audit.is_ssl_enabled())
