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

import os
import shutil
import tempfile

from unittest import TestCase
from mock import patch

from charmhelpers.contrib.hardening.apache.checks import config

TEST_TMPDIR = None
APACHE_VERSION_STR = b"""Server version: Apache/2.4.7 (Ubuntu)
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
        self.assertEqual(7, len(audits))

    @patch.object(config.utils, 'get_settings', lambda x: {
        'common': {'apache_dir': TEST_TMPDIR},
        'hardening': {
            'allowed_http_methods': {'GOGETEM'},
            'modules_to_disable': {'modfoo'},
            'traceenable': 'off',
            'servertokens': 'Prod',
            'honor_cipher_order': 'on',
            'cipher_suite': 'ALL:+MEDIUM:+HIGH:!LOW:!MD5:!RC4:!eNULL:!aNULL:!3DES'
        }
    })
    @patch.object(config, 'subprocess')
    def test_ApacheConfContext(self, mock_subprocess):
        mock_subprocess.call.return_value = 0

        with tempfile.NamedTemporaryFile() as ftmp:  # noqa
            def fake_check_output(cmd, *args, **kwargs):
                if cmd[0] == 'apache2':
                    return APACHE_VERSION_STR

            mock_subprocess.check_output.side_effect = fake_check_output
            ctxt = config.ApacheConfContext()
            self.assertEqual(ctxt(), {
                'allowed_http_methods': set(['GOGETEM']),
                'apache_icondir':
                '/usr/share/apache2/icons/',
                'apache_version': '2.4.7',
                'modules_to_disable': set(['modfoo']),
                'servertokens': 'Prod',
                'traceenable': 'off',
                'honor_cipher_order': 'on',
                'cipher_suite': 'ALL:+MEDIUM:+HIGH:!LOW:!MD5:!RC4:!eNULL:!aNULL:!3DES'
            })

    @patch.object(config.utils, 'get_settings', lambda x: {
        'common': {'apache_dir': TEST_TMPDIR},
        'hardening': {
            'allowed_http_methods': {'GOGETEM'},
            'modules_to_disable': {'modfoo'},
            'traceenable': 'off',
            'servertokens': 'Prod',
            'honor_cipher_order': 'on',
            'cipher_suite': 'ALL:+MEDIUM:+HIGH:!LOW:!MD5:!RC4:!eNULL:!aNULL:!3DES'
        }
    })
    @patch.object(config.subprocess, 'call', lambda *args, **kwargs: 0)
    def test_file_permission_audit(self):
        audits = config.get_audits()
        settings = config.utils.get_settings('apache')
        conf_file_name = 'apache2.conf'
        conf_file_path = os.path.join(
            settings['common']['apache_dir'], conf_file_name
        )
        self.assertEqual(audits[0].paths[0], conf_file_path)
