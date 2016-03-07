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

from mock import patch

from charmhelpers.contrib.hardening.host.checks import limits


class LimitsTestCase(TestCase):

    @patch.object(limits.utils, 'get_defaults',
                  lambda x: {'security': {'kernel_enable_core_dump': False}})
    def test_core_dump_disabled(self):
        audits = limits.get_audits()
        self.assertEqual(2, len(audits))
        audit = audits[0]
        self.assertTrue(isinstance(audit, limits.DirectoryPermissionAudit))
        self.assertEqual('/etc/security/limits.d', audit.paths[0])
        audit = audits[1]
        self.assertTrue(isinstance(audit, limits.TemplatedFile))
        self.assertEqual('/etc/security/limits.d/10.hardcore.conf',
                         audit.paths[0])

    @patch.object(limits.utils, 'get_defaults', lambda x: {
        'security': {'kernel_enable_core_dump': True}
    })
    def test_core_dump_enabled(self):
        audits = limits.get_audits()
        self.assertEqual(1, len(audits))
        self.assertTrue(isinstance(audits[0], limits.DirectoryPermissionAudit))
