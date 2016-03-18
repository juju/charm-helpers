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

import shutil
import tempfile

from unittest import TestCase
from mock import patch

from charmhelpers.contrib.hardening.apache.checks import config

TEST_TMPDIR = None
APACHE_VERSION_STR = """Server version: Apache/2.4.7 (Ubuntu)
Server built:   Jan 14 2016 17:45:23
"""


class ApacheConfigTestCase(TestCase):

    def setUp(self):
        global TEST_TMPDIR
        TEST_TMPDIR = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(TEST_TMPDIR)

    @patch.object(config.subprocess, 'call', lambda *args, **kwargs: 1)
    def test_get_audits_apache_not_installed(self):
        audits = config.get_audits()
        self.assertEqual([], audits)

    @patch.object(config.utils, 'get_settings', lambda x: {
        'common': {'apache_dir': TEST_TMPDIR,
                   'traceenable': 'Off'},
        'hardening': {
            'allowed_http_methods': {'GOGETEM'},
            'modules_to_disable': {'modfoo'}
        }
    })
    @patch.object(config.subprocess, 'call', lambda *args, **kwargs: 0)
    def test_get_audits_apache_is_installed(self):
        audits = config.get_audits()
        self.assertEqual(6, len(audits))

    @patch.object(config.utils, 'get_settings', lambda x: {
        'common': {'apache_dir': TEST_TMPDIR},
        'hardening': {
            'allowed_http_methods': {'GOGETEM'},
            'modules_to_disable': {'modfoo'},
            'traceenable': 'off'
        }
    })
    @patch.object(config, 'subprocess')
    def test_ApacheConfContext(self, mock_subprocess):
        mock_subprocess.call.return_value = 0

        with tempfile.NamedTemporaryFile() as ftmp:
            def fake_check_output(cmd, *args, **kwargs):
                if cmd[0] == 'apache2':
                    return APACHE_VERSION_STR

            mock_subprocess.check_output.side_effect = fake_check_output
            ctxt = config.ApacheConfContext()
            self.assertEqual(ctxt(), {'allowed_http_methods': set(['GOGETEM']),
                                      'apache_icondir':
                                      '/usr/share/apache2/icons/',
                                      'apache_version': '2.4.7',
                                      'modules_to_disable': set(['modfoo']),
                                      'traceenable': 'off'})
