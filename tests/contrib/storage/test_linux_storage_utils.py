from mock import patch
import unittest

import charmhelpers.contrib.storage.linux.utils as storage_utils

# It's a mouthful.
STORAGE_LINUX_UTILS = 'charmhelpers.contrib.storage.linux.utils'


class MiscStorageUtilsTests(unittest.TestCase):
    def test_zap_disk(self):
        '''It calls sgdisk correctly to zap disk'''
        with patch(STORAGE_LINUX_UTILS + '.check_call') as check_call:
            storage_utils.zap_disk('/dev/foo')
            check_call.assert_called_with(['sgdisk', '--zap-all', '/dev/foo'])

    @patch(STORAGE_LINUX_UTILS + '.stat')
    @patch(STORAGE_LINUX_UTILS + '.S_ISBLK')
    def test_is_block_device(self, s_isblk, stat):
        '''It detects device node is block device'''
        with patch(STORAGE_LINUX_UTILS + '.S_ISBLK') as isblk:
            isblk.return_value = True
            self.assertTrue(storage_utils.is_block_device('/dev/foo'))
