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

__author__ = 'Joseph Borg <joseph.borg@canonical.com>'


class SnapTest(TestCase):
    """
    Test and install and removal of a snap.
    """
    @patch('subprocess.Popen')
    def testSnapInstall(self, popen):
        """
        Test snap install.
        :return: None
        """
        from charmhelpers.contrib.snap import snap_install
        popen.return_value.returncode = 0
        snap_install(['hello-world', 'htop'], '--classic', '--stable')
        popen.assert_called_with(['snap', 'install', '--classic', '--stable', 'hello-world', 'htop'])

    @patch('subprocess.Popen')
    def testSnapRefresh(self, popen):
        """
        Test snap refresh.
        :return: None
        """
        from charmhelpers.contrib.snap import snap_refresh
        popen.return_value.returncode = 0
        snap_refresh(['hello-world', 'htop'], '--classic', '--stable')
        popen.assert_called_with(['snap', 'refresh', '--classic', '--stable', 'hello-world', 'htop'])

    @patch('subprocess.Popen')
    def testSnapRemove(self, popen):
        """
        Test snap refresh.
        :return: None
        """
        from charmhelpers.contrib.snap import snap_remove
        popen.return_value.returncode = 0
        snap_remove(['hello-world', 'htop'])
        popen.assert_called_with(['snap', 'remove', 'hello-world', 'htop'])