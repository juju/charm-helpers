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
from testtools import TestCase

from charmhelpers.contrib.hardening.base_check import BaseCheck
from charmhelpers.contrib.hardening.base_check import BaseFileCheck
# from charmhelpers.contrib.hardening.base_check import FilePermissionCheck
# from charmhelpers.contrib.hardening.base_check import DirectoryPermissionCheck


class BaseCheckTestCase(TestCase):

    def setUp(self):
        super(BaseCheckTestCase, self).setUp()

    def test__take_action_default(self):
        check = BaseCheck()
        take_action = check._take_action()
        self.assertTrue(take_action)

    def test__take_action_unless_true(self):
        check = BaseCheck(unless=True)
        take_action = check._take_action()
        self.assertFalse(take_action)

    def test__take_action_unless_false(self):
        check = BaseCheck(unless=False)
        take_action = check._take_action()
        self.assertTrue(take_action)

    def test__take_action_unless_callback_false(self):
        def callback():
            return False
        check = BaseCheck(unless=callback)
        take_action = check._take_action()
        self.assertTrue(take_action)

    def test__take_action_unless_callback_true(self):
        def callback():
            return True
        check = BaseCheck(unless=callback)
        take_action = check._take_action()
        self.assertFalse(take_action)


@patch('os.path.exists')
class BaseFileCheckTestCase(TestCase):

    def setUp(self):
        super(BaseFileCheckTestCase, self).setUp()
        self._patch_obj(BaseFileCheck, 'is_compliant')
        self._patch_obj(BaseFileCheck, 'comply')
        self._patch('charmhelpers.contrib.hardening.base_check.log')

    def _patch_obj(self, obj, method):
        _m = patch.object(obj, method)
        mock = _m.start()
        self.addCleanup(mock.stop)
        setattr(self, method, mock)

    def _patch(self, method):
        _m = patch(method)
        mock = _m.start()
        self.addCleanup(mock.stop)
        method_name = method[method.rfind('.') + 1:]
        setattr(self, method_name, mock)

    def test_ensure_compliance(self, mock_exists):
        mock_exists.return_value = False
        check = BaseFileCheck(paths='/tmp/foo')
        check.ensure_compliance()
        self.assertFalse(self.comply.called)

    def test_ensure_compliance_in_compliance(self, mock_exists):
        mock_exists.return_value = True
        self.is_compliant.return_value = True
        check = BaseFileCheck(paths=['/tmp/foo'])
        check.ensure_compliance()
        mock_exists.assert_has_calls(call('/tmp/foo'))
        self.is_compliant.assert_has_calls(call('/tmp/foo'))
        self.assertFalse(self.log.called)
        self.assertFalse(self.comply.called)

    def test_ensure_compliance_out_of_compliance(self, mock_exists):
        mock_exists.return_value = True
        self.is_compliant.return_value = False
        check = BaseFileCheck(paths=['/tmp/foo'])
        check.ensure_compliance()
        mock_exists.assert_has_calls(call('/tmp/foo'))
        self.is_compliant.assert_has_calls(call('/tmp/foo'))
        self.assertTrue(self.log.called)
        self.comply.assert_has_calls(call('/tmp/foo'))
