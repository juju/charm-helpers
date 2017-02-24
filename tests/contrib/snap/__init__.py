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
import subprocess
from mock import call
from unittest import TestCase
from charmhelpers.contrib.snap import snap_install, snap_remove

__author__ = 'Joseph Borg <joseph.borg@canonical.com>'


class SnapTest(TestCase):
    """
    Test and install and removal of a snap.
    """
    def setUp(self):
        """
        Make sure the hello-world snap isn't installed.
        :return: None
        """
        snap_remove('hello-world')

    def testSnapInstall(self):
        """
        Test snap install.
        :return: None
        """
        snap_install('hello-world')
        proc = subprocess.Popen(
            ['/snap/bin/hello-world'],
            stdout=subprocess.PIPE
        )
        proc.wait()

        self.assertEqual(proc.stdout.read(), b'Hello World!\n')

        proc.stdout.close()

    def tearDown(self):
        """
        Remove test snap.
        :return: None
        """
        snap_remove('hello-world')
