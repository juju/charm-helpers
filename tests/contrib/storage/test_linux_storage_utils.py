from mock import patch
import unittest

import charmhelpers.contrib.storage.linux.utils as storage_utils

# It's a mouthful.
STORAGE_LINUX_UTILS = 'charmhelpers.contrib.storage.linux.utils'


class MiscStorageUtilsTests(unittest.TestCase):
    @patch(STORAGE_LINUX_UTILS + '.check_call')
    def test_zap_disk(self, check_call):
        '''It calls sgdisk correctly to zap disk'''
        with patch(STORAGE_LINUX_UTILS + '.check_output') as check_output:
            check_output.return_value = '200\n'
            storage_utils.zap_disk('/dev/foo')
            check_output.assert_any_call(['sgdisk', '--zap-all', '--mbrtogpt',
                                          '--clear', '/dev/foo'])
            check_output.assert_any_call(['blockdev', '--getsz', '/dev/foo'])
            check_call.assert_any_call(['dd', 'if=/dev/zero', 'of=/dev/foo',
                                        'bs=1M', 'count=1'])
            check_call.assert_any_call(['dd', 'if=/dev/zero', 'of=/dev/foo',
                                        'bs=512', 'count=100', 'seek=100'])

    @patch(STORAGE_LINUX_UTILS + '.stat')
    @patch(STORAGE_LINUX_UTILS + '.S_ISBLK')
    def test_is_block_device(self, s_isblk, stat):
        '''It detects device node is block device'''
        with patch(STORAGE_LINUX_UTILS + '.S_ISBLK') as isblk:
            isblk.return_value = True
            self.assertTrue(storage_utils.is_block_device('/dev/foo'))
