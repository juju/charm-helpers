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

import tempfile

from unittest import TestCase

from mock import call
from mock import patch

from charmhelpers.contrib.hardening.host.checks import suid_sgid


@patch.object(suid_sgid, 'log', lambda *args, **kwargs: None)
class SUIDSGIDTestCase(TestCase):

    @patch.object(suid_sgid.utils, 'get_settings', lambda x: {
        'security': {'suid_sgid_enforce': False}
    })
    def test_no_enforcement(self):
        audits = suid_sgid.get_audits()
        self.assertEqual(0, len(audits))

    @patch.object(suid_sgid, 'subprocess')
    @patch.object(suid_sgid.utils, 'get_settings', lambda x: {
        'security': {'suid_sgid_enforce': True,
                     'suid_sgid_remove_from_unknown': True,
                     'suid_sgid_blacklist': [],
                     'suid_sgid_whitelist': [],
                     'suid_sgid_dry_run_on_unknown': True},
        'environment': {'root_path': '/'}
    })
    def test_suid_guid_harden(self, mock_subprocess):
        p = mock_subprocess.Popen.return_value
        with tempfile.NamedTemporaryFile() as tmp:
            p.communicate.return_value = (tmp.name, "stderr")

        audits = suid_sgid.get_audits()
        self.assertEqual(2, len(audits))
        cmd = ['find', '/', '-perm', '-4000', '-o', '-perm', '-2000', '-type',
               'f', '!', '-path', '/proc/*', '-print']
        calls = [call(cmd, stderr=mock_subprocess.PIPE,
                      stdout=mock_subprocess.PIPE)]
        mock_subprocess.Popen.assert_has_calls(calls)
