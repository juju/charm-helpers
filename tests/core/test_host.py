import os.path
from collections import OrderedDict
import subprocess
from tempfile import mkdtemp
from shutil import rmtree
from textwrap import dedent

import imp

from charmhelpers import osplatform
from mock import patch, call, mock_open
from testtools import TestCase
from tests.helpers import patch_open
from tests.helpers import mock_open as mocked_open
import six

from charmhelpers.core import host
from charmhelpers.fetch import ubuntu_apt_pkg


MOUNT_LINES = ("""
rootfs / rootfs rw 0 0
sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
udev /dev devtmpfs rw,relatime,size=8196788k,nr_inodes=2049197,mode=755 0 0
devpts /dev/pts devpts """
               """rw,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000 0 0
""").strip().split('\n')

LSB_RELEASE = '''DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=13.10
DISTRIB_CODENAME=saucy
DISTRIB_DESCRIPTION="Ubuntu Saucy Salamander (development branch)"
'''

OS_RELEASE = '''NAME="CentOS Linux"
ANSI_COLOR="0;31"
ID_LIKE="rhel fedora"
VERSION_ID="7"
BUG_REPORT_URL="https://bugs.centos.org/"
CENTOS_MANTISBT_PROJECT="CentOS-7"
PRETTY_NAME="CentOS Linux 7 (Core)"
VERSION="7 (Core)"
REDHAT_SUPPORT_PRODUCT_VERSION="7"
CENTOS_MANTISBT_PROJECT_VERSION="7"
REDHAT_SUPPORT_PRODUCT="centos"
HOME_URL="https://www.centos.org/"
CPE_NAME="cpe:/o:centos:centos:7"
ID="centos"
'''

IP_LINE_ETH0 = b"""
2: eth0: <BROADCAST,MULTICAST,SLAVE,UP,LOWER_UP> mtu 1500 qdisc mq master bond0 state UP qlen 1000
    link/ether e4:11:5b:ab:a7:3c brd ff:ff:ff:ff:ff:ff
"""

IP_LINE_ETH100 = b"""
2: eth100: <BROADCAST,MULTICAST,SLAVE,UP,LOWER_UP> mtu 1500 qdisc mq master bond0 state UP qlen 1000
    link/ether e4:11:5b:ab:a7:3d brd ff:ff:ff:ff:ff:ff
"""

IP_LINE_ETH0_VLAN = b"""
6: eth0.10@eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default
    link/ether 08:00:27:16:b9:5f brd ff:ff:ff:ff:ff:ff
"""

IP_LINE_ETH1 = b"""
3: eth1: <BROADCAST,MULTICAST> mtu 1546 qdisc noop state DOWN qlen 1000
    link/ether e4:11:5b:ab:a7:3c brd ff:ff:ff:ff:ff:ff
"""

IP_LINE_HWADDR = b"""2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP qlen 1000\\    link/ether e4:11:5b:ab:a7:3c brd ff:ff:ff:ff:ff:ff"""

IP_LINES = IP_LINE_ETH0 + IP_LINE_ETH1 + IP_LINE_ETH0_VLAN + IP_LINE_ETH100

IP_LINE_BONDS = b"""
6: bond0.10@bond0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default
link/ether 08:00:27:16:b9:5f brd ff:ff:ff:ff:ff:ff
"""


class HelpersTest(TestCase):
    @patch('charmhelpers.core.host.lsb_release')
    @patch('os.path')
    def test_init_is_systemd_service_snap(self, path, lsb_release):
        # If Service begins with 'snap.' it should be True
        service_name = "snap.package.service"
        self.assertTrue(host.init_is_systemd(service_name=service_name))

        # If service doesn't begin with snap. use normal evaluation.
        service_name = "package.service"
        lsb_release.return_value = {'DISTRIB_CODENAME': 'whatever'}
        path.isdir.return_value = True
        self.assertTrue(host.init_is_systemd(service_name=service_name))
        path.isdir.assert_called_with('/run/systemd/system')

    @patch('charmhelpers.core.host.lsb_release')
    @patch('os.path')
    def test_init_is_systemd_upstart(self, path, lsb_release):
        """Upstart based init is correctly detected"""
        lsb_release.return_value = {'DISTRIB_CODENAME': 'whatever'}
        path.isdir.return_value = False
        self.assertFalse(host.init_is_systemd())
        path.isdir.assert_called_with('/run/systemd/system')

    @patch('charmhelpers.core.host.lsb_release')
    @patch('os.path')
    def test_init_is_systemd_system(self, path, lsb_release):
        """Systemd based init is correctly detected"""
        lsb_release.return_value = {'DISTRIB_CODENAME': 'whatever'}
        path.isdir.return_value = True
        self.assertTrue(host.init_is_systemd())
        path.isdir.assert_called_with('/run/systemd/system')

    @patch('charmhelpers.core.host.lsb_release')
    @patch('os.path')
    def test_init_is_systemd_trusty(self, path, lsb_release):
        # Never returns true under trusty, even if the systemd
        # packages have been installed. lp:1670944
        lsb_release.return_value = {'DISTRIB_CODENAME': 'trusty'}
        path.isdir.return_value = True
        self.assertFalse(host.init_is_systemd())
        self.assertFalse(path.isdir.called)

    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.call')
    def test_runs_service_action(self, mock_call, systemd):
        systemd.return_value = False
        mock_call.return_value = 0
        action = 'some-action'
        service_name = 'foo-service'

        result = host.service(action, service_name)

        self.assertTrue(result)
        mock_call.assert_called_with(['service', service_name, action])

    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.call')
    def test_runs_systemctl_action(self, mock_call, systemd):
        """Ensure that service calls under systemd call 'systemctl'."""
        systemd.return_value = True
        mock_call.return_value = 0
        action = 'some-action'
        service_name = 'foo-service'

        result = host.service(action, service_name)

        self.assertTrue(result)
        mock_call.assert_called_with(['systemctl', action, service_name])

    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.call')
    def test_returns_false_when_service_fails(self, mock_call, systemd):
        systemd.return_value = False
        mock_call.return_value = 1
        action = 'some-action'
        service_name = 'foo-service'

        result = host.service(action, service_name)

        self.assertFalse(result)
        mock_call.assert_called_with(['service', service_name, action])

    @patch.object(host, 'service')
    def test_starts_a_service(self, service):
        service_name = 'foo-service'
        service.side_effect = [True]
        self.assertTrue(host.service_start(service_name))

        service.assert_called_with('start', service_name)

    @patch.object(host, 'service')
    def test_starts_a_service_with_parms(self, service):
        service_name = 'foo-service'
        service.side_effect = [True]
        self.assertTrue(host.service_start(service_name, id=4))

        service.assert_called_with('start', service_name, id=4)

    @patch.object(host, 'service')
    def test_stops_a_service(self, service):
        service_name = 'foo-service'
        service.side_effect = [True]
        self.assertTrue(host.service_stop(service_name))

        service.assert_called_with('stop', service_name)

    @patch.object(host, 'service')
    def test_restarts_a_service(self, service):
        service_name = 'foo-service'
        service.side_effect = [True]
        self.assertTrue(host.service_restart(service_name))

        service.assert_called_with('restart', service_name)

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch.object(host, 'service')
    def test_pauses_a_running_systemd_unit(self, service, systemd,
                                           service_running):
        """Pause on a running systemd unit will be stopped and disabled."""
        service_name = 'foo-service'
        service_running.return_value = True
        systemd.return_value = True
        self.assertTrue(host.service_pause(service_name))
        service.assert_has_calls([
            call('stop', service_name),
            call('disable', service_name),
            call('mask', service_name)])

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch.object(host, 'service')
    def test_resumes_a_stopped_systemd_unit(self, service, systemd,
                                            service_running):
        """Resume on a stopped systemd unit will be started and enabled."""
        service_name = 'foo-service'
        service_running.return_value = False
        systemd.return_value = True
        self.assertTrue(host.service_resume(service_name))
        service.assert_has_calls([
            call('unmask', service_name),
            # Ensures a package starts up if disabled but not masked,
            # per lp:1692178
            call('enable', service_name),
            call('start', service_name)])

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch.object(host, 'service')
    def test_pauses_a_running_upstart_service(self, service, systemd,
                                              service_running):
        """Pause on a running service will call service stop."""
        service_name = 'foo-service'
        service.side_effect = [True]
        systemd.return_value = False
        service_running.return_value = True
        tempdir = mkdtemp(prefix="test_pauses_an_upstart_service")
        conf_path = os.path.join(tempdir, "{}.conf".format(service_name))
        # Just needs to exist
        with open(conf_path, "w") as fh:
            fh.write("")
        self.addCleanup(rmtree, tempdir)
        self.assertTrue(host.service_pause(service_name, init_dir=tempdir))

        service.assert_called_with('stop', service_name)
        override_path = os.path.join(
            tempdir, "{}.override".format(service_name))
        with open(override_path, "r") as fh:
            override_contents = fh.read()
        self.assertEqual("manual\n", override_contents)

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch.object(host, 'service')
    def test_pauses_a_stopped_upstart_service(self, service, systemd,
                                              service_running):
        """Pause on a stopped service will not call service stop."""
        service_name = 'foo-service'
        service.side_effect = [True]
        systemd.return_value = False
        service_running.return_value = False
        tempdir = mkdtemp(prefix="test_pauses_an_upstart_service")
        conf_path = os.path.join(tempdir, "{}.conf".format(service_name))
        # Just needs to exist
        with open(conf_path, "w") as fh:
            fh.write("")
        self.addCleanup(rmtree, tempdir)
        self.assertTrue(host.service_pause(service_name, init_dir=tempdir))

        # Stop isn't called because service is already stopped
        self.assertRaises(
            AssertionError, service.assert_called_with, 'stop', service_name)
        override_path = os.path.join(
            tempdir, "{}.override".format(service_name))
        with open(override_path, "r") as fh:
            override_contents = fh.read()
        self.assertEqual("manual\n", override_contents)

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.check_call')
    @patch.object(host, 'service')
    def test_pauses_a_running_sysv_service(self, service, check_call,
                                           systemd, service_running):
        """Pause calls service stop on a running sysv service."""
        service_name = 'foo-service'
        service.side_effect = [True]
        systemd.return_value = False
        service_running.return_value = True
        tempdir = mkdtemp(prefix="test_pauses_a_sysv_service")
        sysv_path = os.path.join(tempdir, service_name)
        # Just needs to exist
        with open(sysv_path, "w") as fh:
            fh.write("")
        self.addCleanup(rmtree, tempdir)
        self.assertTrue(host.service_pause(
            service_name, init_dir=tempdir, initd_dir=tempdir))

        service.assert_called_with('stop', service_name)
        check_call.assert_called_with(["update-rc.d", service_name, "disable"])

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.check_call')
    @patch.object(host, 'service')
    def test_pauses_a_stopped_sysv_service(self, service, check_call,
                                           systemd, service_running):
        """Pause does not call service stop on a stopped sysv service."""
        service_name = 'foo-service'
        service.side_effect = [True]
        systemd.return_value = False
        service_running.return_value = False
        tempdir = mkdtemp(prefix="test_pauses_a_sysv_service")
        sysv_path = os.path.join(tempdir, service_name)
        # Just needs to exist
        with open(sysv_path, "w") as fh:
            fh.write("")
        self.addCleanup(rmtree, tempdir)
        self.assertTrue(host.service_pause(
            service_name, init_dir=tempdir, initd_dir=tempdir))

        # Stop isn't called because service is already stopped
        self.assertRaises(
            AssertionError, service.assert_called_with, 'stop', service_name)
        check_call.assert_called_with(["update-rc.d", service_name, "disable"])

    @patch.object(host, 'init_is_systemd')
    @patch.object(host, 'service')
    def test_pause_with_unknown_service(self, service, systemd):
        service_name = 'foo-service'
        service.side_effect = [True]
        systemd.return_value = False
        tempdir = mkdtemp(prefix="test_pauses_with_unknown_service")
        self.addCleanup(rmtree, tempdir)
        exception = self.assertRaises(
            ValueError, host.service_pause,
            service_name, init_dir=tempdir, initd_dir=tempdir)
        self.assertIn(
            "Unable to detect {0}".format(service_name), str(exception))
        self.assertIn(tempdir, str(exception))

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.check_output')
    @patch.object(host, 'service')
    def test_resumes_a_running_upstart_service(self, service, check_output,
                                               systemd, service_running):
        """When the service is already running, service start isn't called."""
        service_name = 'foo-service'
        service.side_effect = [True]
        systemd.return_value = False
        service_running.return_value = True
        tempdir = mkdtemp(prefix="test_resumes_an_upstart_service")
        conf_path = os.path.join(tempdir, "{}.conf".format(service_name))
        with open(conf_path, "w") as fh:
            fh.write("")
        self.addCleanup(rmtree, tempdir)
        self.assertTrue(host.service_resume(service_name, init_dir=tempdir))

        # Start isn't called because service is already running
        self.assertFalse(service.called)
        override_path = os.path.join(
            tempdir, "{}.override".format(service_name))
        self.assertFalse(os.path.exists(override_path))

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.check_output')
    @patch.object(host, 'service')
    def test_resumes_a_stopped_upstart_service(self, service, check_output,
                                               systemd, service_running):
        """When the service is stopped, service start is called."""
        check_output.return_value = b'foo-service stop/waiting'
        service_name = 'foo-service'
        service.side_effect = [True]
        systemd.return_value = False
        service_running.return_value = False
        tempdir = mkdtemp(prefix="test_resumes_an_upstart_service")
        conf_path = os.path.join(tempdir, "{}.conf".format(service_name))
        with open(conf_path, "w") as fh:
            fh.write("")
        self.addCleanup(rmtree, tempdir)
        self.assertTrue(host.service_resume(service_name, init_dir=tempdir))

        service.assert_called_with('start', service_name)
        override_path = os.path.join(
            tempdir, "{}.override".format(service_name))
        self.assertFalse(os.path.exists(override_path))

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.check_call')
    @patch.object(host, 'service')
    def test_resumes_a_sysv_service(self, service, check_call, systemd,
                                    service_running):
        """When process is in a stop/waiting state, service start is called."""
        service_name = 'foo-service'
        service.side_effect = [True]
        systemd.return_value = False
        service_running.return_value = False
        tempdir = mkdtemp(prefix="test_resumes_a_sysv_service")
        sysv_path = os.path.join(tempdir, service_name)
        # Just needs to exist
        with open(sysv_path, "w") as fh:
            fh.write("")
        self.addCleanup(rmtree, tempdir)
        self.assertTrue(host.service_resume(
            service_name, init_dir=tempdir, initd_dir=tempdir))

        service.assert_called_with('start', service_name)
        check_call.assert_called_with(["update-rc.d", service_name, "enable"])

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.check_call')
    @patch.object(host, 'service')
    def test_resume_a_running_sysv_service(self, service, check_call,
                                           systemd, service_running):
        """When process is already running, service start isn't called."""
        service_name = 'foo-service'
        systemd.return_value = False
        service_running.return_value = True
        tempdir = mkdtemp(prefix="test_resumes_a_sysv_service")
        sysv_path = os.path.join(tempdir, service_name)
        # Just needs to exist
        with open(sysv_path, "w") as fh:
            fh.write("")
        self.addCleanup(rmtree, tempdir)
        self.assertTrue(host.service_resume(
            service_name, init_dir=tempdir, initd_dir=tempdir))

        # Start isn't called because service is already running
        self.assertFalse(service.called)
        check_call.assert_called_with(["update-rc.d", service_name, "enable"])

    @patch.object(host, 'service_running')
    @patch.object(host, 'init_is_systemd')
    @patch.object(host, 'service')
    def test_resume_with_unknown_service(self, service, systemd,
                                         service_running):
        service_name = 'foo-service'
        service.side_effect = [True]
        systemd.return_value = False
        service_running.return_value = False
        tempdir = mkdtemp(prefix="test_resumes_with_unknown_service")
        self.addCleanup(rmtree, tempdir)
        exception = self.assertRaises(
            ValueError, host.service_resume,
            service_name, init_dir=tempdir, initd_dir=tempdir)
        self.assertIn(
            "Unable to detect {0}".format(service_name), str(exception))
        self.assertIn(tempdir, str(exception))

    @patch.object(host, 'service')
    def test_reloads_a_service(self, service):
        service_name = 'foo-service'
        service.side_effect = [True]
        self.assertTrue(host.service_reload(service_name))

        service.assert_called_with('reload', service_name)

    @patch.object(host, 'service')
    def test_failed_reload_restarts_a_service(self, service):
        service_name = 'foo-service'
        service.side_effect = [False, True]
        self.assertTrue(
            host.service_reload(service_name, restart_on_failure=True))

        service.assert_has_calls([
            call('reload', service_name),
            call('restart', service_name)
        ])

    @patch.object(host, 'service')
    def test_failed_reload_without_restart(self, service):
        service_name = 'foo-service'
        service.side_effect = [False]
        self.assertFalse(host.service_reload(service_name))

        service.assert_called_with('reload', service_name)

    @patch.object(host, 'service')
    def test_start_a_service_fails(self, service):
        service_name = 'foo-service'
        service.side_effect = [False]
        self.assertFalse(host.service_start(service_name))

        service.assert_called_with('start', service_name)

    @patch.object(host, 'service')
    def test_stop_a_service_fails(self, service):
        service_name = 'foo-service'
        service.side_effect = [False]
        self.assertFalse(host.service_stop(service_name))

        service.assert_called_with('stop', service_name)

    @patch.object(host, 'service')
    def test_restart_a_service_fails(self, service):
        service_name = 'foo-service'
        service.side_effect = [False]
        self.assertFalse(host.service_restart(service_name))

        service.assert_called_with('restart', service_name)

    @patch.object(host, 'service')
    def test_reload_a_service_fails(self, service):
        service_name = 'foo-service'
        service.side_effect = [False]
        self.assertFalse(host.service_reload(service_name))

        service.assert_called_with('reload', service_name)

    @patch.object(host, 'service')
    def test_failed_reload_restarts_a_service_fails(self, service):
        service_name = 'foo-service'
        service.side_effect = [False, False]
        self.assertFalse(
            host.service_reload(service_name, restart_on_failure=True))

        service.assert_has_calls([
            call('reload', service_name),
            call('restart', service_name)
        ])

    @patch.object(host, 'os')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.check_output')
    def test_service_running_on_stopped_service(self, check_output, systemd,
                                                os):
        systemd.return_value = False
        os.path.exists.return_value = True
        check_output.return_value = b'foo stop/waiting'
        self.assertFalse(host.service_running('foo'))

    @patch.object(host, 'os')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.check_output')
    def test_service_running_on_running_service(self, check_output, systemd,
                                                os):
        systemd.return_value = False
        os.path.exists.return_value = True
        check_output.return_value = b'foo start/running, process 23871'
        self.assertTrue(host.service_running('foo'))

    @patch.object(host, 'os')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.check_output')
    def test_service_running_on_unknown_service(self, check_output, systemd,
                                                os):
        systemd.return_value = False
        os.path.exists.return_value = True
        exc = subprocess.CalledProcessError(1, ['status'])
        check_output.side_effect = exc
        self.assertFalse(host.service_running('foo'))

    @patch.object(host, 'os')
    @patch.object(host, 'service')
    @patch.object(host, 'init_is_systemd')
    def test_service_systemv_running(self, systemd, service, os):
        systemd.return_value = False
        service.return_value = True
        os.path.exists.side_effect = [False, True]
        self.assertTrue(host.service_running('rabbitmq-server'))
        service.assert_called_with('status', 'rabbitmq-server')

    @patch.object(host, 'os')
    @patch.object(host, 'service')
    @patch.object(host, 'init_is_systemd')
    def test_service_systemv_not_running(self, systemd, service,
                                         os):
        systemd.return_value = False
        service.return_value = False
        os.path.exists.side_effect = [False, True]
        self.assertFalse(host.service_running('keystone'))
        service.assert_called_with('status', 'keystone')

    @patch('subprocess.call')
    @patch.object(host, 'init_is_systemd')
    def test_service_start_with_params(self, systemd, call):
        systemd.return_value = False
        call.return_value = 0
        self.assertTrue(host.service_start('ceph-osd', id=4))
        call.assert_called_with(['service', 'ceph-osd', 'start', 'id=4'])

    @patch('subprocess.call')
    @patch.object(host, 'init_is_systemd')
    def test_service_stop_with_params(self, systemd, call):
        systemd.return_value = False
        call.return_value = 0
        self.assertTrue(host.service_stop('ceph-osd', id=4))
        call.assert_called_with(['service', 'ceph-osd', 'stop', 'id=4'])

    @patch('subprocess.call')
    @patch.object(host, 'init_is_systemd')
    def test_service_start_systemd_with_params(self, systemd, call):
        systemd.return_value = True
        call.return_value = 0
        self.assertTrue(host.service_start('ceph-osd', id=4))
        call.assert_called_with(['systemctl', 'start', 'ceph-osd'])

    @patch('grp.getgrnam')
    @patch('pwd.getpwnam')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_adds_a_user_if_it_doesnt_exist(self, log, check_call,
                                            getpwnam, getgrnam):
        username = 'johndoe'
        password = 'eodnhoj'
        shell = '/bin/bash'
        existing_user_pwnam = KeyError('user not found')
        new_user_pwnam = 'some user pwnam'

        getpwnam.side_effect = [existing_user_pwnam, new_user_pwnam]

        result = host.adduser(username, password=password)

        self.assertEqual(result, new_user_pwnam)
        check_call.assert_called_with([
            'useradd',
            '--create-home',
            '--shell', shell,
            '--password', password,
            '-g', username,
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

        result = host.adduser(username, password=password)

        self.assertEqual(result, existing_user_pwnam)
        self.assertFalse(check_call.called)
        getpwnam.assert_called_with(username)

    @patch('grp.getgrnam')
    @patch('pwd.getpwnam')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_adds_a_user_with_different_shell(self, log, check_call, getpwnam,
                                              getgrnam):
        username = 'johndoe'
        password = 'eodnhoj'
        shell = '/bin/zsh'
        existing_user_pwnam = KeyError('user not found')
        new_user_pwnam = 'some user pwnam'

        getpwnam.side_effect = [existing_user_pwnam, new_user_pwnam]
        getgrnam.side_effect = KeyError('group not found')

        result = host.adduser(username, password=password, shell=shell)

        self.assertEqual(result, new_user_pwnam)
        check_call.assert_called_with([
            'useradd',
            '--create-home',
            '--shell', shell,
            '--password', password,
            username
        ])
        getpwnam.assert_called_with(username)

    @patch('grp.getgrnam')
    @patch('pwd.getpwnam')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_adduser_with_groups(self, log, check_call, getpwnam, getgrnam):
        username = 'johndoe'
        password = 'eodnhoj'
        shell = '/bin/bash'
        existing_user_pwnam = KeyError('user not found')
        new_user_pwnam = 'some user pwnam'

        getpwnam.side_effect = [existing_user_pwnam, new_user_pwnam]

        result = host.adduser(username, password=password,
                              primary_group='foo', secondary_groups=[
                                  'bar', 'qux',
                              ])

        self.assertEqual(result, new_user_pwnam)
        check_call.assert_called_with([
            'useradd',
            '--create-home',
            '--shell', shell,
            '--password', password,
            '-g', 'foo',
            '-G', 'bar,qux',
            username
        ])
        getpwnam.assert_called_with(username)
        assert not getgrnam.called

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

    @patch('pwd.getpwnam')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_adds_a_systemuser_with_home_dir(self, log, check_call, getpwnam):
        username = 'johndoe'
        existing_user_pwnam = KeyError('user not found')
        new_user_pwnam = 'some user pwnam'

        getpwnam.side_effect = [existing_user_pwnam, new_user_pwnam]

        result = host.adduser(username, system_user=True,
                              home_dir='/var/lib/johndoe')

        self.assertEqual(result, new_user_pwnam)
        check_call.assert_called_with([
            'useradd',
            '--home',
            '/var/lib/johndoe',
            '--system',
            username
        ])
        getpwnam.assert_called_with(username)

    @patch('pwd.getpwnam')
    @patch('pwd.getpwuid')
    @patch('grp.getgrnam')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_add_user_uid(self, log, check_call, getgrnam, getpwuid, getpwnam):
        user_name = 'james'
        user_id = 1111
        uid_key_error = KeyError('user not found')
        getpwuid.side_effect = uid_key_error
        host.adduser(user_name, uid=user_id)

        check_call.assert_called_with([
            'useradd',
            '--uid',
            str(user_id),
            '--system',
            '-g',
            user_name,
            user_name
        ])
        getpwnam.assert_called_with(user_name)
        getpwuid.assert_called_with(user_id)

    @patch('grp.getgrnam')
    @patch('grp.getgrgid')
    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_add_group_gid(self, log, check_call, getgrgid, getgrnam):
        group_name = 'darkhorse'
        group_id = 1005
        existing_group_gid = KeyError('group not found')
        new_group_gid = 1006
        getgrgid.side_effect = [existing_group_gid, new_group_gid]

        host.add_group(group_name, gid=group_id)
        check_call.assert_called_with([
            'addgroup',
            '--gid',
            str(group_id),
            '--group',
            group_name
        ])
        getgrgid.assert_called_with(group_id)
        getgrnam.assert_called_with(group_name)

    @patch('pwd.getpwnam')
    def test_user_exists_true(self, getpwnam):
        getpwnam.side_effect = 'pw info'
        self.assertTrue(host.user_exists('bob'))

    @patch('pwd.getpwnam')
    def test_user_exists_false(self, getpwnam):
        getpwnam.side_effect = KeyError('user not found')
        self.assertFalse(host.user_exists('bob'))

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

    @patch.object(osplatform, 'get_platform')
    @patch('grp.getgrnam')
    @patch('subprocess.check_call')
    def test_add_a_group_if_it_doesnt_exist_ubuntu(self, check_call,
                                                   getgrnam, platform):
        platform.return_value = 'ubuntu'
        imp.reload(host)

        group_name = 'testgroup'
        existing_group_grnam = KeyError('group not found')
        new_group_grnam = 'some group grnam'

        getgrnam.side_effect = [existing_group_grnam, new_group_grnam]
        with patch("charmhelpers.core.host.log"):
            result = host.add_group(group_name)

        self.assertEqual(result, new_group_grnam)
        check_call.assert_called_with(['addgroup', '--group', group_name])
        getgrnam.assert_called_with(group_name)

    @patch.object(osplatform, 'get_platform')
    @patch('grp.getgrnam')
    @patch('subprocess.check_call')
    def test_add_a_group_if_it_doesnt_exist_centos(self, check_call,
                                                   getgrnam, platform):
        platform.return_value = 'centos'
        imp.reload(host)

        group_name = 'testgroup'
        existing_group_grnam = KeyError('group not found')
        new_group_grnam = 'some group grnam'

        getgrnam.side_effect = [existing_group_grnam, new_group_grnam]

        with patch("charmhelpers.core.host.log"):
            result = host.add_group(group_name)

        self.assertEqual(result, new_group_grnam)
        check_call.assert_called_with(['groupadd', group_name])
        getgrnam.assert_called_with(group_name)

    @patch.object(osplatform, 'get_platform')
    @patch('grp.getgrnam')
    @patch('subprocess.check_call')
    def test_doesnt_add_group_if_it_already_exists_ubuntu(self, check_call,
                                                          getgrnam, platform):
        platform.return_value = 'ubuntu'
        imp.reload(host)

        group_name = 'testgroup'
        existing_group_grnam = 'some group grnam'

        getgrnam.return_value = existing_group_grnam

        with patch("charmhelpers.core.host.log"):
            result = host.add_group(group_name)

        self.assertEqual(result, existing_group_grnam)
        self.assertFalse(check_call.called)
        getgrnam.assert_called_with(group_name)

    @patch.object(osplatform, 'get_platform')
    @patch('grp.getgrnam')
    @patch('subprocess.check_call')
    def test_doesnt_add_group_if_it_already_exists_centos(self, check_call,
                                                          getgrnam, platform):
        platform.return_value = 'centos'
        imp.reload(host)

        group_name = 'testgroup'
        existing_group_grnam = 'some group grnam'

        getgrnam.return_value = existing_group_grnam

        with patch("charmhelpers.core.host.log"):
            result = host.add_group(group_name)

        self.assertEqual(result, existing_group_grnam)
        self.assertFalse(check_call.called)
        getgrnam.assert_called_with(group_name)

    @patch.object(osplatform, 'get_platform')
    @patch('grp.getgrnam')
    @patch('subprocess.check_call')
    def test_add_a_system_group_ubuntu(self, check_call, getgrnam, platform):
        platform.return_value = 'ubuntu'
        imp.reload(host)

        group_name = 'testgroup'
        existing_group_grnam = KeyError('group not found')
        new_group_grnam = 'some group grnam'

        getgrnam.side_effect = [existing_group_grnam, new_group_grnam]

        with patch("charmhelpers.core.host.log"):
            result = host.add_group(group_name, system_group=True)

        self.assertEqual(result, new_group_grnam)
        check_call.assert_called_with([
            'addgroup',
            '--system',
            group_name
        ])
        getgrnam.assert_called_with(group_name)

    @patch.object(osplatform, 'get_platform')
    @patch('grp.getgrnam')
    @patch('subprocess.check_call')
    def test_add_a_system_group_centos(self, check_call, getgrnam, platform):
        platform.return_value = 'centos'
        imp.reload(host)

        group_name = 'testgroup'
        existing_group_grnam = KeyError('group not found')
        new_group_grnam = 'some group grnam'

        getgrnam.side_effect = [existing_group_grnam, new_group_grnam]

        with patch("charmhelpers.core.host.log"):
            result = host.add_group(group_name, system_group=True)

        self.assertEqual(result, new_group_grnam)
        check_call.assert_called_with([
            'groupadd',
            '-r',
            group_name
        ])
        getgrnam.assert_called_with(group_name)

    @patch('subprocess.check_call')
    def test_chage_no_chroot(self, check_call):
        host.chage('usera', expiredate='2019-09-28', maxdays='11')
        check_call.assert_called_with([
            'chage',
            '--expiredate', '2019-09-28',
            '--maxdays', '11',
            'usera'
        ])

    @patch('subprocess.check_call')
    def test_chage_chroot(self, check_call):
        host.chage('usera', expiredate='2019-09-28', maxdays='11',
                   root='mychroot')
        check_call.assert_called_with([
            'chage',
            '--root', 'mychroot',
            '--expiredate', '2019-09-28',
            '--maxdays', '11',
            'usera'
        ])

    @patch('subprocess.check_call')
    def test_remove_password_expiry(self, check_call):
        host.remove_password_expiry('usera')
        check_call.assert_called_with([
            'chage',
            '--expiredate', '-1',
            '--inactive', '-1',
            '--mindays', '0',
            '--maxdays', '-1',
            'usera'
        ])

    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_rsyncs_a_path(self, log, check_output):
        from_path = '/from/this/path/foo'
        to_path = '/to/this/path/bar'
        check_output.return_value = b' some output '  # Spaces will be stripped

        result = host.rsync(from_path, to_path)

        self.assertEqual(result, 'some output')
        check_output.assert_called_with(['/usr/bin/rsync', '-r', '--delete',
                                         '--executability',
                                         '/from/this/path/foo',
                                         '/to/this/path/bar'], stderr=subprocess.STDOUT)

    @patch('subprocess.check_call')
    @patch.object(host, 'log')
    def test_creates_a_symlink(self, log, check_call):
        source = '/from/this/path/foo'
        destination = '/to/this/path/bar'

        host.symlink(source, destination)

        check_call.assert_called_with(['ln', '-sf',
                                       '/from/this/path/foo',
                                       '/to/this/path/bar'])

    @patch('pwd.getpwnam')
    @patch('grp.getgrnam')
    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_creates_a_directory_if_it_doesnt_exist(self, os_, log,
                                                    getgrnam, getpwnam):
        uid = 123
        gid = 234
        owner = 'some-user'
        group = 'some-group'
        path = '/some/other/path/from/link'
        realpath = '/some/path'
        path_exists = False
        perms = 0o644

        getpwnam.return_value.pw_uid = uid
        getgrnam.return_value.gr_gid = gid
        os_.path.abspath.return_value = realpath
        os_.path.exists.return_value = path_exists

        host.mkdir(path, owner=owner, group=group, perms=perms)

        getpwnam.assert_called_with('some-user')
        getgrnam.assert_called_with('some-group')
        os_.path.abspath.assert_called_with(path)
        os_.path.exists.assert_called_with(realpath)
        os_.makedirs.assert_called_with(realpath, perms)
        os_.chown.assert_called_with(realpath, uid, gid)

    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_creates_a_directory_with_defaults(self, os_, log):
        uid = 0
        gid = 0
        path = '/some/other/path/from/link'
        realpath = '/some/path'
        path_exists = False
        perms = 0o555

        os_.path.abspath.return_value = realpath
        os_.path.exists.return_value = path_exists

        host.mkdir(path)

        os_.path.abspath.assert_called_with(path)
        os_.path.exists.assert_called_with(realpath)
        os_.makedirs.assert_called_with(realpath, perms)
        os_.chown.assert_called_with(realpath, uid, gid)

    @patch('pwd.getpwnam')
    @patch('grp.getgrnam')
    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_removes_file_with_same_path_before_mkdir(self, os_, log,
                                                      getgrnam, getpwnam):
        uid = 123
        gid = 234
        owner = 'some-user'
        group = 'some-group'
        path = '/some/other/path/from/link'
        realpath = '/some/path'
        path_exists = True
        force = True
        is_dir = False
        perms = 0o644

        getpwnam.return_value.pw_uid = uid
        getgrnam.return_value.gr_gid = gid
        os_.path.abspath.return_value = realpath
        os_.path.exists.return_value = path_exists
        os_.path.isdir.return_value = is_dir

        host.mkdir(path, owner=owner, group=group, perms=perms, force=force)

        getpwnam.assert_called_with('some-user')
        getgrnam.assert_called_with('some-group')
        os_.path.abspath.assert_called_with(path)
        os_.path.exists.assert_called_with(realpath)
        os_.unlink.assert_called_with(realpath)
        os_.makedirs.assert_called_with(realpath, perms)
        os_.chown.assert_called_with(realpath, uid, gid)

    @patch('pwd.getpwnam')
    @patch('grp.getgrnam')
    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_writes_content_to_a_file(self, os_, log, getgrnam, getpwnam):
        # Curly brackets here demonstrate that we are *not* rendering
        # these strings with Python's string formatting. This is a
        # change from the original behavior per Bug #1195634.
        uid = 123
        gid = 234
        owner = 'some-user-{foo}'
        group = 'some-group-{bar}'
        path = '/some/path/{baz}'
        contents = b'what is {juju}'
        perms = 0o644
        fileno = 'some-fileno'

        getpwnam.return_value.pw_uid = uid
        getgrnam.return_value.gr_gid = gid

        with patch_open() as (mock_open, mock_file):
            mock_file.fileno.return_value = fileno

            host.write_file(path, contents, owner=owner, group=group,
                            perms=perms)

            getpwnam.assert_called_with('some-user-{foo}')
            getgrnam.assert_called_with('some-group-{bar}')
            mock_open.assert_called_with('/some/path/{baz}', 'wb')
            os_.fchown.assert_called_with(fileno, uid, gid)
            os_.fchmod.assert_called_with(fileno, perms)
            mock_file.write.assert_called_with(b'what is {juju}')

    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_writes_content_with_default(self, os_, log):
        uid = 0
        gid = 0
        path = '/some/path/{baz}'
        fmtstr = b'what is {juju}'
        perms = 0o444
        fileno = 'some-fileno'

        with patch_open() as (mock_open, mock_file):
            mock_file.fileno.return_value = fileno

            host.write_file(path, fmtstr)

            mock_open.assert_called_with('/some/path/{baz}', 'wb')
            os_.fchown.assert_called_with(fileno, uid, gid)
            os_.fchmod.assert_called_with(fileno, perms)
            mock_file.write.assert_called_with(b'what is {juju}')

    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_does_not_write_duplicate_content(self, os_, log):
        uid = 0
        gid = 0
        path = '/some/path/{baz}'
        fmtstr = b'what is {juju}'
        perms = 0o444
        fileno = 'some-fileno'

        os_.stat.return_value.st_uid = 1
        os_.stat.return_value.st_gid = 1
        os_.stat.return_value.st_mode = 0o777

        with patch_open() as (mock_open, mock_file):
            mock_file.fileno.return_value = fileno
            mock_file.read.return_value = fmtstr

            host.write_file(path, fmtstr)

            self.assertEqual(mock_open.call_count, 1)  # Called to read
            os_.chown.assert_has_calls([
                call(path, uid, -1),
                call(path, -1, gid),
            ])
            os_.chmod.assert_called_with(path, perms)

    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_only_changes_incorrect_ownership(self, os_, log):
        uid = 0
        gid = 0
        path = '/some/path/{baz}'
        fmtstr = b'what is {juju}'
        perms = 0o444
        fileno = 'some-fileno'

        os_.stat.return_value.st_uid = uid
        os_.stat.return_value.st_gid = gid
        os_.stat.return_value.st_mode = perms

        with patch_open() as (mock_open, mock_file):
            mock_file.fileno.return_value = fileno
            mock_file.read.return_value = fmtstr

            host.write_file(path, fmtstr)

            self.assertEqual(mock_open.call_count, 1)  # Called to read
            self.assertEqual(os_.chown.call_count, 0)

    @patch.object(host, 'log')
    @patch.object(host, 'os')
    def test_writes_binary_contents(self, os_, log):
        path = '/some/path/{baz}'
        fmtstr = six.u('what is {juju}\N{TRADE MARK SIGN}').encode('UTF-8')
        fileno = 'some-fileno'

        with patch_open() as (mock_open, mock_file):
            mock_file.fileno.return_value = fileno

            host.write_file(path, fmtstr)

            mock_open.assert_called_with('/some/path/{baz}', 'wb')
            mock_file.write.assert_called_with(fmtstr)

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

    @patch.object(host, 'Fstab')
    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_mounts_and_persist_a_device(self, log, check_output, fstab):
        """Check if a mount works with the persist flag set to True
        """
        device = '/dev/guido'
        mountpoint = '/mnt/guido'
        options = 'foo,bar'

        result = host.mount(device, mountpoint, options, persist=True)

        self.assertTrue(result)
        check_output.assert_called_with(['mount', '-o', 'foo,bar',
                                         '/dev/guido', '/mnt/guido'])

        fstab.add.assert_called_with('/dev/guido', '/mnt/guido', 'ext3',
                                     options='foo,bar')

        result = host.mount(device, mountpoint, options, persist=True,
                            filesystem="xfs")

        self.assertTrue(result)
        fstab.add.assert_called_with('/dev/guido', '/mnt/guido', 'xfs',
                                     options='foo,bar')

    @patch.object(host, 'Fstab')
    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_umounts_a_device(self, log, check_output, fstab):
        mountpoint = '/mnt/guido'

        result = host.umount(mountpoint, persist=True)

        self.assertTrue(result)
        check_output.assert_called_with(['umount', mountpoint])
        fstab.remove_by_mountpoint_called_with(mountpoint)

    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_umounts_and_persist_device(self, log, check_output):
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

    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_fstab_mount(self, log, check_output):
        self.assertTrue(host.fstab_mount('/mnt/mymntpnt'))
        check_output.assert_called_with(['mount', '/mnt/mymntpnt'])

    @patch('subprocess.check_output')
    @patch.object(host, 'log')
    def test_fstab_mount_fail(self, log, check_output):
        error = subprocess.CalledProcessError(123, 'mount it', 'Oops...')
        check_output.side_effect = error
        self.assertFalse(host.fstab_mount('/mnt/mymntpnt'))
        check_output.assert_called_with(['mount', '/mnt/mymntpnt'])

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

    @patch('hashlib.sha1')
    @patch('os.path.exists')
    def test_file_hash_sha1(self, exists, sha1):
        filename = '/etc/exists.conf'
        exists.side_effect = [True]
        m = sha1()
        m.hexdigest.return_value = self._hash_files[filename]
        with patch_open() as (mock_open, mock_file):
            mock_file.read.return_value = self._hash_files[filename]
            result = host.file_hash(filename, hash_type='sha1')
            self.assertEqual(result, self._hash_files[filename])

    @patch.object(host, 'file_hash')
    def test_check_hash(self, file_hash):
        file_hash.return_value = 'good-hash'
        self.assertRaises(host.ChecksumError, host.check_hash,
                          'file', 'bad-hash')
        host.check_hash('file', 'good-hash', 'sha256')
        self.assertEqual(file_hash.call_args_list, [
            call('file', 'md5'),
            call('file', 'sha256'),
        ])

    @patch.object(host, 'service')
    @patch('os.path.exists')
    @patch('glob.iglob')
    def test_restart_no_changes(self, iglob, exists, service):
        file_name = '/etc/missing.conf'
        restart_map = {
            file_name: ['test-service']
        }
        iglob.return_value = []

        @host.restart_on_change(restart_map)
        def make_no_changes():
            pass

        make_no_changes()

        assert not service.called
        assert not exists.called

    @patch.object(host, 'service')
    @patch('os.path.exists')
    @patch('glob.iglob')
    def test_restart_on_change(self, iglob, exists, service):
        file_name = '/etc/missing.conf'
        restart_map = {
            file_name: ['test-service']
        }
        iglob.side_effect = [[], [file_name]]
        exists.return_value = True

        @host.restart_on_change(restart_map)
        def make_some_changes(mock_file):
            mock_file.read.return_value = b"newstuff"

        with patch_open() as (mock_open, mock_file):
            make_some_changes(mock_file)

        for service_name in restart_map[file_name]:
            service.assert_called_with('restart', service_name)

        exists.assert_has_calls([
            call(file_name),
        ])

    @patch.object(host, 'service')
    @patch('os.path.exists')
    @patch('glob.iglob')
    def test_restart_on_change_context_manager(self, iglob, exists, service):
        file_name = '/etc/missing.conf'
        restart_map = {
            file_name: ['test-service']
        }
        iglob.side_effect = [[], [file_name]]
        exists.return_value = True

        with patch_open() as (mock_open, mock_file):
            with host.restart_on_change(restart_map):
                mock_file.read.return_value = b"newstuff"

        for service_name in restart_map[file_name]:
            service.assert_called_with('restart', service_name)

        exists.assert_has_calls([
            call(file_name),
        ])

    @patch.object(host, 'service')
    @patch('os.path.exists')
    @patch('glob.iglob')
    def test_multiservice_restart_on_change(self, iglob, exists, service):
        file_name_one = '/etc/missing.conf'
        file_name_two = '/etc/exists.conf'
        restart_map = {
            file_name_one: ['test-service'],
            file_name_two: ['test-service', 'test-service2']
        }
        iglob.side_effect = [[], [file_name_two],
                             [file_name_one], [file_name_two]]
        exists.return_value = True

        @host.restart_on_change(restart_map)
        def make_some_changes():
            pass

        with patch_open() as (mock_open, mock_file):
            mock_file.read.side_effect = [b'exists', b'missing', b'exists2']
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
    @patch('glob.iglob')
    def test_multiservice_restart_on_change_in_order(self, iglob, exists,
                                                     service):
        file_name_one = '/etc/cinder/cinder.conf'
        file_name_two = '/etc/haproxy/haproxy.conf'
        restart_map = OrderedDict([
            (file_name_one, ['some-api']),
            (file_name_two, ['haproxy'])
        ])
        iglob.side_effect = [[], [file_name_two],
                             [file_name_one], [file_name_two]]
        exists.return_value = True

        @host.restart_on_change(restart_map)
        def make_some_changes():
            pass

        with patch_open() as (mock_open, mock_file):
            mock_file.read.side_effect = [b'exists', b'missing', b'exists2']
            make_some_changes()

        # Restarts should happen in the order they are described in the
        # restart map.
        expected = [
            call('restart', 'some-api'),
            call('restart', 'haproxy')
        ]
        self.assertEquals(expected, service.call_args_list)

    @patch.object(host, 'service')
    @patch('os.path.exists')
    @patch('glob.iglob')
    def test_glob_no_restart(self, iglob, exists, service):
        glob_path = '/etc/service/*.conf'
        file_name_one = '/etc/service/exists.conf'
        file_name_two = '/etc/service/exists2.conf'
        restart_map = {
            glob_path: ['service']
        }
        iglob.side_effect = [[file_name_one, file_name_two],
                             [file_name_one, file_name_two]]
        exists.return_value = True

        @host.restart_on_change(restart_map)
        def make_some_changes():
            pass

        with patch_open() as (mock_open, mock_file):
            mock_file.read.side_effect = [b'content', b'content2',
                                          b'content', b'content2']
            make_some_changes()

        self.assertEquals([], service.call_args_list)

    @patch.object(host, 'service')
    @patch('os.path.exists')
    @patch('glob.iglob')
    def test_glob_restart_on_change(self, iglob, exists, service):
        glob_path = '/etc/service/*.conf'
        file_name_one = '/etc/service/exists.conf'
        file_name_two = '/etc/service/exists2.conf'
        restart_map = {
            glob_path: ['service']
        }
        iglob.side_effect = [[file_name_one, file_name_two],
                             [file_name_one, file_name_two]]
        exists.return_value = True

        @host.restart_on_change(restart_map)
        def make_some_changes():
            pass

        with patch_open() as (mock_open, mock_file):
            mock_file.read.side_effect = [b'content', b'content2',
                                          b'changed', b'content2']
            make_some_changes()

        self.assertEquals([call('restart', 'service')], service.call_args_list)

    @patch.object(host, 'service')
    @patch('os.path.exists')
    @patch('glob.iglob')
    def test_glob_restart_on_create(self, iglob, exists, service):
        glob_path = '/etc/service/*.conf'
        file_name_one = '/etc/service/exists.conf'
        file_name_two = '/etc/service/missing.conf'
        restart_map = {
            glob_path: ['service']
        }
        iglob.side_effect = [[file_name_one],
                             [file_name_one, file_name_two]]
        exists.return_value = True

        @host.restart_on_change(restart_map)
        def make_some_changes():
            pass

        with patch_open() as (mock_open, mock_file):
            mock_file.read.side_effect = [b'exists',
                                          b'exists', b'created']
            make_some_changes()

        self.assertEquals([call('restart', 'service')], service.call_args_list)

    @patch.object(host, 'service')
    @patch('os.path.exists')
    @patch('glob.iglob')
    def test_glob_restart_on_delete(self, iglob, exists, service):
        glob_path = '/etc/service/*.conf'
        file_name_one = '/etc/service/exists.conf'
        file_name_two = '/etc/service/exists2.conf'
        restart_map = {
            glob_path: ['service']
        }
        iglob.side_effect = [[file_name_one, file_name_two],
                             [file_name_two]]
        exists.return_value = True

        @host.restart_on_change(restart_map)
        def make_some_changes():
            pass

        with patch_open() as (mock_open, mock_file):
            mock_file.read.side_effect = [b'exists', b'exists2',
                                          b'exists2']
            make_some_changes()

        self.assertEquals([call('restart', 'service')], service.call_args_list)

    @patch.object(host, 'service_reload')
    @patch.object(host, 'service')
    @patch('os.path.exists')
    @patch('glob.iglob')
    def test_restart_on_change_restart_functs(self, iglob, exists, service,
                                              service_reload):
        file_name_one = '/etc/cinder/cinder.conf'
        file_name_two = '/etc/haproxy/haproxy.conf'
        restart_map = OrderedDict([
            (file_name_one, ['some-api']),
            (file_name_two, ['haproxy'])
        ])
        iglob.side_effect = [[], [file_name_two],
                             [file_name_one], [file_name_two]]
        exists.return_value = True

        restart_funcs = {
            'some-api': service_reload,
        }

        @host.restart_on_change(restart_map, restart_functions=restart_funcs)
        def make_some_changes():
            pass

        with patch_open() as (mock_open, mock_file):
            mock_file.read.side_effect = [b'exists', b'missing', b'exists2']
            make_some_changes()

        self.assertEquals([call('restart', 'haproxy')], service.call_args_list)
        self.assertEquals([call('some-api')], service_reload.call_args_list)

    @patch.object(osplatform, 'get_platform')
    def test_lsb_release_ubuntu(self, platform):
        platform.return_value = 'ubuntu'
        imp.reload(host)

        result = {
            "DISTRIB_ID": "Ubuntu",
            "DISTRIB_RELEASE": "13.10",
            "DISTRIB_CODENAME": "saucy",
            "DISTRIB_DESCRIPTION": "\"Ubuntu Saucy Salamander "
                                   "(development branch)\""
        }
        with mocked_open('/etc/lsb-release', LSB_RELEASE):
            lsb_release = host.lsb_release()
            for key in result:
                self.assertEqual(result[key], lsb_release[key])

    @patch.object(osplatform, 'get_platform')
    def test_lsb_release_centos(self, platform):
        platform.return_value = 'centos'
        imp.reload(host)

        result = {
            'NAME': '"CentOS Linux"',
            'ANSI_COLOR': '"0;31"',
            'ID_LIKE': '"rhel fedora"',
            'VERSION_ID': '"7"',
            'BUG_REPORT_URL': '"https://bugs.centos.org/"',
            'CENTOS_MANTISBT_PROJECT': '"CentOS-7"',
            'PRETTY_NAME': '"CentOS Linux 7 (Core)"',
            'VERSION': '"7 (Core)"',
            'REDHAT_SUPPORT_PRODUCT_VERSION': '"7"',
            'CENTOS_MANTISBT_PROJECT_VERSION': '"7"',
            'REDHAT_SUPPORT_PRODUCT': '"centos"',
            'HOME_URL': '"https://www.centos.org/"',
            'CPE_NAME': '"cpe:/o:centos:centos:7"',
            'ID': '"centos"'
        }
        with mocked_open('/etc/os-release', OS_RELEASE):
            lsb_release = host.lsb_release()
            for key in result:
                self.assertEqual(result[key], lsb_release[key])

    def test_pwgen(self):
        pw = host.pwgen()
        self.assert_(len(pw) >= 35, 'Password is too short')

        pw = host.pwgen(10)
        self.assertEqual(len(pw), 10, 'Password incorrect length')

        pw2 = host.pwgen(10)
        self.assertNotEqual(pw, pw2, 'Duplicated password')

    @patch.object(host, 'glob')
    @patch('os.path.realpath')
    @patch('os.path.isdir')
    def test_is_phy_iface(self, mock_isdir, mock_realpath, mock_glob):
        mock_isdir.return_value = True
        mock_glob.glob.return_value = ['/sys/class/net/eth0',
                                       '/sys/class/net/veth0']

        def fake_realpath(soft):
            if soft.endswith('/eth0'):
                hard = ('/sys/devices/pci0000:00/0000:00:1c.4'
                        '/0000:02:00.1/net/eth0')
            else:
                hard = '/sys/devices/virtual/net/veth0'

            return hard

        mock_realpath.side_effect = fake_realpath
        self.assertTrue(host.is_phy_iface('eth0'))
        self.assertFalse(host.is_phy_iface('veth0'))

    @patch('os.path.exists')
    @patch('os.path.realpath')
    @patch('os.path.isdir')
    def test_get_bond_master(self, mock_isdir, mock_realpath, mock_exists):
        mock_isdir.return_value = True

        def fake_realpath(soft):
            if soft.endswith('/eth0'):
                return ('/sys/devices/pci0000:00/0000:00:1c.4'
                        '/0000:02:00.1/net/eth0')
            elif soft.endswith('/br0'):
                return '/sys/devices/virtual/net/br0'
            elif soft.endswith('/master'):
                return '/sys/devices/virtual/net/bond0'

            return None

        def fake_exists(path):
            return True

        mock_exists.side_effect = fake_exists
        mock_realpath.side_effect = fake_realpath
        self.assertEqual(host.get_bond_master('eth0'), 'bond0')
        self.assertIsNone(host.get_bond_master('br0'))

    @patch('subprocess.check_output')
    def test_list_nics(self, check_output):
        check_output.return_value = IP_LINES
        nics = host.list_nics()
        self.assertEqual(nics, ['eth0', 'eth1', 'eth0.10', 'eth100'])
        nics = host.list_nics('eth')
        self.assertEqual(nics, ['eth0', 'eth1', 'eth0.10', 'eth100'])
        nics = host.list_nics(['eth'])
        self.assertEqual(nics, ['eth0', 'eth1', 'eth0.10', 'eth100'])

    @patch('subprocess.check_output')
    def test_list_nics_with_bonds(self, check_output):
        check_output.return_value = IP_LINE_BONDS
        nics = host.list_nics('bond')
        self.assertEqual(nics, ['bond0.10', ])

    @patch('subprocess.check_output')
    def test_get_nic_mtu_with_bonds(self, check_output):
        check_output.return_value = IP_LINE_BONDS
        nic = "bond0.10"
        mtu = host.get_nic_mtu(nic)
        self.assertEqual(mtu, '1500')

    @patch('subprocess.check_call')
    def test_set_nic_mtu(self, mock_call):
        mock_call.return_value = 0
        nic = 'eth7'
        mtu = '1546'
        host.set_nic_mtu(nic, mtu)
        mock_call.assert_called_with(['ip', 'link', 'set', nic, 'mtu', mtu])

    @patch('subprocess.check_output')
    def test_get_nic_mtu(self, check_output):
        check_output.return_value = IP_LINE_ETH0
        nic = "eth0"
        mtu = host.get_nic_mtu(nic)
        self.assertEqual(mtu, '1500')

    @patch('subprocess.check_output')
    def test_get_nic_mtu_vlan(self, check_output):
        check_output.return_value = IP_LINE_ETH0_VLAN
        nic = "eth0.10"
        mtu = host.get_nic_mtu(nic)
        self.assertEqual(mtu, '1500')

    @patch('subprocess.check_output')
    def test_get_nic_hwaddr(self, check_output):
        check_output.return_value = IP_LINE_HWADDR
        nic = "eth0"
        hwaddr = host.get_nic_hwaddr(nic)
        self.assertEqual(hwaddr, 'e4:11:5b:ab:a7:3c')

    @patch('charmhelpers.core.host_factory.ubuntu.lsb_release')
    def test_get_distrib_codename(self, lsb_release):
        lsb_release.return_value = {'DISTRIB_CODENAME': 'bionic'}
        self.assertEqual(host.get_distrib_codename(), 'bionic')

    @patch('charmhelpers.fetch.get_installed_version')
    @patch.object(osplatform, 'get_platform')
    @patch.object(ubuntu_apt_pkg, 'Cache')
    def test_cmp_pkgrevno_revnos_ubuntu(self, pkg_cache, platform,
                                        get_installed_version):
        platform.return_value = 'ubuntu'
        imp.reload(host)
        current_ver = '2.4'

        class MockPackage:
            class MockPackageRevno:
                def __init__(self, ver_str):
                    self.ver_str = ver_str

            def __init__(self, current_ver):
                self.current_ver = self.MockPackageRevno(current_ver)

        pkg_dict = {
            'python': MockPackage(current_ver)
        }
        pkg_cache.return_value = pkg_dict
        get_installed_version.return_value = MockPackage.MockPackageRevno(
            current_ver)
        self.assertEqual(host.cmp_pkgrevno('python', '2.3'), 1)
        self.assertEqual(host.cmp_pkgrevno('python', '2.4'), 0)
        self.assertEqual(host.cmp_pkgrevno('python', '2.5'), -1)
        self.assertEqual(
            host.cmp_pkgrevno('python', '2.3', pkgcache=pkg_dict),
            1
        )
        self.assertEqual(
            host.cmp_pkgrevno('python', '2.4', pkgcache=pkg_dict),
            0
        )
        self.assertEqual(
            host.cmp_pkgrevno('python', '2.5', pkgcache=pkg_dict),
            -1
        )

    @patch.object(osplatform, 'get_platform')
    def test_cmp_pkgrevno_revnos_centos(self, platform):
        platform.return_value = 'centos'
        imp.reload(host)

        class MockPackage:
            def __init__(self, name, version):
                self.Name = name
                self.version = version

        yum_dict = {
            'installed': {
                MockPackage('python', '2.4')
            }
        }

        import yum
        yum.YumBase.return_value.doPackageLists.return_value = (
            yum_dict)

        self.assertEqual(host.cmp_pkgrevno('python', '2.3'), 1)
        self.assertEqual(host.cmp_pkgrevno('python', '2.4'), 0)
        self.assertEqual(host.cmp_pkgrevno('python', '2.5'), -1)

    @patch.object(host.os, 'stat')
    @patch.object(host.pwd, 'getpwuid')
    @patch.object(host.grp, 'getgrgid')
    @patch('posix.stat_result')
    def test_owner(self, stat_result_, getgrgid_, getpwuid_, stat_):
        getgrgid_.return_value = ['testgrp']
        getpwuid_.return_value = ['testuser']
        stat_.return_value = stat_result_()

        user, group = host.owner('/some/path')
        stat_.assert_called_once_with('/some/path')
        self.assertEqual('testuser', user)
        self.assertEqual('testgrp', group)

    def test_get_total_ram(self):
        raw = dedent('''\
                     MemFree:          183868 kB
                     MemTotal:        7096108 kB
                     MemAvailable:    5645240 kB
                     ''').strip()
        with patch_open() as (mock_open, mock_file):
            mock_file.readlines.return_value = raw.splitlines()
            self.assertEqual(host.get_total_ram(), 7266414592)  # 7GB
            mock_open.assert_called_once_with('/proc/meminfo', 'r')

    @patch.object(host, 'os')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.call')
    def test_is_container_with_systemd_container(self,
                                                 call,
                                                 init_is_systemd,
                                                 mock_os):
        init_is_systemd.return_value = True
        call.return_value = 0
        self.assertTrue(host.is_container())
        call.assert_called_with(['systemd-detect-virt', '--container'])

    @patch.object(host, 'os')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.call')
    def test_is_container_with_systemd_non_container(self,
                                                     call,
                                                     init_is_systemd,
                                                     mock_os):
        init_is_systemd.return_value = True
        call.return_value = 1
        self.assertFalse(host.is_container())
        call.assert_called_with(['systemd-detect-virt', '--container'])

    @patch.object(host, 'os')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.call')
    def test_is_container_with_upstart_container(self,
                                                 call,
                                                 init_is_systemd,
                                                 mock_os):
        init_is_systemd.return_value = False
        mock_os.path.exists.return_value = True
        self.assertTrue(host.is_container())
        mock_os.path.exists.assert_called_with('/run/container_type')

    @patch.object(host, 'os')
    @patch.object(host, 'init_is_systemd')
    @patch('subprocess.call')
    def test_is_container_with_upstart_not_container(self,
                                                     call,
                                                     init_is_systemd,
                                                     mock_os):
        init_is_systemd.return_value = False
        mock_os.path.exists.return_value = False
        self.assertFalse(host.is_container())
        mock_os.path.exists.assert_called_with('/run/container_type')

    def test_updatedb(self):
        updatedb_text = 'PRUNEPATHS="/tmp"'
        self.assertEqual(host.updatedb(updatedb_text, '/srv/node'),
                         'PRUNEPATHS="/tmp /srv/node"')

    def test_no_change_updatedb(self):
        updatedb_text = 'PRUNEPATHS="/tmp /srv/node"'
        self.assertEqual(host.updatedb(updatedb_text, '/srv/node'),
                         updatedb_text)

    def test_no_prunepaths(self):
        updatedb_text = 'PRUNE_BIND_MOUNTS="yes"'
        self.assertEqual(host.updatedb(updatedb_text, '/srv/node'),
                         updatedb_text)

    @patch('os.path')
    def test_write_updatedb(self, mock_path):
        mock_path.exists.return_value = True
        mock_path.isdir.return_value = False
        _open = mock_open(read_data='PRUNEPATHS="/tmp /srv/node"')
        with patch('charmhelpers.core.host.open', _open, create=True):
            host.add_to_updatedb_prunepath("/tmp/test")
        handle = _open()

        self.assertTrue(handle.read.call_count == 1)
        self.assertTrue(handle.seek.call_count == 1)
        handle.write.assert_called_once_with(
            'PRUNEPATHS="/tmp /srv/node /tmp/test"')

    @patch.object(host, 'os')
    def test_prunepaths_no_updatedb_conf_file(self, mock_os):
        mock_os.path.exists.return_value = False
        _open = mock_open(read_data='PRUNEPATHS="/tmp /srv/node"')
        with patch('charmhelpers.core.host.open', _open, create=True):
            host.add_to_updatedb_prunepath("/tmp/test")
        handle = _open()

        self.assertTrue(handle.call_count == 0)

    @patch.object(host, 'os')
    def test_prunepaths_updatedb_conf_file_isdir(self, mock_os):
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = True
        _open = mock_open(read_data='PRUNEPATHS="/tmp /srv/node"')
        with patch('charmhelpers.core.host.open', _open, create=True):
            host.add_to_updatedb_prunepath("/tmp/test")
        handle = _open()

        self.assertTrue(handle.call_count == 0)

    @patch.object(host, 'local_unit')
    def test_modulo_distribution(self, local_unit):
        local_unit.return_value = 'test/7'

        # unit % modulo * wait
        self.assertEqual(host.modulo_distribution(modulo=6, wait=10), 10)

        # Zero wait when unit % modulo == 0
        self.assertEqual(host.modulo_distribution(modulo=7, wait=10), 0)

        # modulo * wait when unit % modulo == 0 and non_zero_wait=True
        self.assertEqual(host.modulo_distribution(modulo=7, wait=10,
                                                  non_zero_wait=True),
                         70)

    @patch.object(host, 'log')
    @patch.object(host, 'charm_name')
    @patch.object(host, 'write_file')
    @patch.object(subprocess, 'check_call')
    @patch.object(host, 'file_hash')
    @patch('hashlib.md5')
    def test_install_ca_cert_new_cert(self, md5, file_hash, check_call,
                                      write_file, charm_name, log):
        file_hash.return_value = 'old_hash'
        charm_name.return_value = 'charm-name'

        md5().hexdigest.return_value = 'old_hash'
        host.install_ca_cert('cert_data')
        assert not check_call.called

        md5().hexdigest.return_value = 'new_hash'
        host.install_ca_cert(None)
        assert not check_call.called
        host.install_ca_cert('')
        assert not check_call.called

        host.install_ca_cert('cert_data', 'name')
        write_file.assert_called_with(
            '/usr/local/share/ca-certificates/name.crt',
            b'cert_data')
        check_call.assert_called_with(['update-ca-certificates', '--fresh'])

        host.install_ca_cert('cert_data')
        write_file.assert_called_with(
            '/usr/local/share/ca-certificates/juju-charm-name.crt',
            b'cert_data')
        check_call.assert_called_with(['update-ca-certificates', '--fresh'])

    @patch('subprocess.check_output')
    def test_arch(self, check_output):
        _ = host.arch()
        check_output.assert_called_with(
            ['dpkg', '--print-architecture']
        )

    @patch('subprocess.check_output')
    def test_get_system_env(self, check_output):
        check_output.return_value = ''
        self.assertEquals(
            host.get_system_env('aKey', 'aDefault'), 'aDefault')
        self.assertEquals(host.get_system_env('aKey'), None)
        check_output.return_value = 'aKey=aValue\n'
        self.assertEquals(
            host.get_system_env('aKey', 'aDefault'), 'aValue')
        check_output.return_value = 'otherKey=shell=wicked\n'
        self.assertEquals(
            host.get_system_env('otherKey', 'aDefault'), 'shell=wicked')


class TestHostCompator(TestCase):

    def test_compare_ubuntu_releases(self):
        from charmhelpers.osplatform import get_platform
        if get_platform() == 'ubuntu':
            self.assertTrue(host.CompareHostReleases('yakkety') < 'zesty')
