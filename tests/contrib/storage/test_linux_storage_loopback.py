import unittest

from mock import patch

import charmhelpers.contrib.storage.linux.loopback as loopback

LOOPBACK_DEVICES = b"""
/dev/loop0: [0805]:2244465 (/tmp/foo.img)
/dev/loop1: [0805]:2244466 (/tmp/bar.img)
/dev/loop2: [0805]:2244467 (/tmp/baz.img (deleted))
"""

# It's a mouthful.
STORAGE_LINUX_LOOPBACK = 'charmhelpers.contrib.storage.linux.loopback'


class LoopbackStorageUtilsTests(unittest.TestCase):
    @patch(STORAGE_LINUX_LOOPBACK + '.check_output')
    def test_loopback_devices(self, output):
        """It translates current loopback mapping to a dict"""
        output.return_value = LOOPBACK_DEVICES
        ex = {
            '/dev/loop1': '/tmp/bar.img',
            '/dev/loop0': '/tmp/foo.img',
            '/dev/loop2': '/tmp/baz.img (deleted)'
        }
        self.assertEquals(loopback.loopback_devices(), ex)

    @patch(STORAGE_LINUX_LOOPBACK + '.create_loopback')
    @patch('subprocess.check_call')
    @patch(STORAGE_LINUX_LOOPBACK + '.loopback_devices')
    def test_loopback_create_already_exists(self, loopbacks, check_call,
                                            create):
        """It finds existing loopback device for requested file"""
        loopbacks.return_value = {'/dev/loop1': '/tmp/bar.img'}
        res = loopback.ensure_loopback_device('/tmp/bar.img', '5G')
        self.assertEquals(res, '/dev/loop1')
        self.assertFalse(create.called)
        self.assertFalse(check_call.called)

    @patch(STORAGE_LINUX_LOOPBACK + '.loopback_devices')
    @patch(STORAGE_LINUX_LOOPBACK + '.create_loopback')
    @patch('os.path.exists')
    def test_loop_creation_no_truncate(self, path_exists, create_loopback,
                                       loopbacks):
        """It does not create a new sparse image for loopback if one exists"""
        loopbacks.return_value = {}
        path_exists.return_value = True
        with patch('subprocess.check_call') as check_call:
            loopback.ensure_loopback_device('/tmp/foo.img', '15G')
            self.assertFalse(check_call.called)

    @patch(STORAGE_LINUX_LOOPBACK + '.loopback_devices')
    @patch(STORAGE_LINUX_LOOPBACK + '.create_loopback')
    @patch('os.path.exists')
    def test_ensure_loopback_creation(self, path_exists, create_loopback,
                                      loopbacks):
        """It creates a new sparse image for loopback if one does not exists"""
        loopbacks.return_value = {}
        path_exists.return_value = False
        create_loopback.return_value = '/dev/loop0'
        with patch(STORAGE_LINUX_LOOPBACK + '.check_call') as check_call:
            loopback.ensure_loopback_device('/tmp/foo.img', '15G')
            check_call.assert_called_with(['truncate', '--size', '15G',
                                           '/tmp/foo.img'])

    @patch.object(loopback, 'loopback_devices')
    def test_create_loopback(self, _devs):
        """It correctly calls losetup to create a loopback device"""
        _devs.return_value = {'/dev/loop0': '/tmp/foo'}
        with patch(STORAGE_LINUX_LOOPBACK + '.check_call') as check_call:
            check_call.return_value = ''
            result = loopback.create_loopback('/tmp/foo')
            check_call.assert_called_with(['losetup', '--find', '/tmp/foo'])
            self.assertEquals(result, '/dev/loop0')

    @patch.object(loopback, 'loopback_devices')
    def test_create_is_mapped_loopback_device(self, devs):
        devs.return_value = {'/dev/loop0': "/tmp/manco"}
        self.assertEquals(loopback.is_mapped_loopback_device("/dev/loop0"),
                          "/tmp/manco")
        self.assertFalse(loopback.is_mapped_loopback_device("/dev/loop1"))
