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

from charmhelpers.contrib.hardening.host.checks import pam


class PAMTestCase(TestCase):

    @patch.object(pam.utils, 'get_defaults', lambda x: {
        'auth': {'pam_passwdqc_enable': True,
                 'retries': False}
    })
    def test_enable_passwdqc(self):
        audits = pam.get_audits()
        self.assertEqual(2, len(audits))
        audit = audits[0]
        self.assertTrue(isinstance(audit, pam.PasswdqcPAM))
        audit = audits[1]
        self.assertTrue(isinstance(audit, pam.DeletedFile))
        self.assertEqual('/usr/share/pam-configs/tally2', audit.paths[0])

    @patch.object(pam.utils, 'get_defaults', lambda x: {
        'auth': {'pam_passwdqc_enable': False,
                 'retries': True}
    })
    def test_disable_passwdqc(self):
        audits = pam.get_audits()
        self.assertEqual(1, len(audits))
        self.assertFalse(isinstance(audits[0], pam.PasswdqcPAM))

    @patch.object(pam.utils, 'get_defaults', lambda x: {
        'auth': {'pam_passwdqc_enable': False,
                 'retries': True}
    })
    def test_auth_retries(self):
        audits = pam.get_audits()
        self.assertEqual(1, len(audits))
        self.assertTrue(isinstance(audits[0], pam.Tally2PAM))
