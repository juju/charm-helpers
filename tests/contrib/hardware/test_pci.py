# Copyright 2016 Canonical Ltd
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

from tests.contrib.hardware.test_utils import CharmTestCase
from tests.contrib.hardware.test_utils import patch_open

from tests.contrib.hardware.test_pci_helper import check_device
from tests.contrib.hardware.test_pci_helper import mocked_filehandle
from tests.contrib.hardware.test_pci_helper import mocked_globs
from tests.contrib.hardware.test_pci_helper import mocked_islink
from tests.contrib.hardware.test_pci_helper import mocked_listdir
from tests.contrib.hardware.test_pci_helper import mocked_realpath
from tests.contrib.hardware.test_pci_helper import mocked_subprocess

from mock import call
from mock import MagicMock
from mock import patch

from charmhelpers.contrib.hardware import pci

TO_PATCH = ["glob", "subprocess"]
NOT_JSON = "Im not json"


class PCITest(CharmTestCase):
    def setUp(self):
        super(PCITest, self).setUp(pci, TO_PATCH)

    def test_format_pci_addr(self):
        self.assertEqual(pci.format_pci_addr("0:0:1.1"), "0000:00:01.1")
        self.assertEqual(pci.format_pci_addr("0000:00:02.1"), "0000:00:02.1")


class PCINetDeviceTest(CharmTestCase):
    def setUp(self):
        super(PCINetDeviceTest, self).setUp(pci, TO_PATCH)

    @patch("os.path.islink")
    @patch("os.path.realpath")
    def eth_int(self, pci_address, _osrealpath, _osislink, subproc_map=None):
        self.glob.glob.side_effect = mocked_globs
        _osislink.side_effect = mocked_islink
        _osrealpath.side_effect = mocked_realpath
        self.subprocess.check_output.side_effect = mocked_subprocess(
            subproc_map=subproc_map
        )

        with patch_open() as (_open, _file):
            super_fh = mocked_filehandle()
            _file.readlines = MagicMock()
            _open.side_effect = super_fh._setfilename
            _file.read.side_effect = super_fh._getfilecontents_read
            _file.readlines.side_effect = super_fh._getfilecontents_readlines
            netint = pci.PCINetDevice(pci_address)
        return netint

    @patch("os.listdir")
    def test_base_eth_device(self, _oslistdir):
        _oslistdir.side_effect = mocked_listdir
        net = self.eth_int("0000:10:00.0")
        expect = {
            "interface_name": "eth2",
            "mac_address": "a8:9d:21:cf:93:fc",
            "pci_address": "0000:10:00.0",
            "state": "up",
            "sriov": False,
        }
        self.assertTrue(check_device(net, expect))

    @patch("charmhelpers.contrib.hardware.pci.get_sysnet_interfaces_and_macs")
    @patch("charmhelpers.contrib.hardware.pci.PCINetDevice.update_attributes")
    def test_update_interface_info(self, _update, _sysnet_ints):
        dev = pci.PCINetDevice("0000:10:00.0")
        _sysnet_ints.return_value = [
            {
                "interface": "eth2",
                "mac_address": "a8:9d:21:cf:93:fc",
                "pci_address": "0000:10:00.0",
                "state": "up",
                "sriov": False,
            },
            {
                "interface": "eth3",
                "mac_address": "a8:9d:21:cf:93:fd",
                "pci_address": "0000:10:00.1",
                "state": "down",
                "sriov": False,
            },
        ]
        dev.update_interface_info()
        self.assertEqual(dev.interface_name, "eth2")

    @patch("os.path.islink")
    @patch("os.path.realpath")
    @patch("charmhelpers.contrib.hardware.pci.is_sriov")
    @patch("charmhelpers.contrib.hardware.pci.get_sysnet_device_state")
    @patch("charmhelpers.contrib.hardware.pci.get_sysnet_mac")
    @patch("charmhelpers.contrib.hardware.pci.get_sysnet_interface")
    @patch("charmhelpers.contrib.hardware.pci.PCINetDevice.update_attributes")
    def test_get_sysnet_interfaces_and_macs(
        self, _update, _interface, _mac, _state, _sriov, _osrealpath, _osislink
    ):
        self.glob.glob.side_effect = (
            ["/sys/bus/pci/devices/0000:10:00.0"],
            [])
        _interface.return_value = "eth2"
        _mac.return_value = "a8:9d:21:cf:93:fc"
        _state.return_value = "up"
        _sriov.return_value = False
        _osrealpath.return_value = (
            "/sys/devices/pci0000:00/0000:00:02.0/"
            "0000:02:00.0/0000:03:00.0/0000:04:00.0/"
            "0000:05:01.0/0000:07:00.0"
        )
        expect = {
            "interface": "eth2",
            "mac_address": "a8:9d:21:cf:93:fc",
            "pci_address": "0000:07:00.0",
            "state": "up",
            "sriov": False,
        }
        self.assertEqual(pci.get_sysnet_interfaces_and_macs(), [expect])

    @patch("os.path.islink")
    @patch("os.path.realpath")
    @patch("charmhelpers.contrib.hardware.pci.is_sriov")
    @patch("charmhelpers.contrib.hardware.pci.get_sysnet_device_state")
    @patch("charmhelpers.contrib.hardware.pci.get_sysnet_mac")
    @patch("charmhelpers.contrib.hardware.pci.get_sysnet_interface")
    @patch("charmhelpers.contrib.hardware.pci.PCINetDevice.update_attributes")
    def test_get_sysnet_interfaces_and_macs_virtio(
        self, _update, _interface, _mac, _state, _sriov, _osrealpath, _osislink
    ):
        self.glob.glob.side_effect = (
            ["/sys/bus/pci/devices/0000:10:00.0"],
            [])
        _interface.return_value = "eth2"
        _mac.return_value = "a8:9d:21:cf:93:fc"
        _state.return_value = "up"
        _sriov.return_value = False
        _osrealpath.return_value = (
            "/sys/devices/pci0000:00/0000:00:07.0/" "virtio5"
        )
        expect = {
            "interface": "eth2",
            "mac_address": "a8:9d:21:cf:93:fc",
            "pci_address": "0000:00:07.0",
            "state": "up",
            "sriov": False,
        }
        self.assertEqual(pci.get_sysnet_interfaces_and_macs(), [expect])

    @patch("charmhelpers.contrib.hardware.pci.PCINetDevice.update_attributes")
    def test_get_sysnet_mac(self, _update):
        with patch_open() as (_open, _file):
            super_fh = mocked_filehandle()
            _file.readlines = MagicMock()
            _open.side_effect = super_fh._setfilename
            _file.read.side_effect = super_fh._getfilecontents_read
            macaddr = pci.get_sysnet_mac(
                "/sys/bus/pci/devices/0000:10:00.1", "eth3")
        self.assertEqual(macaddr, "a8:9d:21:cf:93:fd")

    @patch("charmhelpers.contrib.hardware.pci.PCINetDevice.update_attributes")
    def test_get_sysnet_device_state(self, _update):
        with patch_open() as (_open, _file):
            super_fh = mocked_filehandle()
            _file.readlines = MagicMock()
            _open.side_effect = super_fh._setfilename
            _file.read.side_effect = super_fh._getfilecontents_read
            state = pci.get_sysnet_device_state(
                "/sys/bus/pci/devices/0000:10:00.1", "eth3")
        self.assertEqual(state, "down")

    @patch("os.listdir")
    @patch("charmhelpers.contrib.hardware.pci.PCINetDevice.update_attributes")
    def test_get_sysnet_interface(self, _update, _oslistdir):
        _oslistdir.side_effect = mocked_listdir
        with patch_open() as (_open, _file):
            super_fh = mocked_filehandle()
            _file.readlines = MagicMock()
            _open.side_effect = super_fh._setfilename
            _file.read.side_effect = super_fh._getfilecontents_read
            self.assertEqual(
                pci.get_sysnet_interface("/sys/bus/pci/devices/0000:10:00.1"),
                "eth3"
            )

    @patch("charmhelpers.contrib.hardware.pci.get_sysnet_interfaces_and_macs")
    def test__set_sriov_numvfs(self, mock_sysnet_ints):
        mock_sysnet_ints.side_effect = (
            [
                {
                    "interface": "eth2",
                    "mac_address": "a8:9d:21:cf:93:fc",
                    "pci_address": "0000:10:00.0",
                    "state": "up",
                    "sriov": True,
                    "sriov_totalvfs": 7,
                    "sriov_numvfs": 0,
                }
            ],
            [
                {
                    "interface": "eth2",
                    "mac_address": "a8:9d:21:cf:93:fc",
                    "pci_address": "0000:10:00.0",
                    "state": "up",
                    "sriov": True,
                    "sriov_totalvfs": 7,
                    "sriov_numvfs": 4,
                }
            ],
        )
        dev = pci.PCINetDevice("0000:10:00.0")
        self.assertEqual("eth2", dev.interface_name)
        self.assertTrue(dev.sriov)
        self.assertEqual(7, dev.sriov_totalvfs)
        self.assertEqual(0, dev.sriov_numvfs)

        with patch_open() as (mock_open, mock_file):
            dev._set_sriov_numvfs(4)
            mock_open.assert_called_with(
                "/sys/bus/pci/devices/0000:10:00.0/sriov_numvfs", "w"
            )
            mock_file.write.assert_called_with("4")
            self.assertTrue(dev.sriov)
            self.assertEqual(7, dev.sriov_totalvfs)
            self.assertEqual(4, dev.sriov_numvfs)

    @patch("charmhelpers.contrib.hardware.pci.PCINetDevice._set_sriov_numvfs")
    def test_set_sriov_numvfs(self, mock__set_sriov_numvfs):
        dev = pci.PCINetDevice("0000:10:00.0")
        dev.sriov = True
        dev.set_sriov_numvfs(4)
        mock__set_sriov_numvfs.assert_has_calls([call(0), call(4)])

    @patch("charmhelpers.contrib.hardware.pci.PCINetDevice._set_sriov_numvfs")
    def test_set_sriov_numvfs_avoid_call(self, mock__set_sriov_numvfs):
        dev = pci.PCINetDevice("0000:10:00.0")
        dev.sriov = True
        dev.sriov_numvfs = 4
        dev.set_sriov_numvfs(4)
        self.assertFalse(mock__set_sriov_numvfs.called)


class PCINetDevicesTest(CharmTestCase):
    def setUp(self):
        super(PCINetDevicesTest, self).setUp(pci, TO_PATCH)

    @patch("os.path.islink")
    def pci_devs(self, _osislink, subproc_map=None):
        self.glob.glob.side_effect = mocked_globs
        rp_patcher = patch("os.path.realpath")
        rp_mock = rp_patcher.start()
        rp_mock.side_effect = mocked_realpath
        _osislink.side_effect = mocked_islink
        self.subprocess.check_output.side_effect = mocked_subprocess(
            subproc_map=subproc_map
        )
        listdir_patch = patch("os.listdir")
        listdir_mock = listdir_patch.start()
        listdir_mock.side_effect = mocked_listdir

        with patch_open() as (_open, _file):
            super_fh = mocked_filehandle()
            _file.readlines = MagicMock()
            _open.side_effect = super_fh._setfilename
            _file.read.side_effect = super_fh._getfilecontents_read
            _file.readlines.side_effect = super_fh._getfilecontents_readlines
            devices = pci.PCINetDevices()
        rp_patcher.stop()
        listdir_patch.stop()
        return devices

    def test_base(self):
        devices = self.pci_devs()
        self.assertEqual(len(devices.pci_devices), 2)
        expect = {
            "0000:10:00.0": {
                "interface_name": "eth2",
                "mac_address": "a8:9d:21:cf:93:fc",
                "pci_address": "0000:10:00.0",
                "state": "up",
                "sriov": False,
            },
            "0000:10:00.1": {
                "interface_name": "eth3",
                "mac_address": "a8:9d:21:cf:93:fd",
                "pci_address": "0000:10:00.1",
                "state": "down",
                "sriov": False,
            },
        }
        for device in devices.pci_devices:
            self.assertTrue(check_device(device, expect[device.pci_address]))

    def test_get_pci_ethernet_addresses(self):
        self.pci_devs()
        expect = ["0000:10:00.0", "0000:10:00.1"]
        self.assertEqual(pci.get_pci_ethernet_addresses(), expect)

    @patch("charmhelpers.contrib.hardware.pci.PCINetDevice.update_attributes")
    def test_update_devices(self, _update):
        devices = self.pci_devs()
        call_count = _update.call_count
        devices.update_devices()
        self.assertEqual(_update.call_count, call_count + 2)

    def test_get_macs(self):
        devices = self.pci_devs()
        expect = ["a8:9d:21:cf:93:fc", "a8:9d:21:cf:93:fd"]
        self.assertEqual(devices.get_macs(), expect)

    def test_get_device_from_mac(self):
        devices = self.pci_devs()
        expect = {
            "0000:10:00.1": {
                "interface_name": "eth3",
                "mac_address": "a8:9d:21:cf:93:fd",
                "pci_address": "0000:10:00.1",
                "state": "down",
                "sriov": False,
            }
        }
        self.assertTrue(
            check_device(
                devices.get_device_from_mac("a8:9d:21:cf:93:fd"),
                expect["0000:10:00.1"],
            )
        )

    def test_get_device_from_pci_address(self):
        devices = self.pci_devs()
        expect = {
            "0000:10:00.1": {
                "interface_name": "eth3",
                "mac_address": "a8:9d:21:cf:93:fd",
                "pci_address": "0000:10:00.1",
                "state": "down",
            }
        }
        self.assertTrue(
            check_device(
                devices.get_device_from_pci_address("0000:10:00.1"),
                expect["0000:10:00.1"],
            )
        )
