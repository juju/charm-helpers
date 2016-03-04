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
