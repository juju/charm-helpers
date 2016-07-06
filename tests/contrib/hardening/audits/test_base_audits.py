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

from charmhelpers.contrib.hardening.audits import BaseAudit


class BaseAuditTestCase(TestCase):

    def setUp(self):
        super(BaseAuditTestCase, self).setUp()

    def test_take_action_default(self):
        check = BaseAudit()
        take_action = check._take_action()
        self.assertTrue(take_action)

    def test_take_action_unless_true(self):
        check = BaseAudit(unless=True)
        take_action = check._take_action()
        self.assertFalse(take_action)

    def test_take_action_unless_false(self):
        check = BaseAudit(unless=False)
        take_action = check._take_action()
        self.assertTrue(take_action)

    def test_take_action_unless_callback_false(self):
        def callback():
            return False
        check = BaseAudit(unless=callback)
        take_action = check._take_action()
        self.assertTrue(take_action)

    def test_take_action_unless_callback_true(self):
        def callback():
            return True
        check = BaseAudit(unless=callback)
        take_action = check._take_action()
        self.assertFalse(take_action)
