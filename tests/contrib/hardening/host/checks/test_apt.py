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

from mock import patch

from charmhelpers.contrib.hardening.host.checks import apt


class AptHardeningTestCase(TestCase):

    @patch.object(apt, 'get_defaults', lambda x: {
        'security': {'packages_clean': False}
    })
    def test_dont_clean_packages(self):
        audits = apt.get_audits()
        self.assertEqual(1, len(audits))

    @patch.object(apt, 'get_defaults', lambda x: {
        'security': {'packages_clean': True,
                     'packages_list': []}
    })
    def test_no_security_packages(self):
        audits = apt.get_audits()
        self.assertEqual(1, len(audits))

    @patch.object(apt, 'get_defaults', lambda x: {
        'security': {'packages_clean': True,
                     'packages_list': ['foo', 'bar']}
    })
    def test_restricted_packages(self):
        audits = apt.get_audits()
        self.assertEqual(2, len(audits))
        self.assertTrue(isinstance(audits[1], apt.RestrictedPackages))
