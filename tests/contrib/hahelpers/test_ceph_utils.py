from mock import patch

from testtools import TestCase

import charmhelpers.contrib.hahelpers.ceph as ceph_utils


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
