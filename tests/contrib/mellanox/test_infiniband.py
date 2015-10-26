#!/usr/bin/env python

from charmhelpers.contrib.mellanox import infiniband

from mock import patch, call
import unittest

TO_PATCH = [
    "log",
    "INFO",
    "apt_install",
    "apt_update",
    "modprobe",
    "network_interfaces"
]

NETWORK_INTERFACES = [
    'lo',
    'eth0',
    'eth1',
    'eth2',
    'eth3',
    'eth4',
    'juju-br0',
    'ib0',
    'virbr0',
    'ovs-system',
    'br-int',
    'br-ex',
    'br-data',
    'phy-br-data',
    'int-br-data',
    'br-tun'
]


IBSTAT_OUTPUT = """
CA 'mlx4_0'
    CA type: MT4103
    Number of ports: 2
    Firmware version: 2.33.5000
    Hardware version: 0
    Node GUID: 0xe41d2d03000a1120
    System image GUID: 0xe41d2d03000a1123
"""


class InfinibandTest(unittest.TestCase):

    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.mellanox.infiniband.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_load_modules(self):
        infiniband.load_modules()

        self.modprobe.assert_has_calls(map(lambda x: call(x, persist=True),
                                           infiniband.REQUIRED_MODULES))

    def test_install_packages(self):
        infiniband.install_packages()

        self.apt_update.assert_is_called_once()
        self.apt_install.assert_is_called_once()

    @patch("os.path.exists")
    def test_is_enabled(self, exists):
        exists.return_value = True
        self.assertTrue(infiniband.is_enabled())

    @patch("subprocess.check_output")
    def test_stat(self, check_output):
        infiniband.stat()

        check_output.assert_called_with(["ibstat"])

    @patch("subprocess.check_output")
    def test_devices(self, check_output):
        infiniband.devices()

        check_output.assert_called_with(["ibstat", "-l"])

    @patch("subprocess.check_output")
    def test_device_info(self, check_output):
        check_output.return_value = IBSTAT_OUTPUT

        info = infiniband.device_info("mlx4_0")

        self.assertEquals(info.num_ports, "2")
        self.assertEquals(info.device_type, "MT4103")
        self.assertEquals(info.fw_ver, "2.33.5000")
        self.assertEquals(info.hw_ver, "0")
        self.assertEquals(info.node_guid, "0xe41d2d03000a1120")
        self.assertEquals(info.sys_guid, "0xe41d2d03000a1123")

    @patch("subprocess.check_output")
    def test_ipoib_interfaces(self, check_output):
        self.network_interfaces.return_value = NETWORK_INTERFACES

        ipoib_nic = "ib0"

        def c(*args, **kwargs):
            if ipoib_nic in args[0]:
                return "driver: ib_ipoib"
            else:
                return "driver: mock"

        check_output.side_effect = c
        self.assertEquals(infiniband.ipoib_interfaces(), [ipoib_nic])
