
from mock import call, patch, MagicMock, sentinel
from testtools import TestCase

from tests.helpers import patch_open, FakeRelation
from charmhelpers.contrib import unison


FAKE_RELATION_ENV = {
    'cluster:0': ['cluster/0', 'cluster/1']
}


TO_PATCH = [
    'log', 'check_call', 'check_output', 'relation_ids',
    'related_units', 'relation_get', 'relation_set',
    'hook_name', 'unit_private_ip',
]

FAKE_LOCAL_UNIT = 'test_host'
FAKE_RELATION = {
    'cluster:0': {
        'cluster/0': {
            'private-address': 'cluster0.local',
            'ssh_authorized_hosts': 'someotherhost:test_host'
        },
        'clsuter/1': {
            'private-address': 'cluster1.local',
            'ssh_authorized_hosts': 'someotherhost'
        },
        'clsuter/3': {
            'private-address': 'cluster2.local',
            'ssh_authorized_hosts': 'someotherthirdhost'
        },

    },

}


class UnisonHelperTests(TestCase):
    def setUp(self):
        super(UnisonHelperTests, self).setUp()
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))
        self.fake_relation = FakeRelation(FAKE_RELATION)
        self.unit_private_ip.return_value = FAKE_LOCAL_UNIT
        self.relation_get.side_effect = self.fake_relation.get
        self.relation_ids.side_effect = self.fake_relation.relation_ids
        self.related_units.side_effect = self.fake_relation.related_units

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.unison.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    @patch('pwd.getpwnam')
    def test_get_homedir(self, pwnam):
        fake_user = MagicMock()
        fake_user.pw_dir = '/home/foo'
        pwnam.return_value = fake_user
        self.assertEquals(unison.get_homedir('foo'),
                          '/home/foo')

    @patch('pwd.getpwnam')
    def test_get_homedir_no_user(self, pwnam):
        e = KeyError
        pwnam.side_effect = e
        self.assertRaises(Exception, unison.get_homedir, user='foo')

    def _ensure_calls_in(self, calls):
        for _call in calls:
            self.assertIn(call(_call), self.check_call.call_args_list)

    @patch('os.chmod')
    @patch('os.chown')
    @patch('os.path.isfile')
    @patch('pwd.getpwnam')
    def test_create_private_key_rsa(self, pwnam, isfile, chown, chmod):
        fake_user = MagicMock()
        fake_user.pw_uid = 3133
        pwnam.return_value = fake_user
        create_cmd = [
            'ssh-keygen', '-q', '-N', '', '-t', 'rsa', '-b', '2048',
            '-f', '/home/foo/.ssh/id_rsa']

        def _ensure_perms():
            chown.assert_called_with('/home/foo/.ssh/id_rsa', 3133, -1)
            chmod.assert_called_with('/home/foo/.ssh/id_rsa', 0o600)

        isfile.return_value = False
        unison.create_private_key(
            user='foo', priv_key_path='/home/foo/.ssh/id_rsa')
        self.assertIn(call(create_cmd), self.check_call.call_args_list)
        _ensure_perms()
        self.check_call.call_args_list = []

        chown.reset_mock()
        chmod.reset_mock()
        isfile.return_value = True
        unison.create_private_key(
            user='foo', priv_key_path='/home/foo/.ssh/id_rsa')
        self.assertNotIn(call(create_cmd), self.check_call.call_args_list)
        _ensure_perms()

    @patch('os.chmod')
    @patch('os.chown')
    @patch('os.path.isfile')
    @patch('pwd.getpwnam')
    def test_create_private_key_ecdsa(self, pwnam, isfile, chown, chmod):
        fake_user = MagicMock()
        fake_user.pw_uid = 3133
        pwnam.return_value = fake_user
        create_cmd = [
            'ssh-keygen', '-q', '-N', '', '-t', 'ecdsa', '-b', '521',
            '-f', '/home/foo/.ssh/id_ecdsa']

        def _ensure_perms():
            chown.assert_called_with('/home/foo/.ssh/id_ecdsa', 3133, -1)
            chmod.assert_called_with('/home/foo/.ssh/id_ecdsa', 0o600)

        isfile.return_value = False
        unison.create_private_key(
            user='foo',
            priv_key_path='/home/foo/.ssh/id_ecdsa',
            key_type='ecdsa')
        self.assertIn(call(create_cmd), self.check_call.call_args_list)
        _ensure_perms()
        self.check_call.call_args_list = []

        chown.reset_mock()
        chmod.reset_mock()
        isfile.return_value = True
        unison.create_private_key(
            user='foo',
            priv_key_path='/home/foo/.ssh/id_ecdsa',
            key_type='ecdsa')
        self.assertNotIn(call(create_cmd), self.check_call.call_args_list)
        _ensure_perms()

    @patch('os.chown')
    @patch('os.path.isfile')
    @patch('pwd.getpwnam')
    def test_create_public_key(self, pwnam, isfile, chown):
        fake_user = MagicMock()
        fake_user.pw_uid = 3133
        pwnam.return_value = fake_user
        create_cmd = ['ssh-keygen', '-y', '-f', '/home/foo/.ssh/id_rsa']

        def _ensure_perms():
            chown.assert_called_with('/home/foo/.ssh/id_rsa.pub', 3133, -1)

        isfile.return_value = True
        unison.create_public_key(
            user='foo', priv_key_path='/home/foo/.ssh/id_rsa',
            pub_key_path='/home/foo/.ssh/id_rsa.pub')
        self.assertNotIn(call(create_cmd), self.check_output.call_args_list)
        _ensure_perms()

        isfile.return_value = False
        with patch_open() as (_open, _file):
            self.check_output.return_value = b'fookey'
            unison.create_public_key(
                user='foo', priv_key_path='/home/foo/.ssh/id_rsa',
                pub_key_path='/home/foo/.ssh/id_rsa.pub')
            self.assertIn(call(create_cmd), self.check_output.call_args_list)
            _ensure_perms()
            _open.assert_called_with('/home/foo/.ssh/id_rsa.pub', 'wb')
            _file.write.assert_called_with(b'fookey')

    @patch('os.mkdir')
    @patch('os.path.isdir')
    @patch.object(unison, 'get_homedir')
    @patch.multiple(unison, create_private_key=MagicMock(),
                    create_public_key=MagicMock())
    def test_get_keypair(self, get_homedir, isdir, mkdir):
        get_homedir.return_value = '/home/foo'
        isdir.return_value = False
        with patch_open() as (_open, _file):
            _file.read.side_effect = [
                'foopriv', 'foopub'
            ]
            priv, pub = unison.get_keypair('adam')
            for f in ['/home/foo/.ssh/id_rsa',
                      '/home/foo/.ssh/id_rsa.pub']:
                self.assertIn(call(f, 'r'), _open.call_args_list)
        self.assertEquals(priv, 'foopriv')
        self.assertEquals(pub, 'foopub')

    @patch.object(unison, 'get_homedir')
    @patch('os.chown')
    @patch('pwd.getpwnam')
    def test_write_auth_keys(self, pwnam, chown, get_homedir):
        fake_user = MagicMock()
        fake_user.pw_uid = 3133
        pwnam.return_value = fake_user
        get_homedir.return_value = '/home/foo'
        keys = [
            'ssh-rsa AAAB3Nz adam',
            'ssh-rsa ALKJFz adam@whereschuck.org',
        ]

        def _ensure_perms():
            chown.assert_called_with('/home/foo/.ssh/authorized_keys', 3133, -1)

        with patch_open() as (_open, _file):
            unison.write_authorized_keys('foo', keys)
            _open.assert_called_with('/home/foo/.ssh/authorized_keys', 'w')
            for k in keys:
                self.assertIn(call('%s\n' % k), _file.write.call_args_list)
            _ensure_perms()

    @patch.object(unison, 'get_homedir')
    @patch('os.chown')
    @patch('pwd.getpwnam')
    def test_write_known_hosts(self, pwnam, chown, get_homedir):
        fake_user = MagicMock()
        fake_user.pw_uid = 3133
        pwnam.return_value = fake_user
        get_homedir.return_value = '/home/foo'
        keys = [
            '10.0.0.1 ssh-rsa KJDSJF=',
            '10.0.0.2 ssh-rsa KJDSJF=',
        ]
        self.check_output.side_effect = keys

        def _ensure_perms():
            chown.assert_called_with('/home/foo/.ssh/known_hosts', 3133, -1)

        with patch_open() as (_open, _file):
            unison.write_known_hosts('foo', ['10.0.0.1', '10.0.0.2'])
            _open.assert_called_with('/home/foo/.ssh/known_hosts', 'w')
            for k in keys:
                self.assertIn(call('%s\n' % k), _file.write.call_args_list)
            _ensure_perms()

    @patch.object(unison, 'remove_password_expiry')
    @patch.object(unison, 'pwgen')
    @patch.object(unison, 'add_user_to_group')
    @patch.object(unison, 'adduser')
    def test_ensure_user(self, adduser, to_group, pwgen,
                         remove_password_expiry):
        pwgen.return_value = sentinel.password
        unison.ensure_user('foo', group='foobar')
        adduser.assert_called_with('foo', sentinel.password)
        to_group.assert_called_with('foo', 'foobar')
        remove_password_expiry.assert_called_with('foo')

    @patch.object(unison, '_run_as_user')
    def test_run_as_user(self, _run):
        with patch.object(unison, '_run_as_user') as _run:
            fake_preexec = MagicMock()
            _run.return_value = fake_preexec
            unison.run_as_user('foo', ['echo', 'foo'])
            self.check_output.assert_called_with(
                ['echo', 'foo'], preexec_fn=fake_preexec, cwd='/')

    @patch('pwd.getpwnam')
    def test_run_user_not_found(self, getpwnam):
        e = KeyError
        getpwnam.side_effect = e
        self.assertRaises(Exception, unison._run_as_user, 'nouser')

    @patch('os.setuid')
    @patch('os.setgid')
    @patch('os.environ', spec=dict)
    @patch('pwd.getpwnam')
    def test_run_as_user_preexec(self, pwnam, environ, setgid, setuid):
        fake_env = {'HOME': '/root'}
        environ.__getitem__ = MagicMock()
        environ.__setitem__ = MagicMock()
        environ.__setitem__.side_effect = fake_env.__setitem__
        environ.__getitem__.side_effect = fake_env.__getitem__

        fake_user = MagicMock()
        fake_user.pw_uid = 1010
        fake_user.pw_gid = 1011
        fake_user.pw_dir = '/home/foo'
        pwnam.return_value = fake_user
        inner = unison._run_as_user('foo')
        self.assertEquals(fake_env['HOME'], '/home/foo')
        inner()
        setgid.assert_called_with(1011)
        setuid.assert_called_with(1010)

    @patch('os.setuid')
    @patch('os.setgid')
    @patch('os.environ', spec=dict)
    @patch('pwd.getpwnam')
    def test_run_as_user_preexec_with_group(self, pwnam, environ, setgid, setuid):
        fake_env = {'HOME': '/root'}
        environ.__getitem__ = MagicMock()
        environ.__setitem__ = MagicMock()
        environ.__setitem__.side_effect = fake_env.__setitem__
        environ.__getitem__.side_effect = fake_env.__getitem__

        fake_user = MagicMock()
        fake_user.pw_uid = 1010
        fake_user.pw_gid = 1011
        fake_user.pw_dir = '/home/foo'
        fake_group_id = 2000
        pwnam.return_value = fake_user
        inner = unison._run_as_user('foo', gid=fake_group_id)
        self.assertEquals(fake_env['HOME'], '/home/foo')
        inner()
        setgid.assert_called_with(2000)
        setuid.assert_called_with(1010)

    @patch.object(unison, 'get_keypair')
    @patch.object(unison, 'ensure_user')
    def test_ssh_auth_peer_joined(self, ensure_user, get_keypair):
        get_keypair.return_value = ('privkey', 'pubkey')
        self.hook_name.return_value = 'cluster-relation-joined'
        unison.ssh_authorized_peers(peer_interface='cluster',
                                    user='foo', group='foo',
                                    ensure_local_user=True)
        self.relation_set.assert_called_with(ssh_pub_key='pubkey')
        self.assertFalse(self.relation_get.called)
        ensure_user.assert_called_with('foo', 'foo')
        get_keypair.assert_called_with('foo')

    @patch.object(unison, 'write_known_hosts')
    @patch.object(unison, 'write_authorized_keys')
    @patch.object(unison, 'get_keypair')
    @patch.object(unison, 'ensure_user')
    def test_ssh_auth_peer_changed(self, ensure_user, get_keypair,
                                   write_keys, write_hosts):
        get_keypair.return_value = ('privkey', 'pubkey')

        self.hook_name.return_value = 'cluster-relation-changed'

        self.relation_get.side_effect = [
            'key1',
            'host1',
            'key2',
            'host2',
            '', ''
        ]
        unison.ssh_authorized_peers(peer_interface='cluster',
                                    user='foo', group='foo',
                                    ensure_local_user=True)

        ensure_user.assert_called_with('foo', 'foo')
        get_keypair.assert_called_with('foo')
        write_keys.assert_called_with('foo', ['key1', 'key2'])
        write_hosts.assert_called_with('foo', ['host1', 'host2'])
        self.relation_set.assert_called_with(ssh_authorized_hosts='host1:host2')

    @patch.object(unison, 'write_known_hosts')
    @patch.object(unison, 'write_authorized_keys')
    @patch.object(unison, 'get_keypair')
    @patch.object(unison, 'ensure_user')
    def test_ssh_auth_peer_departed(self, ensure_user, get_keypair,
                                    write_keys, write_hosts):
        get_keypair.return_value = ('privkey', 'pubkey')

        self.hook_name.return_value = 'cluster-relation-departed'

        self.relation_get.side_effect = [
            'key1',
            'host1',
            'key2',
            'host2',
            '', ''
        ]
        unison.ssh_authorized_peers(peer_interface='cluster',
                                    user='foo', group='foo',
                                    ensure_local_user=True)

        ensure_user.assert_called_with('foo', 'foo')
        get_keypair.assert_called_with('foo')
        write_keys.assert_called_with('foo', ['key1', 'key2'])
        write_hosts.assert_called_with('foo', ['host1', 'host2'])
        self.relation_set.assert_called_with(ssh_authorized_hosts='host1:host2')

    def test_collect_authed_hosts(self):
        # only one of the hosts in fake environment has auth'd
        # the local peer
        hosts = unison.collect_authed_hosts('cluster')
        self.assertEquals(hosts, ['cluster0.local'])

    def test_collect_authed_hosts_none_authed(self):
        with patch.object(unison, 'relation_get') as relation_get:
            relation_get.return_value = ''
            hosts = unison.collect_authed_hosts('cluster')
            self.assertEquals(hosts, [])

    @patch.object(unison, 'run_as_user')
    def test_sync_path_to_host(self, run_as_user, verbose=True, gid=None):
        for path in ['/tmp/foo', '/tmp/foo/']:
            unison.sync_path_to_host(path=path, host='clusterhost1',
                                     user='foo', verbose=verbose, gid=gid)
            ex_cmd = ['unison', '-auto', '-batch=true',
                      '-confirmbigdel=false', '-fastcheck=true',
                      '-group=false', '-owner=false',
                      '-prefer=newer', '-times=true']
            if not verbose:
                ex_cmd.append('-silent')
            ex_cmd += ['/tmp/foo', 'ssh://foo@clusterhost1//tmp/foo']
            run_as_user.assert_called_with('foo', ex_cmd, gid)

    @patch.object(unison, 'run_as_user')
    def test_sync_path_to_host_error(self, run_as_user):
        for i, path in enumerate(['/tmp/foo', '/tmp/foo/']):
            run_as_user.side_effect = Exception
            if i == 0:
                unison.sync_path_to_host(path=path, host='clusterhost1',
                                         user='foo', verbose=True, gid=None)
            else:
                self.assertRaises(Exception, unison.sync_path_to_host,
                                  path=path, host='clusterhost1',
                                  user='foo', verbose=True, gid=None,
                                  fatal=True)

            ex_cmd = ['unison', '-auto', '-batch=true',
                      '-confirmbigdel=false', '-fastcheck=true',
                      '-group=false', '-owner=false',
                      '-prefer=newer', '-times=true',
                      '/tmp/foo', 'ssh://foo@clusterhost1//tmp/foo']
            run_as_user.assert_called_with('foo', ex_cmd, None)

    def test_sync_path_to_host_non_verbose(self):
        return self.test_sync_path_to_host(verbose=False)

    def test_sync_path_to_host_with_gid(self):
        return self.test_sync_path_to_host(gid=111)

    @patch.object(unison, 'sync_path_to_host')
    def test_sync_to_peer(self, sync_path_to_host):
        paths = ['/tmp/foo1', '/tmp/foo2']
        host = 'host1'
        unison.sync_to_peer(host, 'foouser', paths, True)
        calls = [call('/tmp/foo1', host, 'foouser', True, None, None, False),
                 call('/tmp/foo2', host, 'foouser', True, None, None, False)]
        sync_path_to_host.assert_has_calls(calls)

    @patch.object(unison, 'sync_path_to_host')
    def test_sync_to_peer_with_gid(self, sync_path_to_host):
        paths = ['/tmp/foo1', '/tmp/foo2']
        host = 'host1'
        unison.sync_to_peer(host, 'foouser', paths, True, gid=111)
        calls = [call('/tmp/foo1', host, 'foouser', True, None, 111, False),
                 call('/tmp/foo2', host, 'foouser', True, None, 111, False)]
        sync_path_to_host.assert_has_calls(calls)

    @patch.object(unison, 'collect_authed_hosts')
    @patch.object(unison, 'sync_to_peer')
    def test_sync_to_peers(self, sync_to_peer, collect_hosts):
        collect_hosts.return_value = ['host1', 'host2', 'host3']
        paths = ['/tmp/foo']
        unison.sync_to_peers(peer_interface='cluster', user='foouser',
                             paths=paths, verbose=True)
        calls = [call('host1', 'foouser', ['/tmp/foo'], True, None, None, False),
                 call('host2', 'foouser', ['/tmp/foo'], True, None, None, False),
                 call('host3', 'foouser', ['/tmp/foo'], True, None, None, False)]
        sync_to_peer.assert_has_calls(calls)

    @patch.object(unison, 'collect_authed_hosts')
    @patch.object(unison, 'sync_to_peer')
    def test_sync_to_peers_with_gid(self, sync_to_peer, collect_hosts):
        collect_hosts.return_value = ['host1', 'host2', 'host3']
        paths = ['/tmp/foo']
        unison.sync_to_peers(peer_interface='cluster', user='foouser',
                             paths=paths, verbose=True, gid=111)
        calls = [call('host1', 'foouser', ['/tmp/foo'], True, None, 111, False),
                 call('host2', 'foouser', ['/tmp/foo'], True, None, 111, False),
                 call('host3', 'foouser', ['/tmp/foo'], True, None, 111, False)]
        sync_to_peer.assert_has_calls(calls)

    @patch.object(unison, 'collect_authed_hosts')
    @patch.object(unison, 'sync_to_peer')
    def test_sync_to_peers_with_cmd(self, sync_to_peer, collect_hosts):
        collect_hosts.return_value = ['host1', 'host2', 'host3']
        paths = ['/tmp/foo']
        cmd = ['dummy_cmd']
        unison.sync_to_peers(peer_interface='cluster', user='foouser',
                             paths=paths, verbose=True, cmd=cmd, gid=111)
        calls = [call('host1', 'foouser', ['/tmp/foo'], True, cmd, 111, False),
                 call('host2', 'foouser', ['/tmp/foo'], True, cmd, 111, False),
                 call('host3', 'foouser', ['/tmp/foo'], True, cmd, 111, False)]
        sync_to_peer.assert_has_calls(calls)
