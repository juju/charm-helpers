from mock import patch
import unittest

import charmhelpers.contrib.storage.linux.utils as storage_utils

# It's a mouthful.
STORAGE_LINUX_UTILS = 'charmhelpers.contrib.storage.linux.utils'


class MiscStorageUtilsTests(unittest.TestCase):

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    @patch(STORAGE_LINUX_UTILS + '.call')
    @patch(STORAGE_LINUX_UTILS + '.check_call')
    def test_zap_disk(self, check_call, call, check_output):
        """It calls sgdisk correctly to zap disk"""
        check_output.return_value = b'200\n'
        storage_utils.zap_disk('/dev/foo')
        call.assert_any_call(['sgdisk', '--zap-all', '--', '/dev/foo'])
        call.assert_any_call(['sgdisk', '--clear', '--mbrtogpt',
                              '--', '/dev/foo'])
        check_output.assert_any_call(['blockdev', '--getsz', '/dev/foo'])
        check_call.assert_any_call(['dd', 'if=/dev/zero', 'of=/dev/foo',
                                    'bs=1M', 'count=1'])
        check_call.assert_any_call(['dd', 'if=/dev/zero', 'of=/dev/foo',
                                    'bs=512', 'count=100', 'seek=100'])

    @patch(STORAGE_LINUX_UTILS + '.S_ISBLK')
    @patch('os.path.exists')
    @patch('os.stat')
    def test_is_block_device(self, S_ISBLK, exists, stat):
        """It detects device node is block device"""
        class fake_stat:
            st_mode = True
        S_ISBLK.return_value = fake_stat()
        exists.return_value = True
        self.assertTrue(storage_utils.is_block_device('/dev/foo'))

    @patch(STORAGE_LINUX_UTILS + '.S_ISBLK')
    @patch('os.path.exists')
    @patch('os.stat')
    def test_is_block_device_does_not_exist(self, S_ISBLK, exists, stat):
        """It detects device node is block device"""
        class fake_stat:
            st_mode = True
        S_ISBLK.return_value = fake_stat()
        exists.return_value = False
        self.assertFalse(storage_utils.is_block_device('/dev/foo'))

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted(self, check_output):
        """It detects mounted devices as mounted."""
        check_output.return_value = (
            b'NAME="sda" MAJ:MIN="8:16" RM="0" SIZE="238.5G" RO="0" TYPE="disk" MOUNTPOINT="/tmp"\n')
        result = storage_utils.is_device_mounted('/dev/sda')
        self.assertTrue(result)

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted_partition(self, check_output):
        """It detects mounted partitions as mounted."""
        check_output.return_value = (
            b'NAME="sda1" MAJ:MIN="8:16" RM="0" SIZE="238.5G" RO="0" TYPE="disk" MOUNTPOINT="/tmp"\n')
        result = storage_utils.is_device_mounted('/dev/sda1')
        self.assertTrue(result)

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted_partition_with_device(self, check_output):
        """It detects mounted devices as mounted if "mount" shows only a
        partition as mounted."""
        check_output.return_value = (
            b'NAME="sda1" MAJ:MIN="8:16" RM="0" SIZE="238.5G" RO="0" TYPE="disk" MOUNTPOINT="/tmp"\n')
        result = storage_utils.is_device_mounted('/dev/sda')
        self.assertTrue(result)

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted_not_mounted(self, check_output):
        """It detects unmounted devices as not mounted."""
        check_output.return_value = (
            b'NAME="sda" MAJ:MIN="8:16" RM="0" SIZE="238.5G" RO="0" TYPE="disk" MOUNTPOINT=""\n')
        result = storage_utils.is_device_mounted('/dev/sda')
        self.assertFalse(result)

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted_not_mounted_partition(self, check_output):
        """It detects unmounted partitions as not mounted."""
        check_output.return_value = (
            b'NAME="sda" MAJ:MIN="8:16" RM="0" SIZE="238.5G" RO="0" TYPE="disk" MOUNTPOINT=""\n')
        result = storage_utils.is_device_mounted('/dev/sda1')
        self.assertFalse(result)

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted_full_disks(self, check_output):
        """It detects mounted full disks as mounted."""
        check_output.return_value = (
            b'NAME="sda" MAJ:MIN="8:16" RM="0" SIZE="238.5G" RO="0" TYPE="disk" MOUNTPOINT="/tmp"\n')
        result = storage_utils.is_device_mounted('/dev/sda')
        self.assertTrue(result)

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted_cciss(self, check_output):
        """It detects mounted cciss partitions as mounted."""
        check_output.return_value = (
            b'NAME="cciss!c0d0" MAJ:MIN="104:0" RM="0" SIZE="273.3G" RO="0" TYPE="disk" MOUNTPOINT="/root"\n')
        result = storage_utils.is_device_mounted('/dev/cciss/c0d0')
        self.assertTrue(result)

    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_is_device_mounted_cciss_not_mounted(self, check_output):
        """It detects unmounted cciss partitions as not mounted."""
        check_output.return_value = (
            b'NAME="cciss!c0d0" MAJ:MIN="104:0" RM="0" SIZE="273.3G" RO="0" TYPE="disk" MOUNTPOINT=""\n')
        result = storage_utils.is_device_mounted('/dev/cciss/c0d0')
        self.assertFalse(result)

    @patch(STORAGE_LINUX_UTILS + '.check_call')
    def test_mkfs_xfs(self, check_call):
        storage_utils.mkfs_xfs('/dev/sdb')
        check_call.assert_called_with(
            ['mkfs.xfs', '-i', 'size=1024', '/dev/sdb']
        )

    @patch(STORAGE_LINUX_UTILS + '.check_call')
    def test_mkfs_xfs_force(self, check_call):
        storage_utils.mkfs_xfs('/dev/sdb', force=True)
        check_call.assert_called_with(
            ['mkfs.xfs', '-f', '-i', 'size=1024', '/dev/sdb']
        )
