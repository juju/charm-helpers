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
import tempfile

from testtools import TestCase

from mock import call
from mock import patch

from charmhelpers.contrib.hardening.host.checks import suid_sgid


@patch.object(suid_sgid, 'log', lambda *args, **kwargs: None)
class SUIDSGIDTestCase(TestCase):

    @patch.object(suid_sgid.utils, 'get_defaults', lambda x: {
        'security': {'suid_sgid_enforce': False}
    })
    def test_no_enforcement(self):
        audits = suid_sgid.get_audits()
        self.assertEqual(0, len(audits))

    @patch.object(suid_sgid, 'subprocess')
    @patch.object(suid_sgid.utils, 'get_defaults', lambda x: {
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
