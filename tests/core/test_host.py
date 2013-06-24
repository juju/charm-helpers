from collections import OrderedDict
from contextlib import contextmanager
import os
import subprocess

from mock import patch, call, MagicMock
from testtools import TestCase

from charmhelpers.core import host


MOUNT_LINES = ("""
rootfs / rootfs rw 0 0
sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
udev /dev devtmpfs rw,relatime,size=8196788k,nr_inodes=2049197,mode=755 0 0
devpts /dev/pts devpts """
               """rw,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000 0 0
""").strip().split('\n')

FAKE_APT_CACHE = {
    # an installed package
    'vim': {
        'current_ver': '2:7.3.547-6ubuntu5'
    },
    # a uninstalled installation candidate
    'emacs': {
    }
}

def fake_apt_cache():
    def _get(package):
        pkg = MagicMock()
        if package not in FAKE_APT_CACHE:
            raise KeyError
        pkg.name = package
        if 'current_ver' in FAKE_APT_CACHE[package]:
            pkg.current_ver = FAKE_APT_CACHE[package]['current_ver']
        else:
            pkg.current_ver = None
        return pkg
    cache = MagicMock()
    cache.__getitem__.side_effect = _get
    return cache

@contextmanager
def patch_open():
    '''Patch open() to allow mocking both open() itself and the file that is
    yielded.

    Yields the mock for "open" and "file", respectively.'''
    mock_open = MagicMock(spec=open)
    mock_file = MagicMock(spec=file)

    @contextmanager
    def stub_open(*args, **kwargs):
        mock_open(*args, **kwargs)
        yield mock_file

    with patch('__builtin__.open', stub_open):
        yield mock_open, mock_file


class HelpersTest(TestCase):
    @patch('subprocess.call')
    def test_runs_service_action(self, mock_call):
        mock_call.return_value = 0
        action = 'some-action'
        service_name = 'foo-service'

        result = host.service(action, service_name)

        self.assertTrue(result)
        mock_call.assert_called_with(['service', service_name, action])

    @patch('subprocess.call')
    def test_returns_false_when_service_fails(self, mock_call):
        mock_call.return_value = 1
        action = 'some-action'
        service_name = 'foo-service'

        result = host.service(action, service_name)

        self.assertFalse(result)
        mock_call.assert_called_with(['service', service_name, action])

    @patch.object(host, 'service')
    def test_starts_a_service(self, service):
        service_name = 'foo-service'
        host.service_start(service_name)

        service.assert_called_with('start', service_name)

    @patch.object(host, 'service')
    def test_stops_a_service(self, service):
        service_name = 'foo-service'
        host.service_stop(service_name)

        service.assert_called_with('stop', service_name)

    @patch.object(host, 'service')
    def test_restarts_a_service(self, service):
        service_name = 'foo-service'
        host.service_restart(service_name)

        service.assert_called_with('restart', service_name)

    @patch.object(host, 'service')
    def test_reloads_a_service(self, service):
        service_name = 'foo-service'
        service.side_effect = [True]
        host.service_reload(service_name)

        service.assert_called_with('reload', service_name)

    @patch.object(host, 'service')
    def test_failed_reload_restarts_a_service(self, service):
        service_name = 'foo-service'
        service.side_effect = [False, True]
        host.service_reload(service_name, restart_on_failure=True)

        service.assert_has_calls([
                            call('reload', service_name),
                            call('restart', service_name)
                            ])

    @patch.object(host, 'service')
    def test_failed_reload_without_restart(self, service):
        service_name = 'foo-service'
        service.side_effect = [False]
        host.service_reload(service_name)

        service.assert_called_with('reload', service_name)

    @patch('pwd.getpwnam')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_adds_a_user_if_it_doesnt_exist(self, log, check_call, getpwnam):
        username = 'johndoe'
        password = 'eodnhoj'
        shell = '/bin/bash'
        existing_user_pwnam = KeyError('user not found')
        new_user_pwnam = 'some user pwnam'

        getpwnam.side_effect = [existing_user_pwnam, new_user_pwnam]

        result = host.adduser(username, password)

        self.assertEqual(result, new_user_pwnam)
        check_call.assert_called_with([
            'useradd',
            '--create-home',
            '--shell', shell,
            '--password', password,
            username
        ])
        getpwnam.assert_called_with(username)

    @patch('pwd.getpwnam')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_doesnt_add_user_if_it_already_exists(self, log, check_call,
                                                  getpwnam):
        username = 'johndoe'
        password = 'eodnhoj'
        existing_user_pwnam = 'some user pwnam'

        getpwnam.return_value = existing_user_pwnam

        result = host.adduser(username, password)

        self.assertEqual(result, existing_user_pwnam)
        self.assertFalse(check_call.called)
        getpwnam.assert_called_with(username)

    @patch('pwd.getpwnam')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_adds_a_user_with_different_shell(self, log, check_call, getpwnam):
        username = 'johndoe'
        password = 'eodnhoj'
        shell = '/bin/zsh'
        existing_user_pwnam = KeyError('user not found')
        new_user_pwnam = 'some user pwnam'

        getpwnam.side_effect = [existing_user_pwnam, new_user_pwnam]

        result = host.adduser(username, password, shell=shell)

        self.assertEqual(result, new_user_pwnam)
        check_call.assert_called_with([
            'useradd',
            '--create-home',
            '--shell', shell,
            '--password', password,
            username
        ])
        getpwnam.assert_called_with(username)

    @patch('pwd.getpwnam')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_adds_a_systemuser(self, log, check_call, getpwnam):
        username = 'johndoe'
        existing_user_pwnam = KeyError('user not found')
        new_user_pwnam = 'some user pwnam'

        getpwnam.side_effect = [existing_user_pwnam, new_user_pwnam]

        result = host.adduser(username, system_user=True)

        self.assertEqual(result, new_user_pwnam)
        check_call.assert_called_with([
            'useradd',
            '--system',
            username
        ])
        getpwnam.assert_called_with(username)

    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_adds_a_user_to_a_group(self, log, check_call):
        username = 'foo'
        group = 'bar'

        host.add_user_to_group(username, group)

        check_call.assert_called_with([
            'gpasswd', '-a',
            username,
            group
        ])

    @patch('subprocess.check_output')
    @patch.object(host, 'execution_environment')
    @patch.object(host, 'log')
    def test_rsyncs_a_path(self, log, execution_environment, check_output):
        execution_environment.return_value = {
            'foo': 'FOO',
            'bar': 'BAR',
        }
        from_path = '/from/this/path/{foo}'
        to_path = '/to/this/path/{bar}'
        check_output.return_value = ' some output '

        result = host.rsync(from_path, to_path)

        self.assertEqual(result, 'some output')
        check_output.assert_called_with(['/usr/bin/rsync', '-r', '--delete',
                                         '--executability',
                                         '/from/this/path/FOO',
                                         '/to/this/path/BAR'])

    @patch('subprocess.check_call')
    @patch.object(host, 'execution_environment')
    @patch.object(host, 'log')
    def test_creates_a_symlink(self, log, execution_environment, check_call):
        execution_environment.return_value = {
            'foo': 'FOO',
            'bar': 'BAR',
        }
        source = '/from/this/path/{foo}'
        destination = '/to/this/path/{bar}'

        host.symlink(source, destination)

        check_call.assert_called_with(['ln', '-sf',
                                       '/from/this/path/FOO',
                                       '/to/this/path/BAR'])

    @patch('pwd.getpwnam')
    @patch('grp.getgrnam')
    @patch.object(host, 'execution_environment')
    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_creates_a_directory_if_it_doesnt_exist(self, os_, log,
                                                    execution_environment,
                                                    getgrnam, getpwnam):
        execution_environment.return_value = {
            'foo': 'FOO',
            'bar': 'BAR',
        }
        uid = 123
        gid = 234
        owner = 'some-user-{foo}'
        group = 'some-group-{bar}'
        path = '/some/other/path/from/link'
        realpath = '/some/path'
        path_exists = False
        perms = 0644

        getpwnam.return_value.pw_uid = uid
        getgrnam.return_value.gr_gid = gid
        os_.path.abspath.return_value = realpath
        os_.path.exists.return_value = path_exists

        host.mkdir(path, owner=owner, group=group, perms=perms)

        getpwnam.assert_called_with('some-user-FOO')
        getgrnam.assert_called_with('some-group-BAR')
        os_.path.abspath.assert_called_with(path)
        os_.path.exists.assert_called_with(realpath)
        os_.makedirs.assert_called_with(realpath, perms)
        os_.chown.assert_called_with(realpath, uid, gid)

    @patch.object(host, 'execution_environment')
    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_creates_a_directory_with_defaults(self, os_, log,
                                               execution_environment):
        execution_environment.return_value = {
            'foo': 'FOO',
            'bar': 'BAR',
        }
        uid = 0
        gid = 0
        path = '/some/other/path/from/link'
        realpath = '/some/path'
        path_exists = False
        perms = 0555

        os_.path.abspath.return_value = realpath
        os_.path.exists.return_value = path_exists

        host.mkdir(path)

        os_.path.abspath.assert_called_with(path)
        os_.path.exists.assert_called_with(realpath)
        os_.makedirs.assert_called_with(realpath, perms)
        os_.chown.assert_called_with(realpath, uid, gid)

    @patch('pwd.getpwnam')
    @patch('grp.getgrnam')
    @patch.object(host, 'execution_environment')
    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_removes_file_with_same_path_before_mkdir(self, os_, log,
                                                      execution_environment,
                                                      getgrnam, getpwnam):
        execution_environment.return_value = {
            'foo': 'FOO',
            'bar': 'BAR',
        }
        uid = 123
        gid = 234
        owner = 'some-user-{foo}'
        group = 'some-group-{bar}'
        path = '/some/other/path/from/link'
        realpath = '/some/path'
        path_exists = True
        force = True
        is_dir = False
        perms = 0644

        getpwnam.return_value.pw_uid = uid
        getgrnam.return_value.gr_gid = gid
        os_.path.abspath.return_value = realpath
        os_.path.exists.return_value = path_exists
        os_.path.isdir.return_value = is_dir

        host.mkdir(path, owner=owner, group=group, perms=perms, force=force)

        getpwnam.assert_called_with('some-user-FOO')
        getgrnam.assert_called_with('some-group-BAR')
        os_.path.abspath.assert_called_with(path)
        os_.path.exists.assert_called_with(realpath)
        os_.unlink.assert_called_with(realpath)
        self.assertFalse(os_.makedirs.called)
        os_.chown.assert_called_with(realpath, uid, gid)

    @patch('pwd.getpwnam')
    @patch('grp.getgrnam')
    @patch.object(host, 'execution_environment')
    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_writes_content_to_a_file(self, os_, log, execution_environment,
                                      getgrnam, getpwnam):
        execution_environment.return_value = {
            'foo': 'FOO',
            'bar': 'BAR',
            'baz': 'BAZ',
            'juju': 'DevOps Distilled',
        }
        uid = 123
        gid = 234
        owner = 'some-user-{foo}'
        group = 'some-group-{bar}'
        path = '/some/path/{baz}'
        fmtstr = 'what is {juju}'
        perms = 0644
        fileno = 'some-fileno'

        getpwnam.return_value.pw_uid = uid
        getgrnam.return_value.gr_gid = gid

        with patch_open() as (mock_open, mock_file):
            mock_file.fileno.return_value = fileno

            host.write_file(path, fmtstr, owner=owner, group=group,
                            perms=perms)

            getpwnam.assert_called_with('some-user-FOO')
            getgrnam.assert_called_with('some-group-BAR')
            mock_open.assert_called_with('/some/path/BAZ', 'w')
            os_.fchown.assert_called_with(fileno, uid, gid)
            os_.fchmod.assert_called_with(fileno, perms)
            mock_file.write.assert_called_with('what is DevOps Distilled')

    @patch.object(host, 'execution_environment')
    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_writes_content_with_default(self, os_, log,
                                         execution_environment):
        execution_environment.return_value = {
            'foo': 'FOO',
            'bar': 'BAR',
            'baz': 'BAZ',
            'juju': 'DevOps Distilled',
        }
        uid = 0
        gid = 0
        path = '/some/path/{baz}'
        fmtstr = 'what is {juju}'
        perms = 0444
        fileno = 'some-fileno'

        with patch_open() as (mock_open, mock_file):
            mock_file.fileno.return_value = fileno

            host.write_file(path, fmtstr)

            mock_open.assert_called_with('/some/path/BAZ', 'w')
            os_.fchown.assert_called_with(fileno, uid, gid)
            os_.fchmod.assert_called_with(fileno, perms)
            mock_file.write.assert_called_with('what is DevOps Distilled')

    @patch.object(host, 'execution_environment')
    @patch.object(host, 'log')
    @patch.object(host, 'os')
    @patch.object(host, 'write_file')
    def test_renders_a_template_file(self, write_file, os_, log,
                                     execution_environment):
        execution_environment.return_value = {
            'foo': 'FOO',
            'bar': 'BAR',
        }
        source = '/some/path/{foo}'
        destination = '/some/path/{bar}'
        content = 'some-content'

        with patch_open() as (mock_open, mock_file):
            mock_file.read.return_value = content

            host.render_template_file(source, destination, foo2='2')

            mock_open.assert_called_with('/some/path/FOO', 'r')
            write_file.assert_called_with('/some/path/BAR', content, foo2='2')

    @patch('subprocess.call')
    @patch.object(host, 'log')
    def test_installs_apt_packages(self, log, mock_call):
        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        host.apt_install(packages, options)

        mock_call.assert_called_with(['apt-get', '-y', '--foo', '--bar',
                                      'install', 'foo', 'bar'])

    @patch('subprocess.call')
    @patch.object(host, 'log')
    def test_installs_apt_packages_without_options(self, log, mock_call):
        packages = ['foo', 'bar']

        host.apt_install(packages)

        mock_call.assert_called_with(['apt-get', '-y', 'install', 'foo',
                                      'bar'])

    @patch('subprocess.call')
    @patch.object(host, 'log')
    def test_installs_apt_packages_as_string(self, log, mock_call):
        packages = 'foo bar'
        options = ['--foo', '--bar']

        host.apt_install(packages, options)

        mock_call.assert_called_with(['apt-get', '-y', '--foo', '--bar',
                                      'install', 'foo bar'])

    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_installs_apt_packages_with_possible_errors(self, log, check_call):
        packages = ['foo', 'bar']
        options = ['--foo', '--bar']

        host.apt_install(packages, options, fatal=True)

        check_call.assert_called_with(['apt-get', '-y', '--foo', '--bar',
                                       'install', 'foo', 'bar'])

    @patch('subprocess.check_call')
    def test_apt_update_fatal(self, check_call):
        host.apt_update(fatal=True)
        check_call.assert_called_with(['apt-get', 'update'])

    @patch('subprocess.call')
    def test_apt_update_nonfatal(self, call):
        host.apt_update()
        call.assert_called_with(['apt-get', 'update'])

    @patch('apt_pkg.Cache')
    def test_filter_packages_missing(self, cache):
        cache.side_effect = fake_apt_cache
        result = host.filter_installed_packages(['vim', 'emacs'])
        self.assertEquals(result, ['emacs'])

    @patch('apt_pkg.Cache')
    def test_filter_packages_none_missing(self, cache):
        cache.side_effect = fake_apt_cache
        result = host.filter_installed_packages(['vim'])
        self.assertEquals(result, [])

    @patch.object(host, 'log')
    @patch('apt_pkg.Cache')
    def test_filter_packages_not_available(self, cache, log):
        cache.side_effect = fake_apt_cache
        result = host.filter_installed_packages(['vim', 'joe'])
        self.assertEquals(result, ['joe'])
        log.assert_called_with('Package joe has no installation candidate.',
                               level='WARNING')

    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_mounts_a_device(self, log, check_output):
        device = '/dev/guido'
        mountpoint = '/mnt/guido'
        options = 'foo,bar'

        result = host.mount(device, mountpoint, options)

        self.assertTrue(result)
        check_output.assert_called_with(['mount', '-o', 'foo,bar',
                                         '/dev/guido', '/mnt/guido'])

    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_doesnt_mount_on_error(self, log, check_output):
        device = '/dev/guido'
        mountpoint = '/mnt/guido'
        options = 'foo,bar'

        error = subprocess.CalledProcessError(123, 'mount it', 'Oops...')
        check_output.side_effect = error

        result = host.mount(device, mountpoint, options)

        self.assertFalse(result)
        check_output.assert_called_with(['mount', '-o', 'foo,bar',
                                         '/dev/guido', '/mnt/guido'])

    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_mounts_a_device_without_options(self, log, check_output):
        device = '/dev/guido'
        mountpoint = '/mnt/guido'

        result = host.mount(device, mountpoint)

        self.assertTrue(result)
        check_output.assert_called_with(['mount', '/dev/guido', '/mnt/guido'])

    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_umounts_a_device(self, log, check_output):
        mountpoint = '/mnt/guido'

        result = host.umount(mountpoint)

        self.assertTrue(result)
        check_output.assert_called_with(['umount', '/mnt/guido'])

    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_doesnt_umount_on_error(self, log, check_output):
        mountpoint = '/mnt/guido'

        error = subprocess.CalledProcessError(123, 'mount it', 'Oops...')
        check_output.side_effect = error

        result = host.umount(mountpoint)

        self.assertFalse(result)
        check_output.assert_called_with(['umount', '/mnt/guido'])

    def test_lists_the_mount_points(self):
        with patch_open() as (mock_open, mock_file):
            mock_file.readlines.return_value = MOUNT_LINES
            result = host.mounts()

            self.assertEqual(result, [
                ['/', 'rootfs'],
                ['/sys', 'sysfs'],
                ['/proc', 'proc'],
                ['/dev', 'udev'],
                ['/dev/pts', 'devpts']
            ])
            mock_open.assert_called_with('/proc/mounts')

    _hash_files = {
        '/etc/exists.conf': 'lots of nice ceph configuration',
        '/etc/missing.conf': None
    }

    @patch('hashlib.md5')
    @patch('os.path.exists')
    def test_file_hash_exists(self, exists, md5):
        filename = '/etc/exists.conf'
        exists.side_effect = [True]
        m = md5()
        m.hexdigest.return_value = self._hash_files[filename]
        with patch_open() as (mock_open, mock_file):
            mock_file.read.return_value = self._hash_files[filename]
            result = host.file_hash(filename)
            self.assertEqual(result, self._hash_files[filename])

    @patch('os.path.exists')
    def test_file_hash_missing(self, exists):
        filename = '/etc/missing.conf'
        exists.side_effect = [False]
        with patch_open() as (mock_open, mock_file):
            mock_file.read.return_value = self._hash_files[filename]
            result = host.file_hash(filename)
            self.assertEqual(result, None)

    @patch.object(host, 'service')
    @patch('os.path.exists')
    def test_restart_no_changes(self, exists, service):
        file_name = '/etc/missing.conf'
        restart_map = {
            file_name: ['test-service']
            }
        exists.side_effect = [False, False]

        @host.restart_on_change(restart_map)
        def make_no_changes():
            pass

        make_no_changes()

        assert not service.called

        exists.assert_has_calls([
            call(file_name),
        ])

    @patch.object(host, 'service')
    @patch('os.path.exists')
    def test_restart_on_change(self, exists, service):
        file_name = '/etc/missing.conf'
        restart_map = {
            file_name: ['test-service']
            }
        exists.side_effect = [False, True]

        @host.restart_on_change(restart_map)
        def make_some_changes(mock_file):
            mock_file.read.return_value = "newstuff"

        with patch_open() as (mock_open, mock_file):
            make_some_changes(mock_file)

        for service_name in restart_map[file_name]:
            service.assert_called_with('restart', service_name)

        exists.assert_has_calls([
            call(file_name),
        ])

    @patch.object(host, 'service')
    @patch('os.path.exists')
    def test_multiservice_restart_on_change(self, exists, service):
        file_name_one = '/etc/missing.conf'
        file_name_two = '/etc/exists.conf'
        restart_map = {
            file_name_one: ['test-service'],
            file_name_two: ['test-service', 'test-service2']
            }
        exists.side_effect = [False, True, True, True]

        @host.restart_on_change(restart_map)
        def make_some_changes():
            pass

        with patch_open() as (mock_open, mock_file):
            mock_file.read.side_effect = ['exists', 'missing', 'exists2']
            make_some_changes()

        # Restart should only happen once per service
        for svc in ['test-service2', 'test-service']:
            c = call('restart', svc)
            self.assertEquals(1, service.call_args_list.count(c))

        exists.assert_has_calls([
            call(file_name_one),
            call(file_name_two)
        ])

    @patch.object(host, 'service')
    @patch('os.path.exists')
    def test_multiservice_restart_on_change_in_order(self, exists, service):
        restart_map = OrderedDict([
            ('/etc/cinder/cinder.conf', ['some-api']),
            ('/etc/haproxy/haproxy.conf',  ['haproxy'])
        ])
        exists.side_effect = [False, True, True, True]

        @host.restart_on_change(restart_map)
        def make_some_changes():
            pass

        with patch_open() as (mock_open, mock_file):
            mock_file.read.side_effect = ['exists', 'missing', 'exists2']
            make_some_changes()

        # Restarts should happen in the order they are described in the
        # restart map.
        expected = [
            call('restart', 'some-api'),
            call('restart', 'haproxy')
        ]
        self.assertEquals(expected, service.call_args_list)
