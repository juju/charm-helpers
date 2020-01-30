from __future__ import print_function

import mock
import os
import subprocess
import unittest

from charmhelpers.contrib.network import ufw

__author__ = 'Felipe Reyes <felipe.reyes@canonical.com>'


LSMOD_NO_IP6 = """Module                  Size  Used by
raid1                  39533  1
psmouse               106548  0
raid0                  17842  0
ahci                   34062  5
multipath              13145  0
r8169                  71471  0
libahci                32424  1 ahci
mii                    13934  1 r8169
linear                 12894  0
"""
LSMOD_IP6 = """Module                  Size  Used by
xt_hl                  12521  0
ip6_tables             27026  0
ip6t_rt                13537  0
nf_conntrack_ipv6      18894  0
nf_defrag_ipv6         34769  1 nf_conntrack_ipv6
xt_recent              18457  0
xt_LOG                 17702  0
xt_limit               12711  0
"""
DEFAULT_POLICY_OUTPUT = """Default incoming policy changed to 'deny'
(be sure to update your rules accordingly)
"""
DEFAULT_POLICY_OUTPUT_OUTGOING = """Default outgoing policy changed to 'allow'
(be sure to update your rules accordingly)
"""

UFW_STATUS_NUMBERED = """Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 6641/tcp                   ALLOW IN    10.219.3.86                # charm-ovn-central
[12] 6641/tcp                   REJECT IN   Anywhere
[19] 6644/tcp (v6)              REJECT IN   Anywhere (v6)              # charm-ovn-central

"""


class TestUFW(unittest.TestCase):
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    @mock.patch('charmhelpers.contrib.network.ufw.modprobe')
    def test_enable_ok(self, modprobe, check_output, log):
        msg = 'Firewall is active and enabled on system startup\n'
        check_output.return_value = msg
        self.assertTrue(ufw.enable())

        check_output.assert_any_call(['ufw', 'enable'],
                                     universal_newlines=True,
                                     env={'LANG': 'en_US',
                                          'PATH': os.environ['PATH']})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call('ufw enabled', level='INFO')

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    @mock.patch('charmhelpers.contrib.network.ufw.modprobe')
    def test_enable_fail(self, modprobe, check_output, log):
        msg = 'neneene\n'
        check_output.return_value = msg
        self.assertFalse(ufw.enable())

        check_output.assert_any_call(['ufw', 'enable'],
                                     universal_newlines=True,
                                     env={'LANG': 'en_US',
                                          'PATH': os.environ['PATH']})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call("ufw couldn't be enabled", level='WARN')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_disable_ok(self, check_output, log, is_enabled):
        is_enabled.return_value = True
        msg = 'Firewall stopped and disabled on system startup\n'
        check_output.return_value = msg
        self.assertTrue(ufw.disable())

        check_output.assert_any_call(['ufw', 'disable'],
                                     universal_newlines=True,
                                     env={'LANG': 'en_US',
                                          'PATH': os.environ['PATH']})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call('ufw disabled', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_disable_fail(self, check_output, log, is_enabled):
        is_enabled.return_value = True
        msg = 'neneene\n'
        check_output.return_value = msg
        self.assertFalse(ufw.disable())

        check_output.assert_any_call(['ufw', 'disable'],
                                     universal_newlines=True,
                                     env={'LANG': 'en_US',
                                          'PATH': os.environ['PATH']})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call("ufw couldn't be disabled", level='WARN')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_modify_access_ufw_is_disabled(self, check_output, log,
                                           is_enabled):
        is_enabled.return_value = False
        ufw.modify_access('127.0.0.1')
        log.assert_any_call('ufw is disabled, skipping modify_access()',
                            level='WARN')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_allow(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('127.0.0.1')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               'any'], stdout=subprocess.PIPE)
        log.assert_any_call('ufw allow: ufw allow from 127.0.0.1 to any',
                            level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_allow_set_proto(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('127.0.0.1', proto='udp')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               'any', 'proto', 'udp'], stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw allow from 127.0.0.1 '
                             'to any proto udp'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_allow_set_port(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('127.0.0.1', port='80')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               'any', 'port', '80'], stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw allow from 127.0.0.1 '
                             'to any port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_allow_set_dst(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('127.0.0.1', dst='127.0.0.1', port='80')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               '127.0.0.1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw allow from 127.0.0.1 '
                             'to 127.0.0.1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_allow_ipv6(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('::1', dst='::1', port='80')
        popen.assert_any_call(['ufw', 'allow', 'from', '::1', 'to',
                               '::1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw allow from ::1 '
                             'to ::1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_with_index(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.modify_access('127.0.0.1', dst='127.0.0.1', port='80', index=1)
        popen.assert_any_call(['ufw', 'insert', '1', 'allow', 'from',
                               '127.0.0.1', 'to', '127.0.0.1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw insert 1 allow from 127.0.0.1 '
                             'to 127.0.0.1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_prepend(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p
        ufw.modify_access('127.0.0.1', dst='127.0.0.1', port='80',
                          prepend=True)
        popen.assert_any_call(['ufw', 'prepend', 'allow', 'from', '127.0.0.1',
                               'to', '127.0.0.1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw prepend allow from 127.0.0.1 '
                             'to 127.0.0.1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_comment(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p
        ufw.modify_access('127.0.0.1', dst='127.0.0.1', port='80',
                          comment='No comment')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1',
                               'to', '127.0.0.1', 'port', '80',
                               'comment', 'No comment'],
                              stdout=subprocess.PIPE)

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_modify_access_delete_index(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p
        ufw.modify_access(None, dst=None, action='delete', index=42)
        popen.assert_any_call(['ufw', '--force', 'delete', '42'],
                              stdout=subprocess.PIPE)

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_grant_access(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.grant_access('127.0.0.1', dst='127.0.0.1', port='80')
        popen.assert_any_call(['ufw', 'allow', 'from', '127.0.0.1', 'to',
                               '127.0.0.1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw allow from 127.0.0.1 '
                             'to 127.0.0.1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_grant_access_with_index(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.grant_access('127.0.0.1', dst='127.0.0.1', port='80', index=1)
        popen.assert_any_call(['ufw', 'insert', '1', 'allow', 'from',
                               '127.0.0.1', 'to', '127.0.0.1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw allow: ufw insert 1 allow from 127.0.0.1 '
                             'to 127.0.0.1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.Popen')
    def test_revoke_access(self, popen, log, is_enabled):
        is_enabled.return_value = True
        p = mock.Mock()
        p.configure_mock(**{'communicate.return_value': ('stdout', 'stderr'),
                            'returncode': 0})
        popen.return_value = p

        ufw.revoke_access('127.0.0.1', dst='127.0.0.1', port='80')
        popen.assert_any_call(['ufw', 'delete', 'allow', 'from', '127.0.0.1',
                               'to', '127.0.0.1', 'port', '80'],
                              stdout=subprocess.PIPE)
        log.assert_any_call(('ufw delete: ufw delete allow from 127.0.0.1 '
                             'to 127.0.0.1 port 80'), level='DEBUG')
        log.assert_any_call('stdout', level='INFO')

    @mock.patch('subprocess.check_output')
    def test_service_open(self, check_output):
        ufw.service('ssh', 'open')
        check_output.assert_any_call(['ufw', 'allow', 'ssh'],
                                     universal_newlines=True)

    @mock.patch('subprocess.check_output')
    def test_service_close(self, check_output):
        ufw.service('ssh', 'close')
        check_output.assert_any_call(['ufw', 'delete', 'allow', 'ssh'],
                                     universal_newlines=True)

    @mock.patch('subprocess.check_output')
    def test_service_unsupport_action(self, check_output):
        self.assertRaises(ufw.UFWError, ufw.service, 'ssh', 'nenene')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('os.path.isdir')
    @mock.patch('subprocess.call')
    @mock.patch('subprocess.check_output')
    def test_no_ipv6(self, check_output, call, isdir, log, is_enabled):
        check_output.return_value = ('Firewall is active and enabled '
                                     'on system startup\n')
        isdir.return_value = False
        call.return_value = 0
        is_enabled.return_value = False
        ufw.enable()

        call.assert_called_with(['sed', '-i', 's/IPV6=.*/IPV6=no/g',
                                 '/etc/default/ufw'])
        log.assert_any_call('IPv6 support in ufw disabled', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('os.path.isdir')
    @mock.patch('subprocess.call')
    @mock.patch('subprocess.check_output')
    @mock.patch('charmhelpers.contrib.network.ufw.modprobe')
    def test_no_ip6_tables(self, modprobe, check_output, call, isdir, log,
                           is_enabled):
        def c(*args, **kwargs):
            if args[0] == ['lsmod']:
                return LSMOD_NO_IP6
            elif args[0] == ['modprobe', 'ip6_tables']:
                return ""
            else:
                return 'Firewall is active and enabled on system startup\n'

        check_output.side_effect = c
        isdir.return_value = True
        call.return_value = 0

        is_enabled.return_value = False
        self.assertTrue(ufw.enable())

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('os.path.isdir')
    @mock.patch('charmhelpers.contrib.network.ufw.modprobe')
    @mock.patch('charmhelpers.contrib.network.ufw.is_module_loaded')
    def test_no_ip6_tables_fail_to_load(self, is_module_loaded,
                                        modprobe, isdir, log, is_enabled):
        is_module_loaded.return_value = False

        def c(m):
            raise subprocess.CalledProcessError(1, ['modprobe',
                                                    'ip6_tables'],
                                                "fail to load ip6_tables")

        modprobe.side_effect = c
        isdir.return_value = True
        is_enabled.return_value = False

        self.assertRaises(ufw.UFWIPv6Error, ufw.enable)

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('os.path.isdir')
    @mock.patch('charmhelpers.contrib.network.ufw.modprobe')
    @mock.patch('charmhelpers.contrib.network.ufw.is_module_loaded')
    @mock.patch('subprocess.call')
    @mock.patch('subprocess.check_output')
    def test_no_ip6_tables_fail_to_load_soft_fail(self, check_output,
                                                  call, is_module_loaded,
                                                  modprobe,
                                                  isdir, log, is_enabled):
        is_module_loaded.return_value = False

        def c(m):
            raise subprocess.CalledProcessError(1, ['modprobe',
                                                    'ip6_tables'],
                                                "fail to load ip6_tables")

        modprobe.side_effect = c
        isdir.return_value = True
        call.return_value = 0
        check_output.return_value = ("Firewall is active and enabled on "
                                     "system startup\n")
        is_enabled.return_value = False
        self.assertTrue(ufw.enable(soft_fail=True))
        call.assert_called_with(['sed', '-i', 's/IPV6=.*/IPV6=no/g',
                                 '/etc/default/ufw'])
        log.assert_any_call('IPv6 support in ufw disabled', level='INFO')

    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('os.path.isdir')
    @mock.patch('subprocess.call')
    @mock.patch('subprocess.check_output')
    def test_no_ipv6_failed_disabling_ufw(self, check_output, call, isdir,
                                          log, is_enabled):
        check_output.return_value = ('Firewall is active and enabled '
                                     'on system startup\n')
        isdir.return_value = False
        call.return_value = 1
        is_enabled.return_value = False
        self.assertRaises(ufw.UFWError, ufw.enable)

        call.assert_called_with(['sed', '-i', 's/IPV6=.*/IPV6=no/g',
                                 '/etc/default/ufw'])
        log.assert_any_call("Couldn't disable IPv6 support in ufw",
                            level="ERROR")

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('charmhelpers.contrib.network.ufw.is_enabled')
    @mock.patch('os.path.isdir')
    @mock.patch('subprocess.check_output')
    @mock.patch('charmhelpers.contrib.network.ufw.modprobe')
    def test_with_ipv6(self, modprobe, check_output, isdir, is_enabled, log):
        def c(*args, **kwargs):
            if args[0] == ['lsmod']:
                return LSMOD_IP6
            else:
                return 'Firewall is active and enabled on system startup\n'

        check_output.side_effect = c
        is_enabled.return_value = False
        isdir.return_value = True
        ufw.enable()

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_change_default_policy(self, check_output, log):
        check_output.return_value = DEFAULT_POLICY_OUTPUT
        self.assertTrue(ufw.default_policy())
        check_output.asser_any_call(['ufw', 'default', 'deny', 'incoming'])

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_change_default_policy_allow_outgoing(self, check_output, log):
        check_output.return_value = DEFAULT_POLICY_OUTPUT_OUTGOING
        self.assertTrue(ufw.default_policy('allow', 'outgoing'))
        check_output.asser_any_call(['ufw', 'default', 'allow', 'outgoing'])

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_change_default_policy_unexpected_output(self, check_output, log):
        check_output.return_value = "asdf"
        self.assertFalse(ufw.default_policy())

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_change_default_policy_wrong_policy(self, check_output, log):
        self.assertRaises(ufw.UFWError, ufw.default_policy, 'asdf')

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    def test_change_default_policy_wrong_direction(self, check_output, log):
        self.assertRaises(ufw.UFWError, ufw.default_policy, 'allow', 'asdf')

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    @mock.patch('charmhelpers.contrib.network.ufw.modprobe')
    def test_reload_ok(self, modprobe, check_output, log):
        msg = 'Firewall reloaded\n'
        check_output.return_value = msg
        self.assertTrue(ufw.reload())

        check_output.assert_any_call(['ufw', 'reload'],
                                     universal_newlines=True,
                                     env={'LANG': 'en_US',
                                          'PATH': os.environ['PATH']})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call('ufw reloaded', level='INFO')

    @mock.patch('charmhelpers.core.hookenv.log')
    @mock.patch('subprocess.check_output')
    @mock.patch('charmhelpers.contrib.network.ufw.modprobe')
    def test_reload_fail(self, modprobe, check_output, log):
        msg = 'This did not work\n'
        check_output.return_value = msg
        self.assertFalse(ufw.reload())

        check_output.assert_any_call(['ufw', 'reload'],
                                     universal_newlines=True,
                                     env={'LANG': 'en_US',
                                          'PATH': os.environ['PATH']})
        log.assert_any_call(msg, level='DEBUG')
        log.assert_any_call("ufw couldn't be reloaded", level='WARN')

    def test_status(self):
        with mock.patch('subprocess.check_output') as check_output:
            check_output.return_value = UFW_STATUS_NUMBERED
            expect = {
                1: {'to': '6641/tcp', 'action': 'allow in',
                    'from': '10.219.3.86', 'ipv6': False,
                    'comment': 'charm-ovn-central'},
                12: {'to': '6641/tcp', 'action': 'reject in',
                     'from': 'any', 'ipv6': False,
                     'comment': ''},
                19: {'to': '6644/tcp', 'action': 'reject in',
                     'from': 'any', 'ipv6': True,
                     'comment': 'charm-ovn-central'},
            }
            n_rules = 0
            for n, r in ufw.status():
                self.assertDictEqual(r, expect[n])
                n_rules += 1
            self.assertEquals(n_rules, 3)
