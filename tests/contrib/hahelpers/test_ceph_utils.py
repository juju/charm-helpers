from mock import patch

from shutil import rmtree
from tempfile import mkdtemp
from threading import Timer
from testtools import TestCase

import charmhelpers.contrib.hahelpers.ceph as ceph_utils
import os
import time


LS_POOLS = """
images
volumes
rbd
"""


class CephUtilsTests(TestCase):
    def setUp(self):
        super(CephUtilsTests, self).setUp()
        [self._patch(m) for m in [
            'check_call',
            'log',
        ]]

    def _patch(self, method):
        _m = patch.object(ceph_utils, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    def test_create_keyring(self):
        '''It creates a new ceph keyring'''
        ceph_utils.create_keyring('cinder', 'cephkey')
        _cmd = ['ceph-authtool', '/etc/ceph/ceph.client.cinder.keyring',
                '--create-keyring', '--name=client.cinder',
                '--add-key=cephkey']
        self.check_call.assert_called_with(_cmd)

    def test_create_pool(self):
        '''It creates rados pool correctly'''
        ceph_utils.create_pool(service='cinder', name='foo')
        self.check_call.assert_called_with(
            ['rados', '--id', 'cinder', 'mkpool', 'foo']
        )

    def test_keyring_path(self):
        '''It correctly dervies keyring path from service name'''
        result = ceph_utils.keyring_path('cinder')
        self.assertEquals('/etc/ceph/ceph.client.cinder.keyring', result)

    @patch('commands.getstatusoutput')
    def test_pool_exists(self, get_output):
        '''It detects an rbd pool exists'''
        get_output.return_value = (0, LS_POOLS)
        self.assertTrue(ceph_utils.pool_exists('cinder', 'volumes'))

    @patch('commands.getstatusoutput')
    def test_pool_does_not_exist(self, get_output):
        '''It detects an rbd pool exists'''
        get_output.return_value = (0, LS_POOLS)
        self.assertFalse(ceph_utils.pool_exists('cinder', 'foo'))

    def test_make_filesystem_default_filesystem(self):
        '''make_filesystem() uses ext4 as the default filesystem.'''
        device = '/dev/zero'
        ceph_utils.make_filesystem(device)
        self.check_call.assert_called_with(['mkfs', '-t', 'ext4', device])

    def test_make_filesystem_no_device(self):
        '''make_filesystem() raises an IOError if the device does not exist.'''
        device = '/no/such/device'
        e = self.assertRaises(IOError, ceph_utils.make_filesystem, device,
                              timeout=0)
        self.assertEquals(device, e.filename)
        self.assertEquals(os.errno.ENOENT, e.errno)
        self.assertEquals(os.strerror(os.errno.ENOENT), e.strerror)
        self.log.assert_called_with('ceph: gave up waiting on block device %s' % device,
                                    level='ERROR')

    def test_make_filesystem_timeout(self):
        """
        make_filesystem() allows to specify how long it should wait for the
        device to appear before it fails.
        """
        device = '/no/such/device'
        timeout = 2
        before = time.time()
        self.assertRaises(IOError, ceph_utils.make_filesystem, device,
                          timeout=timeout)
        after = time.time()
        duration = after - before
        self.assertTrue(timeout - duration < 0.1)
        self.log.assert_called_with('ceph: gave up waiting on block device %s' % device,
                                    level='ERROR')

    def test_device_is_formatted_if_it_appears(self):
        """
        The specified device is formatted if it appears before the timeout
        is reached.
        """
        def create_my_device(filename):
            with open(filename, "w") as device:
                device.write("hello\n")
        temp_dir = mkdtemp()
        self.addCleanup(rmtree, temp_dir)
        device = "%s/mydevice" % temp_dir
        fstype = 'xfs'
        timeout = 4
        t = Timer(2, create_my_device, [device])
        t.start()
        ceph_utils.make_filesystem(device, fstype, timeout)
        self.check_call.assert_called_with(['mkfs', '-t', fstype, device])

    def test_existing_device_is_formatted(self):
        """
        make_filesystem() formats the given device if it exists with the
        specified filesystem.
        """
        device = '/dev/zero'
        fstype = 'xfs'
        ceph_utils.make_filesystem(device, fstype)
        self.check_call.assert_called_with(['mkfs', '-t', fstype, device])
        self.log.assert_called_with('ceph: Formatting block device %s as '
            'filesystem %s.' % (device, fstype), level='INFO')

