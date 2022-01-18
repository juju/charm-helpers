import mock
import os
import tempfile
import unittest

from charmhelpers.contrib.network.files import check_sriov_numvfs

__author__ = 'Stephan Pampel <stephan.pampel@canonical.com>'


class TestCheckSriovNumfs(unittest.TestCase):

    interface_folder = os.path.join(tempfile.gettempdir(), 'ens3f0')
    sriov_numvfs_file = os.path.join(interface_folder, 'sriov_numvfs')
    sriov_totalvfs_file = os.path.join(interface_folder, 'sriov_totalvfs')

    def __init__(self, *args, **kwargs):
        super(TestCheckSriovNumfs, self).__init__(*args, **kwargs)
        if not os.path.exists(self.interface_folder):
            os.mkdir(self.interface_folder)
        with open(self.sriov_numvfs_file, "w") as f:
            f.write("32")
        with open(self.sriov_totalvfs_file, "w") as f:
            f.write("64")

    def __del__(self):
        if os.path.exists(self.interface_folder):
            for file in os.listdir(self.interface_folder):
                os.remove(os.path.join(self.interface_folder, file))
            os.removedirs(self.interface_folder)

    def test_parameter_parsing(self):
        """Ensure that the format of the sriov_numvfs parameter is parsed correctly"""
        iface, numvfs = check_sriov_numvfs.parse_sriov_numvfs('ens3f0:32')
        self.assertEqual(iface, 'ens3f0')
        self.assertEqual(numvfs, 32)

        for param in ['', ':', ':test', ':32', 'ens3f2', 'a:1:b', 'ens3f2:']:
            self.assertRaises(check_sriov_numvfs.ArgsFormatError, check_sriov_numvfs.parse_sriov_numvfs, param)

        for param in ['ens3f2:test']:
            self.assertRaises(ValueError, check_sriov_numvfs.parse_sriov_numvfs, param)

    def test_check_interface_numvfs_no_interface(self):
        """Check should ignore the interface if it does not exists"""
        self.assertListEqual(
            check_sriov_numvfs.check_interface_numvfs('no-interface', 0), []
        )

    @mock.patch('charmhelpers.contrib.network.files.check_sriov_numvfs.DEVICE_TEMPLATE', interface_folder)
    def test_check_interface_numvfs_vfs_disabled(self):
        """Check should report if virtual functions are disabled """
        self.assertListEqual(
            check_sriov_numvfs.check_interface_numvfs('ens3f0', 0),
            ['ens3f0: VFs are disabled or not-available']
        )

    @mock.patch('charmhelpers.contrib.network.files.check_sriov_numvfs.DEVICE_TEMPLATE', interface_folder)
    @mock.patch('charmhelpers.contrib.network.files.check_sriov_numvfs.SRIOV_NUMVFS_TEMPLATE', sriov_numvfs_file)
    @mock.patch('charmhelpers.contrib.network.files.check_sriov_numvfs.SRIOV_TOTALVFS_TEMPLATE', sriov_totalvfs_file)
    def test_check_interface_numvfs_vfs_enabled(self):
        """Check if numvfs is evaluated correctly"""

        # check numvfs correct should pass
        self.assertListEqual(
            check_sriov_numvfs.check_interface_numvfs('ens3f0', 32),
            []
        )

        # check numvfs != expected should faild
        self.assertListEqual(
            check_sriov_numvfs.check_interface_numvfs('ens3f0', 16),
            ['ens3f0: Number of VFs on interface (32) does not match expected (16)']
        )

        # check numvfs > sriov_totalvfs should fail
        with open(self.sriov_numvfs_file, "w") as f:
            f.write("128")
        self.assertListEqual(
            check_sriov_numvfs.check_interface_numvfs('ens3f0', 128),
            ['ens3f0: Maximum number of VFs available on interface (64) is lower than the expected (128)']
        )
