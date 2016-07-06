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

from mock import patch

from charmhelpers.contrib.hardening.host.checks import apt


class AptHardeningTestCase(TestCase):

    @patch.object(apt, 'get_settings', lambda x: {
        'security': {'packages_clean': False}
    })
    def test_dont_clean_packages(self):
        audits = apt.get_audits()
        self.assertEqual(1, len(audits))

    @patch.object(apt, 'get_settings', lambda x: {
        'security': {'packages_clean': True,
                     'packages_list': []}
    })
    def test_no_security_packages(self):
        audits = apt.get_audits()
        self.assertEqual(1, len(audits))

    @patch.object(apt, 'get_settings', lambda x: {
        'security': {'packages_clean': True,
                     'packages_list': ['foo', 'bar']}
    })
    def test_restricted_packages(self):
        audits = apt.get_audits()
        self.assertEqual(2, len(audits))
        self.assertTrue(isinstance(audits[1], apt.RestrictedPackages))
