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

from unittest import TestCase

from charmhelpers.contrib.hardening.host.checks import securetty


class SecureTTYTestCase(TestCase):

    def test_securetty(self):
        audits = securetty.get_audits()
        self.assertEqual(1, len(audits))
        audit = audits[0]
        self.assertTrue(isinstance(audit, securetty.TemplatedFile))
        self.assertEqual('/etc/securetty', audit.paths[0])
