#!/usr/bin/python

#
# Easy file synchronization among peer units using ssh + unison.
#
# From *both* peer relation -joined and -changed, add a call to
# ssh_authorized_peers() describing the peer relation and the desired
# user + group.  After all peer relations have settled, all hosts should
# be able to connect to on another via key auth'd ssh as the specified user.
#
# Other hooks are then free to synchronize files and directories using
# sync_to_peers().
#
# For a peer relation named 'cluster', for example:
#
# cluster-relation-joined:
# ...
# ssh_authorized_peers(peer_interface='cluster',
#                      user='juju_ssh', group='juju_ssh',
#                      ensure_user=True)
# ...
#
# cluster-relation-changed:
# ...
# ssh_authorized_peers(peer_interface='cluster',
#                      user='juju_ssh', group='juju_ssh',
#                      ensure_user=True)
# ...
#
# Hooks are now free to sync files as easily as:
#
# files = ['/etc/fstab', '/etc/apt.conf.d/']
# sync_to_peers(peer_interface='cluster',
#                user='juju_ssh', paths=[files], verbose=False)
#
# It is assumed the charm itself has setup permissions on each unit
# such that 'juju_ssh' has read + write permissions.  Also assumed
# that the calling charm takes care of leader delegation.
#
# Additionally files can be synchronized only to an specific unit:
# sync_to_peer(slave_address, user='juju_ssh',
#              paths=[files], verbose=False)
import grp
import os
import pwd
import subprocess
import sys

from charmhelpers.core.hookenv import (
    log,
    ERROR,
    INFO,
    relation_get,
    relation_set,
    relation_ids,
    related_units as relation_list,
    unit_get
)


def get_homedir(user):
    try:
        user = pwd.getpwnam(user)
        return user.pw_dir
    except KeyError:
        log('INFO', 'Could not get homedir for user %s: user exists?')
        sys.exit(1)


def get_keypair(user):
    home_dir = get_homedir(user)
    ssh_dir = os.path.join(home_dir, '.ssh')
    if not os.path.isdir(ssh_dir):
        os.mkdir(ssh_dir)

    priv_key = os.path.join(ssh_dir, 'id_rsa')
    if not os.path.isfile(priv_key):
        log('INFO', 'Generating new ssh key for user %s.' % user)
        cmd = ['ssh-keygen', '-q', '-N', '', '-t', 'rsa', '-b', '2048',
               '-f', priv_key]
        subprocess.check_call(cmd)

    pub_key = '%s.pub' % priv_key
    if not os.path.isfile(pub_key):
        log('INFO', 'Generatring missing ssh public key @ %s.' % pub_key)
        cmd = ['ssh-keygen', '-y', '-f', priv_key]
        p = subprocess.check_output(cmd).strip()
        with open(pub_key, 'wb') as out:
            out.write(p)
    subprocess.check_call(['chown', '-R', user, ssh_dir])
    return open(priv_key, 'r').read().strip(), \
        open(pub_key, 'r').read().strip()


def write_authorized_keys(user, keys):
    home_dir = get_homedir(user)
    ssh_dir = os.path.join(home_dir, '.ssh')
    auth_keys = os.path.join(ssh_dir, 'authorized_keys')
    log('INFO', 'Syncing authorized_keys @ %s.' % auth_keys)
    with open(auth_keys, 'wb') as out:
        for k in keys:
            out.write('%s\n' % k)


def write_known_hosts(user, hosts):
    home_dir = get_homedir(user)
    ssh_dir = os.path.join(home_dir, '.ssh')
    known_hosts = os.path.join(ssh_dir, 'known_hosts')
    khosts = []
    for host in hosts:
        cmd = ['ssh-keyscan', '-H', '-t', 'rsa', host]
        remote_key = subprocess.check_output(cmd).strip()
        khosts.append(remote_key)
    log('INFO', 'Syncing known_hosts @ %s.' % known_hosts)
    with open(known_hosts, 'wb') as out:
        for host in khosts:
            out.write('%s\n' % host)


def ensure_user(user, group=None):
    # need to ensure a bash shell'd user exists.
    try:
        pwd.getpwnam(user)
    except KeyError:
        log('INFO', 'Creating new user %s.%s.' % (user, group))
        cmd = ['adduser', '--system', '--shell', '/bin/bash', user]
        if group:
            try:
                grp.getgrnam(group)
            except KeyError:
                subprocess.check_call(['addgroup', group])
            cmd += ['--ingroup', group]
        subprocess.check_call(cmd)


def ssh_authorized_peers(peer_interface, user, group=None,
                         ensure_local_user=False):
    """
    Main setup function, should be called from both peer -changed and -joined
    hooks with the same parameters.
    """
    if ensure_local_user:
        ensure_user(user, group)
    priv_key, pub_key = get_keypair(user)
    hook = os.path.basename(sys.argv[0])
    if hook == '%s-relation-joined' % peer_interface:
        relation_set(ssh_pub_key=pub_key)
    elif hook == '%s-relation-changed' % peer_interface:
        hosts = []
        keys = []
        for r_id in relation_ids(peer_interface):
            for unit in relation_list(r_id):
                settings = relation_get(rid=r_id, unit=unit)
                if 'ssh_pub_key' in settings:
                    keys.append(settings['ssh_pub_key'])
                    hosts.append(settings['private-address'])
                else:
                    log('INFO', 'ssh_authorized_peers(): ssh_pub_key '
                        'missing for unit %s, skipping.' % unit)
        write_authorized_keys(user, keys)
        write_known_hosts(user, hosts)
        authed_hosts = ':'.join(hosts)
        relation_set(ssh_authorized_hosts=authed_hosts)


def _run_as_user(user):
    try:
        user = pwd.getpwnam(user)
    except KeyError:
        log('INFO', 'Invalid user: %s' % user)
        sys.exit(1)
    uid, gid = user.pw_uid, user.pw_gid
    os.environ['HOME'] = user.pw_dir

    def _inner():
        os.setgid(gid)
        os.setuid(uid)
    return _inner


def run_as_user(user, cmd):
    return subprocess.check_output(cmd, preexec_fn=_run_as_user(user), cwd='/')


def sync_to_peer(host, user, paths=[], verbose=False):
    base_cmd = ['unison', '-auto', '-batch=true', '-confirmbigdel=false',
                '-fastcheck=true', '-group=false', '-owner=false',
                '-prefer=newer', '-times=true']
    if not verbose:
        base_cmd.append('-silent')

    for path in paths:
        # removing trailing slash from directory paths, unison
        # doesn't like these.
        if path.endswith('/'):
            path = path[:(len(path) - 1)]
        try:
            cmd = base_cmd + [path, 'ssh://%s@%s/%s' % (user, host, path)]
            log('INFO', 'Syncing local path %s to %s@%s:%s' %
                (path, user, host, path))
            run_as_user(user, cmd)
        except:
            # it may fail for permissions on some files
            log('INFO', 'Error syncing rabbit passwd files')


def sync_to_peers(peer_interface, user, paths=[], verbose=False):
    for r_id in (relation_ids(peer_interface) or []):
        for unit in relation_list(r_id):
            settings = relation_get(rid=r_id, unit=unit)
            try:
                authed_hosts = settings['ssh_authorized_hosts'].split(':')
            except KeyError:
                log('INFO',
                    'unison sync_to_peers: peer has not authorized '
                    '*any* hosts yet.')
                return

            unit_hostname = unit_get('private-address')
            add_host = None
            for authed_host in authed_hosts:
                if unit_hostname == authed_host:
                    add_host = settings['private-address']
            if add_host:
                # sync to this peer
                sync_to_peer(settings['private-address'], user, paths, verbose)
            else:
                log('INFO', 'unison sync_to_peers: peer (%s) '
                    'has not authorized *this* host yet, skipping.' %
                    settings['private-address'])
