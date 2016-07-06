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

from mock import patch
from unittest import TestCase

from charmhelpers.contrib.hardening import harden


class HardenTestCase(TestCase):

    def setUp(self):
        super(HardenTestCase, self).setUp()

    @patch.object(harden, 'run_apache_checks')
    @patch.object(harden, 'run_mysql_checks')
    @patch.object(harden, 'run_ssh_checks')
    @patch.object(harden, 'run_os_checks')
    @patch.object(harden, 'log', lambda *args, **kwargs: None)
    def test_harden(self, mock_host, mock_ssh, mock_mysql, mock_apache):
        mock_host.__name__ = 'host'
        mock_ssh.__name__ = 'ssh'
        mock_mysql.__name__ = 'mysql'
        mock_apache.__name__ = 'apache'

        @harden.harden(overrides=['ssh', 'mysql'])
        def foo(arg1, kwarg1=None):
            return "done."

        self.assertEqual(foo('anarg', kwarg1='akwarg'), "done.")
        self.assertTrue(mock_ssh.called)
        self.assertTrue(mock_mysql.called)
        self.assertFalse(mock_apache.called)
        self.assertFalse(mock_host.called)
