import unittest
import subprocess

from mock import patch

import charmhelpers.contrib.storage.linux.lvm as lvm

PVDISPLAY = b"""
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

EMPTY_VG_IN_PVDISPLAY = b"""
  --- Physical volume ---
  PV Name               /dev/loop0
  VG Name
  PV Size               10.00 MiB / not usable 2.00 MiB
  Allocatable           yes
  PE Size               4.00 MiB
  Total PE              2
  Free PE               2
  Allocated PE          0
  PV UUID               fyVqlr-pyrL-89On-f6MD-U91T-dEfc-SL0V2V

"""
LVS_DEFAULT = b"""
  cinder-volumes-pool
  testvol
  volume-48be6ba0-84c3-4b8d-9be5-e68e47fc7682
  volume-f8c1d2fd-1fa1-4d84-b4e0-431dba7d582e
"""
LVS_WITH_VG = b"""
  cinder-volumes cinder-volumes-pool
  cinder-volumes testvol
  cinder-volumes volume-48be6ba0-84c3-4b8d-9be5-e68e47fc7682
  cinder-volumes volume-f8c1d2fd-1fa1-4d84-b4e0-431dba7d582e
"""
LVS_THIN_POOLS = b"""
  cinder-volumes-pool
"""
LVS_THIN_POOLS_WITH_VG = b"""
  cinder-volumes cinder-volumes-pool
"""

# It's a mouthful.
STORAGE_LINUX_LVM = 'charmhelpers.contrib.storage.linux.lvm'


class LVMStorageUtilsTests(unittest.TestCase):
    def test_find_volume_group_on_pv(self):
        """It determines any volume group assigned to a LVM PV"""
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.return_value = PVDISPLAY
            vg = lvm.list_lvm_volume_group('/dev/loop0')
            self.assertEquals(vg, 'foo')

    def test_find_empty_volume_group_on_pv(self):
        """Return empty string when no volume group is assigned to the PV"""
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.return_value = EMPTY_VG_IN_PVDISPLAY
            vg = lvm.list_lvm_volume_group('/dev/loop0')
            self.assertEquals(vg, '')

    @patch(STORAGE_LINUX_LVM + '.list_lvm_volume_group')
    def test_deactivate_lvm_volume_groups(self, ls_vg):
        """It deactivates active volume groups on LVM PV"""
        ls_vg.return_value = 'foo-vg'
        with patch(STORAGE_LINUX_LVM + '.check_call') as check_call:
            lvm.deactivate_lvm_volume_group('/dev/loop0')
            check_call.assert_called_with(['vgchange', '-an', 'foo-vg'])

    def test_remove_lvm_physical_volume(self):
        """It removes LVM physical volume signatures from block device"""
        with patch(STORAGE_LINUX_LVM + '.Popen') as popen:
            lvm.remove_lvm_physical_volume('/dev/foo')
            popen.assert_called_with(['pvremove', '-ff', '/dev/foo'], stdin=-1)

    def test_is_physical_volume(self):
        """It properly reports block dev is an LVM PV"""
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.return_value = PVDISPLAY
            self.assertTrue(lvm.is_lvm_physical_volume('/dev/loop0'))

    def test_is_not_physical_volume(self):
        """It properly reports block dev is an LVM PV"""
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.side_effect = subprocess.CalledProcessError('cmd', 2)
            self.assertFalse(lvm.is_lvm_physical_volume('/dev/loop0'))

    def test_pvcreate(self):
        """It correctly calls pvcreate for a given block dev"""
        with patch(STORAGE_LINUX_LVM + '.check_call') as check_call:
            lvm.create_lvm_physical_volume('/dev/foo')
            check_call.assert_called_with(['pvcreate', '/dev/foo'])

    def test_vgcreate(self):
        """It correctly calls vgcreate for given block dev and vol group"""
        with patch(STORAGE_LINUX_LVM + '.check_call') as check_call:
            lvm.create_lvm_volume_group('foo-vg', '/dev/foo')
            check_call.assert_called_with(['vgcreate', 'foo-vg', '/dev/foo'])

    def test_list_logical_volumes(self):
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.return_value = LVS_DEFAULT
            self.assertEqual(lvm.list_logical_volumes(), [
                'cinder-volumes-pool',
                'testvol',
                'volume-48be6ba0-84c3-4b8d-9be5-e68e47fc7682',
                'volume-f8c1d2fd-1fa1-4d84-b4e0-431dba7d582e'])
            check_output.assert_called_with([
                'lvs',
                '--options',
                'lv_name',
                '--noheadings'])

    def test_list_logical_volumes_empty(self):
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.return_value = b''
            self.assertEqual(lvm.list_logical_volumes(), [])

    def test_list_logical_volumes_path_mode(self):
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.return_value = LVS_WITH_VG
            self.assertEqual(lvm.list_logical_volumes(path_mode=True), [
                'cinder-volumes/cinder-volumes-pool',
                'cinder-volumes/testvol',
                'cinder-volumes/volume-48be6ba0-84c3-4b8d-9be5-e68e47fc7682',
                'cinder-volumes/volume-f8c1d2fd-1fa1-4d84-b4e0-431dba7d582e'])
            check_output.assert_called_with([
                'lvs',
                '--options',
                'vg_name,lv_name',
                '--noheadings'])

    def test_list_logical_volumes_select_criteria(self):
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.return_value = LVS_THIN_POOLS
            self.assertEqual(
                lvm.list_logical_volumes(select_criteria='lv_attr =~ ^t'),
                ['cinder-volumes-pool'])
            check_output.assert_called_with([
                'lvs',
                '--options',
                'lv_name',
                '--noheadings',
                '--select',
                'lv_attr =~ ^t'])

    def test_list_thin_logical_volume_pools(self):
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.return_value = LVS_THIN_POOLS
            self.assertEqual(
                lvm.list_thin_logical_volume_pools(),
                ['cinder-volumes-pool'])
            check_output.assert_called_with([
                'lvs',
                '--options',
                'lv_name',
                '--noheadings',
                '--select',
                'lv_attr =~ ^t'])

    def test_list_thin_logical_volume_pools_path_mode(self):
        with patch(STORAGE_LINUX_LVM + '.check_output') as check_output:
            check_output.return_value = LVS_THIN_POOLS_WITH_VG
            self.assertEqual(
                lvm.list_thin_logical_volume_pools(path_mode=True),
                ['cinder-volumes/cinder-volumes-pool'])
            check_output.assert_called_with([
                'lvs',
                '--options',
                'vg_name,lv_name',
                '--noheadings',
                '--select',
                'lv_attr =~ ^t'])

    def test_extend_logical_volume_by_device(self):
        """It correctly calls pvcreate for a given block dev"""
        with patch(STORAGE_LINUX_LVM + '.check_call') as check_call:
            lvm.extend_logical_volume_by_device('mylv', '/dev/foo')
            check_call.assert_called_with(['lvextend', 'mylv', '/dev/foo'])

    def test_create_logical_volume_nosize(self):
        with patch(STORAGE_LINUX_LVM + '.check_call') as check_call:
            lvm.create_logical_volume('testlv', 'testvg')
            check_call.assert_called_with([
                'lvcreate',
                '--yes',
                '-l',
                '100%FREE',
                '-n', 'testlv', 'testvg'
            ])

    def test_create_logical_volume_size(self):
        with patch(STORAGE_LINUX_LVM + '.check_call') as check_call:
            lvm.create_logical_volume('testlv', 'testvg', '10G')
            check_call.assert_called_with([
                'lvcreate',
                '--yes',
                '-L',
                '10G',
                '-n', 'testlv', 'testvg'
            ])
