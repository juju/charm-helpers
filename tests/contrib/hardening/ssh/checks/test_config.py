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

from testtools import TestCase

from mock import patch

from charmhelpers.contrib.hardening.ssh.checks import config


class SSHConfigTestCase(TestCase):

    @patch.object(config.utils, 'get_settings', lambda x: {})
    def test_dont_clean_packages(self):
        audits = config.get_audits()
        self.assertEqual(4, len(audits))
