import os
import subprocess
import unittest
from testtools import TestCase

from copy import copy
from mock import MagicMock, patch, call

import charmhelpers.contrib.unison as unison


class UnisonTestCase(TestCase):
    def setUp(self):
        super(UnisonTestCase, self).setUp()
        self.user = 'ubuntu'
        self.group = 'users'
        self.host = 'host'

    @patch('pwd.getpwnam')
    def test_get_homedir(self, getpwnam):
        '''Tests that homedir is returned correctly'''
        unison.get_homedir(self.user)
        getpwnam.assert_called_with(self.user)

    @patch('charmhelpers.contrib.unison.get_homedir')
    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('charmhelpers.contrib.unison.log')
    @patch('subprocess.check_output')
    @patch('subprocess.check_call')
    @patch('__builtin__.open')
    def get_test_keypair(self, open, check_call, check_output,
                         log, isfile, isdir, homedir):
        '''Tests that keypairs are generated and written correctly'''
        homedir.return_value = '/home/ubuntu/'
        isdir.return_value = True
        isfile.return_value = False
        unison.get_keypair(self.user)

        # checks that all system calls are called in the right way
        homedir.assert_called_with(self.user)
        check_output.assert_called_with(['ssh-keygen', '-y', '-f',
                                        '/home/ubuntu/.ssh/id_rsa'])
        check_call.assert_called_with(['chown', '-R',
                                      self.user, '/home/ubuntu/.ssh'])

    @patch('charmhelpers.contrib.unison.get_homedir')
    @patch('charmhelpers.contrib.unison.log')
    @patch('__builtin__.open')
    def test_write_authorized_keys(self, open, log, homedir):
        '''Tests that keys are written into proper directory'''
        keys = ['key1', 'key2', 'key3']
        homedir.return_value = '/home/ubuntu/'
        unison.write_authorized_keys(self.user, keys)
        open.assert_called_with('/home/ubuntu/.ssh/authorized_keys', 'wb')

    @patch('charmhelpers.contrib.unison.get_homedir')
    @patch('charmhelpers.contrib.unison.log')
    @patch('__builtin__.open')
    @patch('subprocess.check_output')
    def test_write_known_hosts(self, check_output, open, log, homedir):
        '''Tests that hosts are written properly'''
        homedir.return_value = '/home/ubuntu/'
        hosts = [self.host]
        unison.write_known_hosts(self.user, hosts)
        for host in hosts:
            check_output.assert_called_with(['ssh-keyscan',
                                            '-H', '-t', 'rsa', host])
        open.assert_called_with('/home/ubuntu/.ssh/known_hosts', 'wb')

    @patch('pwd.getpwnam')
    def test_ensure_user_without_key_error(self, getpwnam):
        '''Tests user creation, that already exists'''
        unison.ensure_user(self.user, self.group)
        getpwnam.assert_called_with(self.user)

    @patch('pwd.getpwnam')
    @patch('grp.getgrnam')
    @patch('charmhelpers.contrib.unison.log')
    @patch('subprocess.check_call')
    def test_ensure_user_group_with_key_error(self, check_call, log,
                                              getgrnam, getpwnam):
        '''Tests creation of user that does not exist'''
        e = KeyError('Invalid user')
        getpwnam.side_effect = e
        unison.ensure_user(self.user, self.group)
        getpwnam.assert_called_with(self.user)
        getgrnam.assert_called_with(self.group)
        # checks generation of user
        check_call.assert_called_with(
            ['adduser', '--system', '--shell', '/bin/bash', self.user,
             '--ingroup', self.group])

    @patch('charmhelpers.contrib.unison.ensure_user')
    @patch('charmhelpers.contrib.unison.get_keypair')
    @patch('os.path.basename')
    @patch('charmhelpers.contrib.unison.relation_set')
    def test_ssh_autorized_peers_relation_joined(self, relation_set, basename,
                                                 get_keypair, ensure_user):
        '''Tests ssh method on cluster joined'''
        basename.return_value = 'cluster-relation-joined'
        get_keypair.return_value = ['priv', 'pub']
        unison.ssh_authorized_peers('cluster', self.user, self.group, True)
        ensure_user.assert_called_with(self.user, self.group)
        get_keypair.assert_called_with(self.user)
        # only need to check that relation_set is called
        relation_set.assert_called_with(ssh_pub_key='pub')

    @patch('charmhelpers.contrib.unison.ensure_user')
    @patch('charmhelpers.contrib.unison.get_keypair')
    @patch('os.path.basename')
    @patch('charmhelpers.contrib.unison.relation_set')
    @patch('charmhelpers.contrib.unison.relation_ids')
    @patch('charmhelpers.contrib.unison.relation_list')
    @patch('charmhelpers.contrib.unison.relation_get')
    @patch('charmhelpers.contrib.unison.write_authorized_keys')
    @patch('charmhelpers.contrib.unison.write_known_hosts')
    @patch('charmhelpers.contrib.unison.log')
    def test_ssh_autorized_peers_relation_changed(
            self, log, write_known_hosts, write_authorized_keys, relation_get,
            relation_list, relation_ids, relation_set, basename, get_keypair,
            ensure_user):
        '''Tests ssh for a cluster changed relation'''
        basename.return_value = 'cluster-relation-changed'
        get_keypair.return_value = ['pub', 'priv']
        relation_ids.return_value = ['id0']
        relation_list.return_value = ['unit0']
        relation_get.return_value = {'ssh_pub_key': 'pub',
                                     'private-address': self.host}
        unison.ssh_authorized_peers('cluster', self.user, self.group, True)

        # need to check writing keys, hosts, and properly setting relation vars
        ensure_user.assert_called_with(self.user, self.group)
        get_keypair.assert_called_with(self.user)
        write_authorized_keys.assert_called_with(self.user, ['pub'])
        write_known_hosts.assert_called_with(self.user, [self.host])
        relation_set.assert_called_with(ssh_authorized_hosts=self.host)

    @patch('charmhelpers.contrib.unison.run_as_user')
    @patch('charmhelpers.contrib.unison.log')
    def test_sync_to_peer(self, log, run_as_user):
        '''Tests that unison call is properly executed'''
        paths = ['path1']
        unison.sync_to_peer(self.host, self.user, paths, False)
        base_cmd = ['unison', '-auto', '-batch=true', '-confirmbigdel=false',
                    '-fastcheck=true', '-group=false', '-owner=false',
                    '-prefer=newer', '-times=true', '-silent']
        for path in paths:
            base_cmd += [path, 'ssh://%s@%s/%s' % (self.user, self.host, path)]
        run_as_user.assert_called_with(self.user, base_cmd)

    @patch('charmhelpers.contrib.unison.relation_ids')
    @patch('charmhelpers.contrib.unison.relation_list')
    @patch('charmhelpers.contrib.unison.relation_get')
    @patch('charmhelpers.contrib.unison.unit_get')
    @patch('charmhelpers.contrib.unison.sync_to_peer')
    def test_sync_to_peers(self, sync_to_peer, unit_get, relation_get,
                           relation_list, relation_ids):
        '''Tests that all the calls to sync_to_peer
        for the unit are properly executed'''
        relation_ids.return_value = ['id0']
        relation_list.return_value = ['unit0']
        relation_get.return_value = {'ssh_authorized_hosts': self.host,
                                     'private-address': self.host}
        unit_get.return_value = self.host
        unison.sync_to_peers('cluster', self.user, ['path'], False)
        sync_to_peer.assert_called_with(self.host, self.user, ['path'], False)
