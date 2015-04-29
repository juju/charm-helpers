from mock import patch, call

from shutil import rmtree
from tempfile import mkdtemp
from threading import Timer
from testtools import TestCase
import json

import charmhelpers.contrib.storage.linux.ceph as ceph_utils
from subprocess import CalledProcessError
from tests.helpers import patch_open
import nose.plugins.attrib
import os
import time


LS_POOLS = b"""
images
volumes
rbd
"""

LS_RBDS = b"""
rbd1
rbd2
rbd3
"""

IMG_MAP = b"""
bar
baz
"""


class CephUtilsTests(TestCase):
    def setUp(self):
        super(CephUtilsTests, self).setUp()
        [self._patch(m) for m in [
            'check_call',
            'check_output',
            'log',
        ]]

    def _patch(self, method):
        _m = patch.object(ceph_utils, method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        setattr(self, method, mock)

    @patch('os.path.exists')
    def test_create_keyring(self, _exists):
        '''It creates a new ceph keyring'''
        _exists.return_value = False
        ceph_utils.create_keyring('cinder', 'cephkey')
        _cmd = ['ceph-authtool', '/etc/ceph/ceph.client.cinder.keyring',
                '--create-keyring', '--name=client.cinder',
                '--add-key=cephkey']
        self.check_call.assert_called_with(_cmd)

    @patch('os.path.exists')
    def test_create_keyring_already_exists(self, _exists):
        '''It creates a new ceph keyring'''
        _exists.return_value = True
        ceph_utils.create_keyring('cinder', 'cephkey')
        self.log.assert_called()
        self.check_call.assert_not_called()

    @patch('os.remove')
    @patch('os.path.exists')
    def test_delete_keyring(self, _exists, _remove):
        '''It deletes a ceph keyring.'''
        _exists.return_value = True
        ceph_utils.delete_keyring('cinder')
        _remove.assert_called_with('/etc/ceph/ceph.client.cinder.keyring')
        self.log.assert_called()

    @patch('os.remove')
    @patch('os.path.exists')
    def test_delete_keyring_not_exists(self, _exists, _remove):
        '''It creates a new ceph keyring.'''
        _exists.return_value = False
        ceph_utils.delete_keyring('cinder')
        self.log.assert_called()
        _remove.assert_not_called()

    @patch('os.path.exists')
    def test_create_keyfile(self, _exists):
        '''It creates a new ceph keyfile'''
        _exists.return_value = False
        with patch_open() as (_open, _file):
            ceph_utils.create_key_file('cinder', 'cephkey')
            _file.write.assert_called_with('cephkey')
        self.log.assert_called()

    @patch('os.path.exists')
    def test_create_key_file_already_exists(self, _exists):
        '''It creates a new ceph keyring'''
        _exists.return_value = True
        ceph_utils.create_key_file('cinder', 'cephkey')
        self.log.assert_called()

    @patch('os.mkdir')
    @patch.object(ceph_utils, 'apt_install')
    @patch('os.path.exists')
    def test_install(self, _exists, _install, _mkdir):
        _exists.return_value = False
        ceph_utils.install()
        _mkdir.assert_called_with('/etc/ceph')
        _install.assert_called_with('ceph-common', fatal=True)

    @patch.object(ceph_utils, 'ceph_version')
    def test_get_osds(self, version):
        version.return_value = '0.56.2'
        self.check_output.return_value = json.dumps([1, 2, 3]).encode('UTF-8')
        self.assertEquals(ceph_utils.get_osds('test'), [1, 2, 3])

    @patch.object(ceph_utils, 'ceph_version')
    def test_get_osds_argonaut(self, version):
        version.return_value = '0.48.3'
        self.assertEquals(ceph_utils.get_osds('test'), None)

    @patch.object(ceph_utils, 'ceph_version')
    def test_get_osds_none(self, version):
        version.return_value = '0.56.2'
        self.check_output.return_value = json.dumps(None).encode('UTF-8')
        self.assertEquals(ceph_utils.get_osds('test'), None)

    @patch.object(ceph_utils, 'get_osds')
    @patch.object(ceph_utils, 'pool_exists')
    def test_create_pool(self, _exists, _get_osds):
        '''It creates rados pool correctly with default replicas '''
        _exists.return_value = False
        _get_osds.return_value = [1, 2, 3]
        ceph_utils.create_pool(service='cinder', name='foo')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'cinder', 'osd', 'pool',
                  'create', 'foo', '100']),
            call(['ceph', '--id', 'cinder', 'osd', 'pool', 'set',
                  'foo', 'size', '3'])
        ])

    @patch.object(ceph_utils, 'get_osds')
    @patch.object(ceph_utils, 'pool_exists')
    def test_create_pool_2_replicas(self, _exists, _get_osds):
        '''It creates rados pool correctly with 3 replicas'''
        _exists.return_value = False
        _get_osds.return_value = [1, 2, 3]
        ceph_utils.create_pool(service='cinder', name='foo', replicas=2)
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'cinder', 'osd', 'pool',
                  'create', 'foo', '150']),
            call(['ceph', '--id', 'cinder', 'osd', 'pool', 'set',
                  'foo', 'size', '2'])
        ])

    @patch.object(ceph_utils, 'get_osds')
    @patch.object(ceph_utils, 'pool_exists')
    def test_create_pool_argonaut(self, _exists, _get_osds):
        '''It creates rados pool correctly with 3 replicas'''
        _exists.return_value = False
        _get_osds.return_value = None
        ceph_utils.create_pool(service='cinder', name='foo')
        self.check_call.assert_has_calls([
            call(['ceph', '--id', 'cinder', 'osd', 'pool',
                  'create', 'foo', '200']),
            call(['ceph', '--id', 'cinder', 'osd', 'pool', 'set',
                  'foo', 'size', '3'])
        ])

    def test_create_pool_already_exists(self):
        self._patch('pool_exists')
        self.pool_exists.return_value = True
        ceph_utils.create_pool(service='cinder', name='foo')
        self.log.assert_called()
        self.check_call.assert_not_called()

    def test_keyring_path(self):
        '''It correctly dervies keyring path from service name'''
        result = ceph_utils._keyring_path('cinder')
        self.assertEquals('/etc/ceph/ceph.client.cinder.keyring', result)

    def test_keyfile_path(self):
        '''It correctly dervies keyring path from service name'''
        result = ceph_utils._keyfile_path('cinder')
        self.assertEquals('/etc/ceph/ceph.client.cinder.key', result)

    def test_pool_exists(self):
        '''It detects an rbd pool exists'''
        self.check_output.return_value = LS_POOLS
        self.assertTrue(ceph_utils.pool_exists('cinder', 'volumes'))

    def test_pool_does_not_exist(self):
        '''It detects an rbd pool exists'''
        self.check_output.return_value = LS_POOLS
        self.assertFalse(ceph_utils.pool_exists('cinder', 'foo'))

    def test_pool_exists_error(self):
        ''' Ensure subprocess errors and sandboxed with False '''
        self.check_output.side_effect = CalledProcessError(1, 'rados')
        self.assertFalse(ceph_utils.pool_exists('cinder', 'foo'))

    def test_rbd_exists(self):
        self.check_output.return_value = LS_RBDS
        self.assertTrue(ceph_utils.rbd_exists('service', 'pool', 'rbd1'))
        self.check_output.assert_call_with(
            ['rbd', 'list', '--id', 'service', '--pool', 'pool']
        )

    def test_rbd_does_not_exist(self):
        self.check_output.return_value = LS_RBDS
        self.assertFalse(ceph_utils.rbd_exists('service', 'pool', 'rbd4'))
        self.check_output.assert_call_with(
            ['rbd', 'list', '--id', 'service', '--pool', 'pool']
        )

    def test_rbd_exists_error(self):
        ''' Ensure subprocess errors and sandboxed with False '''
        self.check_output.side_effect = CalledProcessError(1, 'rbd')
        self.assertFalse(ceph_utils.rbd_exists('cinder', 'foo', 'rbd'))

    def test_create_rbd_image(self):
        ceph_utils.create_rbd_image('service', 'pool', 'image', 128)
        _cmd = ['rbd', 'create', 'image',
                '--size', '128',
                '--id', 'service',
                '--pool', 'pool']
        self.check_call.assert_called_with(_cmd)

    def test_delete_pool(self):
        ceph_utils.delete_pool('cinder', 'pool')
        _cmd = [
            'ceph', '--id', 'cinder',
            'osd', 'pool', 'delete',
            'pool', '--yes-i-really-really-mean-it'
        ]
        self.check_call.assert_called_with(_cmd)

    def test_get_ceph_nodes(self):
        self._patch('relation_ids')
        self._patch('related_units')
        self._patch('relation_get')
        units = ['ceph/1', 'ceph2', 'ceph/3']
        self.relation_ids.return_value = ['ceph:0']
        self.related_units.return_value = units
        self.relation_get.return_value = '192.168.1.1'
        self.assertEquals(len(ceph_utils.get_ceph_nodes()), 3)

    def test_get_ceph_nodes_not_related(self):
        self._patch('relation_ids')
        self.relation_ids.return_value = []
        self.assertEquals(ceph_utils.get_ceph_nodes(), [])

    def test_configure(self):
        self._patch('create_keyring')
        self._patch('create_key_file')
        self._patch('get_ceph_nodes')
        self._patch('modprobe')
        _hosts = ['192.168.1.1', '192.168.1.2']
        self.get_ceph_nodes.return_value = _hosts
        _conf = ceph_utils.CEPH_CONF.format(
            auth='cephx',
            keyring=ceph_utils._keyring_path('cinder'),
            mon_hosts=",".join(map(str, _hosts)),
            use_syslog='true'
        )
        with patch_open() as (_open, _file):
            ceph_utils.configure('cinder', 'key', 'cephx', 'true')
            _file.write.assert_called_with(_conf)
            _open.assert_called_with('/etc/ceph/ceph.conf', 'w')
        self.modprobe.assert_called_with('rbd')
        self.create_keyring.assert_called_with('cinder', 'key')
        self.create_key_file.assert_called_with('cinder', 'key')

    def test_image_mapped(self):
        self.check_output.return_value = IMG_MAP
        self.assertTrue(ceph_utils.image_mapped('bar'))

    def test_image_not_mapped(self):
        self.check_output.return_value = IMG_MAP
        self.assertFalse(ceph_utils.image_mapped('foo'))

    def test_image_not_mapped_error(self):
        self.check_output.side_effect = CalledProcessError(1, 'rbd')
        self.assertFalse(ceph_utils.image_mapped('bar'))

    def test_map_block_storage(self):
        _service = 'cinder'
        _pool = 'bar'
        _img = 'foo'
        _cmd = [
            'rbd',
            'map',
            '{}/{}'.format(_pool, _img),
            '--user',
            _service,
            '--secret',
            ceph_utils._keyfile_path(_service),
        ]
        ceph_utils.map_block_storage(_service, _pool, _img)
        self.check_call.assert_called_with(_cmd)

    def test_modprobe(self):
        with patch_open() as (_open, _file):
            _file.read.return_value = 'anothermod\n'
            ceph_utils.modprobe('mymod')
            _open.assert_called_with('/etc/modules', 'r+')
            _file.read.assert_called()
            _file.write.assert_called_with('mymod')
        self.check_call.assert_called_with(['modprobe', 'mymod'])

    def test_filesystem_mounted(self):
        self._patch('mounts')
        self.mounts.return_value = [['/afs', '/dev/sdb'], ['/bfs', '/dev/sdd']]
        self.assertTrue(ceph_utils.filesystem_mounted('/afs'))
        self.assertFalse(ceph_utils.filesystem_mounted('/zfs'))

    @patch('os.path.exists')
    def test_make_filesystem(self, _exists):
        _exists.return_value = True
        ceph_utils.make_filesystem('/dev/sdd')
        self.log.assert_called()
        self.check_call.assert_called_with(['mkfs', '-t', 'ext4', '/dev/sdd'])

    @patch('os.path.exists')
    def test_make_filesystem_xfs(self, _exists):
        _exists.return_value = True
        ceph_utils.make_filesystem('/dev/sdd', 'xfs')
        self.log.assert_called()
        self.check_call.assert_called_with(['mkfs', '-t', 'xfs', '/dev/sdd'])

    @patch('os.chown')
    @patch('os.stat')
    def test_place_data_on_block_device(self, _stat, _chown):
        self._patch('mount')
        self._patch('copy_files')
        self._patch('umount')
        _stat.return_value.st_uid = 100
        _stat.return_value.st_gid = 100
        ceph_utils.place_data_on_block_device('/dev/sdd', '/var/lib/mysql')
        self.mount.assert_has_calls([
            call('/dev/sdd', '/mnt'),
            call('/dev/sdd', '/var/lib/mysql', persist=True)
        ])
        self.copy_files.assert_called_with('/var/lib/mysql', '/mnt')
        self.umount.assert_called_with('/mnt')
        _chown.assert_called_with('/var/lib/mysql', 100, 100)

    @patch('shutil.copytree')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_is_dir(self, _isdir, _listdir, _copytree):
        _isdir.return_value = True
        subdirs = ['a', 'b', 'c']
        _listdir.return_value = subdirs
        ceph_utils.copy_files('/source', '/dest')
        for d in subdirs:
            _copytree.assert_has_calls([
                call('/source/{}'.format(d), '/dest/{}'.format(d),
                     False, None)
            ])

    @patch('shutil.copytree')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_include_symlinks(self, _isdir, _listdir, _copytree):
        _isdir.return_value = True
        subdirs = ['a', 'b', 'c']
        _listdir.return_value = subdirs
        ceph_utils.copy_files('/source', '/dest', True)
        for d in subdirs:
            _copytree.assert_has_calls([
                call('/source/{}'.format(d), '/dest/{}'.format(d),
                     True, None)
            ])

    @patch('shutil.copytree')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_ignore(self, _isdir, _listdir, _copytree):
        _isdir.return_value = True
        subdirs = ['a', 'b', 'c']
        _listdir.return_value = subdirs
        ceph_utils.copy_files('/source', '/dest', True, False)
        for d in subdirs:
            _copytree.assert_has_calls([
                call('/source/{}'.format(d), '/dest/{}'.format(d),
                     True, False)
            ])

    @patch('shutil.copy2')
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_copy_files_files(self, _isdir, _listdir, _copy2):
        _isdir.return_value = False
        files = ['a', 'b', 'c']
        _listdir.return_value = files
        ceph_utils.copy_files('/source', '/dest')
        for f in files:
            _copy2.assert_has_calls([
                call('/source/{}'.format(f), '/dest/{}'.format(f))
            ])

    def test_ensure_ceph_storage(self):
        self._patch('pool_exists')
        self.pool_exists.return_value = False
        self._patch('create_pool')
        self._patch('rbd_exists')
        self.rbd_exists.return_value = False
        self._patch('create_rbd_image')
        self._patch('image_mapped')
        self.image_mapped.return_value = False
        self._patch('map_block_storage')
        self._patch('filesystem_mounted')
        self.filesystem_mounted.return_value = False
        self._patch('make_filesystem')
        self._patch('service_stop')
        self._patch('service_start')
        self._patch('service_running')
        self.service_running.return_value = True
        self._patch('place_data_on_block_device')
        _service = 'mysql'
        _pool = 'bar'
        _rbd_img = 'foo'
        _mount = '/var/lib/mysql'
        _services = ['mysql']
        _blk_dev = '/dev/rbd1'
        ceph_utils.ensure_ceph_storage(_service, _pool,
                                       _rbd_img, 1024, _mount,
                                       _blk_dev, 'ext4', _services, 3)
        self.create_pool.assert_called_with(_service, _pool, replicas=3)
        self.create_rbd_image.assert_called_with(_service, _pool,
                                                 _rbd_img, 1024)
        self.map_block_storage.assert_called_with(_service, _pool, _rbd_img)
        self.make_filesystem.assert_called_with(_blk_dev, 'ext4')
        self.service_stop.assert_called_with(_services[0])
        self.place_data_on_block_device.assert_called_with(_blk_dev, _mount)
        self.service_start.assert_called_with(_services[0])

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
        self.log.assert_called_with(
            'Gave up waiting on block device %s' % device, level='ERROR')

    @nose.plugins.attrib.attr('slow')
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
        self.log.assert_called_with(
            'Gave up waiting on block device %s' % device, level='ERROR')

    @nose.plugins.attrib.attr('slow')
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
        self.log.assert_called_with(
            'Formatting block device %s as '
            'filesystem %s.' % (device, fstype), level='INFO'
        )

    @patch.object(ceph_utils, 'relation_ids')
    @patch.object(ceph_utils, 'related_units')
    @patch.object(ceph_utils, 'relation_get')
    def test_ensure_ceph_keyring_no_relation_no_data(self, rget, runits, rids):
        rids.return_value = []
        self.assertEquals(False, ceph_utils.ensure_ceph_keyring(service='foo'))
        rids.return_value = ['ceph:0']
        runits.return_value = ['ceph/0']
        rget.return_value = ''
        self.assertEquals(False, ceph_utils.ensure_ceph_keyring(service='foo'))

    @patch.object(ceph_utils, '_keyring_path')
    @patch.object(ceph_utils, 'create_keyring')
    @patch.object(ceph_utils, 'relation_ids')
    @patch.object(ceph_utils, 'related_units')
    @patch.object(ceph_utils, 'relation_get')
    def test_ensure_ceph_keyring_with_data(self, rget, runits,
                                           rids, create, _path):
        rids.return_value = ['ceph:0']
        runits.return_value = ['ceph/0']
        rget.return_value = 'fookey'
        self.assertEquals(True,
                          ceph_utils.ensure_ceph_keyring(service='foo'))
        create.assert_called_with(service='foo', key='fookey')
        _path.assert_called_with('foo')
        self.assertFalse(self.check_call.called)

        _path.return_value = '/etc/ceph/client.foo.keyring'
        self.assertEquals(
            True,
            ceph_utils.ensure_ceph_keyring(
                service='foo', user='adam', group='users'))
        create.assert_called_with(service='foo', key='fookey')
        _path.assert_called_with('foo')
        self.check_call.assert_called_with([
            'chown',
            'adam.users',
            '/etc/ceph/client.foo.keyring'
        ])

    @patch('os.path.exists')
    def test_ceph_version_not_installed(self, path):
        path.return_value = False
        self.assertEquals(ceph_utils.ceph_version(), None)

    @patch.object(ceph_utils, 'check_output')
    @patch('os.path.exists')
    def test_ceph_version_error(self, path, output):
        path.return_value = True
        output.return_value = b''
        self.assertEquals(ceph_utils.ceph_version(), None)

    @patch.object(ceph_utils, 'check_output')
    @patch('os.path.exists')
    def test_ceph_version_ok(self, path, output):
        path.return_value = True
        output.return_value = \
            b'ceph version 0.67.4 (ad85b8bfafea6232d64cb7ba76a8b6e8252fa0c7)'
        self.assertEquals(ceph_utils.ceph_version(), '0.67.4')

    def test_ceph_broker_rq_class(self):
        rq = ceph_utils.CephBrokerRq()
        rq.add_op_create_pool('pool1', replica_count=1)
        rq.add_op_create_pool('pool2')
        expected = json.dumps({'api-version': 1,
                               'ops': [{'op': 'create-pool', 'name': 'pool1',
                                        'replicas': 1},
                                       {'op': 'create-pool', 'name': 'pool2',
                                        'replicas': 3}]})
        self.assertEqual(rq.request, expected)

    def test_ceph_broker_rsp_class(self):
        rsp = ceph_utils.CephBrokerRsp(json.dumps({'exit-code': 0,
                                                   'stderr': "Success"}))
        self.assertEqual(rsp.exit_code, 0)
        self.assertEqual(rsp.exit_msg, "Success")
