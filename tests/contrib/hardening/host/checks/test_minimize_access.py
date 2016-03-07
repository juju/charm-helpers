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

from charmhelpers.contrib.hardening.host.checks import minimize_access


class MinimizeAccessTestCase(TestCase):

    @patch.object(minimize_access.utils, 'get_defaults', lambda x:
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

    @patch.object(minimize_access.utils, 'get_defaults', lambda x:
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
