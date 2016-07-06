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

from charmhelpers.contrib.hardening.host.checks import pam


class PAMTestCase(TestCase):

    @patch.object(pam.utils, 'get_settings', lambda x: {
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

    @patch.object(pam.utils, 'get_settings', lambda x: {
        'auth': {'pam_passwdqc_enable': False,
                 'retries': True}
    })
    def test_disable_passwdqc(self):
        audits = pam.get_audits()
        self.assertEqual(1, len(audits))
        self.assertFalse(isinstance(audits[0], pam.PasswdqcPAM))

    @patch.object(pam.utils, 'get_settings', lambda x: {
        'auth': {'pam_passwdqc_enable': False,
                 'retries': True}
    })
    def test_auth_retries(self):
        audits = pam.get_audits()
        self.assertEqual(1, len(audits))
        self.assertTrue(isinstance(audits[0], pam.Tally2PAM))
