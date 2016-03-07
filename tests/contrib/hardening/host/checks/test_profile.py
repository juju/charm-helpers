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

from charmhelpers.contrib.hardening.host.checks import profile


class ProfileTestCase(TestCase):

    @patch.object(profile.utils, 'get_defaults', lambda x:
                  {'security': {'kernel_enable_core_dump': False}})
    def test_core_dump_disabled(self):
        audits = profile.get_audits()
        self.assertEqual(1, len(audits))
        self.assertTrue(isinstance(audits[0], profile.TemplatedFile))

    @patch.object(profile.utils, 'get_defaults', lambda x: {
        'security': {'kernel_enable_core_dump': True}
    })
    def test_core_dump_enabled(self):
        audits = profile.get_audits()
        self.assertEqual(0, len(audits))
