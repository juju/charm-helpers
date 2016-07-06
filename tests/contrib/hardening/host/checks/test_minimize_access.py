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

from charmhelpers.contrib.hardening.host.checks import minimize_access


class MinimizeAccessTestCase(TestCase):

    @patch.object(minimize_access.utils, 'get_settings', lambda x:
                  {'environment': {'extra_user_paths': []},
                   'security': {'users_allow': []}})
    def test_default_options(self):
        audits = minimize_access.get_audits()
        self.assertEqual(3, len(audits))

        # First audit is to ensure that all folders in the $PATH variable
        # are read-only.
        self.assertTrue(isinstance(audits[0], minimize_access.ReadOnly))
        self.assertEqual({'/usr/local/sbin', '/usr/local/bin',
                          '/usr/sbin', '/usr/bin', '/bin'}, audits[0].paths)

        # Second audit is to ensure that the /etc/shadow is only readable
        # by the root user.
        self.assertTrue(isinstance(audits[1],
                                   minimize_access.FilePermissionAudit))
        self.assertEqual(audits[1].paths[0], '/etc/shadow')
        self.assertEqual(audits[1].mode, 0o0600)

        # Last audit is to ensure that only root has access to the su
        self.assertTrue(isinstance(audits[2],
                                   minimize_access.FilePermissionAudit))
        self.assertEqual(audits[2].paths[0], '/bin/su')
        self.assertEqual(audits[2].mode, 0o0750)

    @patch.object(minimize_access.utils, 'get_settings', lambda x:
                  {'environment': {'extra_user_paths': []},
                   'security': {'users_allow': ['change_user']}})
    def test_allow_change_user(self):
        audits = minimize_access.get_audits()
        self.assertEqual(2, len(audits))

        # First audit is to ensure that all folders in the $PATH variable
        # are read-only.
        self.assertTrue(isinstance(audits[0], minimize_access.ReadOnly))
        self.assertEqual({'/usr/local/sbin', '/usr/local/bin',
                          '/usr/sbin', '/usr/bin', '/bin'}, audits[0].paths)

        # Second audit is to ensure that the /etc/shadow is only readable
        # by the root user.
        self.assertTrue(isinstance(audits[1],
                                   minimize_access.FilePermissionAudit))
        self.assertEqual(audits[1].paths[0], '/etc/shadow')
        self.assertEqual(audits[1].mode, 0o0600)
