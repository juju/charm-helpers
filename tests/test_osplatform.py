#
# Copyright (C) 2024 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
try:
    import unittest.mock as mock
except ImportError:
    import mock

from charmhelpers import osplatform


class TestPlatform(unittest.TestCase):

    @mock.patch.object(osplatform, "_get_current_platform")
    def test_get_platform_ubuntu(self, _platform):
        _platform.return_value = "Ubuntu"
        self.assertEqual("ubuntu", osplatform.get_platform())

    @mock.patch.object(osplatform, "_get_current_platform")
    def test_get_platform_centos(self, _platform):
        _platform.return_value = "CentOS"
        self.assertEqual("centos", osplatform.get_platform())

    @mock.patch.object(osplatform, "_get_current_platform")
    def test_get_platform_debian(self, _platform):
        _platform.return_value = "debian gnu/linux"
        self.assertEqual("ubuntu", osplatform.get_platform())

        _platform.return_value = "Debian GNU/Linux"
        self.assertEqual("ubuntu", osplatform.get_platform())

    @mock.patch.object(osplatform, "_get_current_platform")
    def test_get_platform_elementary(self, _platform):
        _platform.return_value = "elementary linux"
        self.assertEqual("ubuntu", osplatform.get_platform())

    @mock.patch.object(osplatform, "_get_current_platform")
    def test_get_platform_pop_os(self, _platform):
        _platform.return_value = "Pop!_OS"
        self.assertEqual("ubuntu", osplatform.get_platform())

    @mock.patch.object(osplatform, "_get_current_platform")
    def test_get_platform_unknown(self, _platform):
        _platform.return_value = "crazy custom flavor"
        self.assertRaises(RuntimeError, osplatform.get_platform)

    @mock.patch.object(osplatform, "_get_platform_from_fs")
    @mock.patch.object(osplatform, "platform")
    def test_get_current_platform_module(self, _platform, _platform_from_fs):
        _platform.linux_distribution.return_value = ("Ubuntu", "test")
        self.assertEqual("Ubuntu", osplatform._get_current_platform())
        _platform_from_fs.assert_not_called()

    @mock.patch.object(osplatform, "_get_platform_from_fs")
    @mock.patch.object(osplatform, "platform")
    def test_get_current_platform_fs(self, _platform, _platform_from_fs):
        # make sure hasattr says False
        del _platform.linux_distribution
        _platform_from_fs.return_value = "foobar"
        self.assertEqual("foobar", osplatform._get_current_platform())
