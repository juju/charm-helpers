from mock import patch
import unittest

import charmhelpers.contrib.storage.linux.utils as storage_utils

LOOPBACK_DEVICES = """
/dev/loop0: [0805]:2244465 (/tmp/foo.img)
/dev/loop1: [0805]:2244466 (/tmp/bar.img)
/dev/loop2: [0805]:2244467 (/tmp/baz.img)
"""


PVDISPLAY = """
  --- Physical volume ---
  PV Name               /dev/loop0
  VG Name               foo
  PV Size               10.00 MiB / not usable 2.00 MiB
  Allocatable           yes
  PE Size               4.00 MiB
  Total PE              2
  Free PE               2
  Allocated PE          0
  PV UUID               fyVqlr-pyrL-89On-f6MD-U91T-dEfc-SL0V2V

"""

# It's a mouthful.
STORAGE_LINUX_UTILS = 'charmhelpers.contrib.storage.linux.utils'

class MiscStorageUtilsTests(unittest.TestCase):
    def test_zap_disk(self):
        '''It calls sgdisk correctly to zap disk'''
        with patch(STORAGE_LINUX_UTILS + '.check_call') as check_call:
            storage_utils.zap_disk('/dev/foo')
            check_call.assert_called_with(['sgdisk', '--zap-all', '/dev/foo'])

class LVMStorageUtilsTests(unittest.TestCase):
    def test_find_volume_group_on_pv(self):
        '''It determines any volume group assigned to a LVM PV'''
        with patch(STORAGE_LINUX_UTILS + '.check_output') as check_output:
            check_output.return_value = PVDISPLAY
            vg = storage_utils.list_lvm_volume_group('/dev/loop0')
            self.assertEquals(vg, 'foo')

    @patch(STORAGE_LINUX_UTILS + '.list_lvm_volume_group')
    def test_deactivate_lvm_volume_groups(self, ls_vg):
        '''It deactivates active volume groups on LVM PV'''
        ls_vg.return_value = 'foo-vg'
        with patch(STORAGE_LINUX_UTILS + '.check_call') as check_call:
            storage_utils.deactivate_lvm_volume_group('/dev/loop0')
            check_call.assert_called_with(['vgchange', '-an', 'foo-vg'])

    def test_remove_lvm_physical_volume(self):
        '''It removes LVM physical volume signatures from block device'''
        with patch(STORAGE_LINUX_UTILS + '.Popen') as popen:
            storage_utils.remove_lvm_physical_volume('/dev/foo')
            popen.assert_called_with(['pvremove', '-ff', '/dev/foo'], stdin=-1)


class LoopbackStorageUtilsTests(unittest.TestCase):
    @patch(STORAGE_LINUX_UTILS + '.check_output')
    def test_loopback_devices(self, output):
        '''It translates current loopback mapping to a dict'''
        output.return_value = LOOPBACK_DEVICES
        ex = {
            '/dev/loop1': '/tmp/bar.img',
            '/dev/loop0': '/tmp/foo.img',
            '/dev/loop2': '/tmp/baz.img'
        }
        self.assertEquals(storage_utils.loopback_devices(), ex)

    @patch(STORAGE_LINUX_UTILS + '.create_loopback')
    @patch('subprocess.check_call')
    @patch(STORAGE_LINUX_UTILS + '.loopback_devices')
    def test_loopback_create_already_exists(self, loopbacks, check_call, create):
        '''It finds existing loopback device for requested file'''
        loopbacks.return_value = {'/dev/loop1': '/tmp/bar.img'}
        res = storage_utils.ensure_loopback_device('/tmp/bar.img', '5G')
        self.assertEquals(res, '/dev/loop1')
        self.assertFalse(create.called)
        self.assertFalse(check_call.called)

    @patch(STORAGE_LINUX_UTILS + '.loopback_devices')
    @patch(STORAGE_LINUX_UTILS + '.create_loopback')
    @patch('os.path.exists')
    def test_loop_creation_no_truncate(self, path_exists, create_loopback, loopbacks):
        '''It does not create a new sparse image for loopback if one exists'''
        loopbacks.return_value = {}
        path_exists.return_value = True
        with patch('subprocess.check_call') as check_call:
            storage_utils.ensure_loopback_device('/tmp/foo.img', '15G')
            self.assertFalse(check_call.called)

    @patch(STORAGE_LINUX_UTILS + '.loopback_devices')
    @patch(STORAGE_LINUX_UTILS + '.create_loopback')
    @patch('os.path.exists')
    def test_loopback_creation(self, path_exists, create_loopback, loopbacks):
        '''It creates a new sparse image for loopback if one does not exists'''
        loopbacks.return_value = {}
        path_exists.return_value = False
        create_loopback.return_value = '/dev/loop0'
        with patch(STORAGE_LINUX_UTILS + '.check_call') as check_call:
            storage_utils.ensure_loopback_device('/tmp/foo.img', '15G')
            check_call.assert_called_with(['truncate', '--size', '15G',
                                           '/tmp/foo.img'])
