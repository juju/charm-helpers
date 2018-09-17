# Copyright 2014-2017 Canonical Limited.
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
import charmhelpers.fetch.snap as fetch_snap

__author__ = 'Joseph Borg <joseph.borg@canonical.com>'

TEST_ENV = {'foo': 'bar'}


class SnapTest(TestCase):
    """
    Test and install and removal of a snap.
    """
    @patch.object(fetch_snap, 'log', lambda *args, **kwargs: None)
    @patch('subprocess.check_call')
    @patch('os.environ', TEST_ENV)
    def testSnapInstall(self, check_call):
        """
        Test snap install.

        :param check_call: Mock object
        :return: None
        """
        check_call.return_value = 0
        fetch_snap.snap_install(['hello-world', 'htop'], '--classic', '--stable')
        check_call.assert_called_with(['snap', 'install', '--classic', '--stable', 'hello-world', 'htop'], env=TEST_ENV)

    @patch.object(fetch_snap, 'log', lambda *args, **kwargs: None)
    @patch('subprocess.check_call')
    @patch('os.environ', TEST_ENV)
    def testSnapRefresh(self, check_call):
        """
        Test snap refresh.

        :param check_call: Mock object
        :return: None
        """
        check_call.return_value = 0
        fetch_snap.snap_refresh(['hello-world', 'htop'], '--classic', '--stable')
        check_call.assert_called_with(['snap', 'refresh', '--classic', '--stable', 'hello-world', 'htop'], env=TEST_ENV)

    @patch.object(fetch_snap, 'log', lambda *args, **kwargs: None)
    @patch('subprocess.check_call')
    @patch('os.environ', TEST_ENV)
    def testSnapRemove(self, check_call):
        """
        Test snap remove.

        :param check_call: Mock object
        :return: None
        """
        check_call.return_value = 0
        fetch_snap.snap_remove(['hello-world', 'htop'])
        check_call.assert_called_with(['snap', 'remove', 'hello-world', 'htop'], env=TEST_ENV)

    def test_valid_snap_channel(self):
        """ Test valid snap channel

        :return: None
        """
        # Valid
        self.assertTrue(fetch_snap.valid_snap_channel('edge'))

        # Invalid
        with self.assertRaises(fetch_snap.InvalidSnapChannel):
            fetch_snap.valid_snap_channel('DOESNOTEXIST')
