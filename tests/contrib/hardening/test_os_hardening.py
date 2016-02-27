import six
import tempfile

from mock import patch
from testtools import TestCase

CONFIG = {'harden': False}


with patch('charmhelpers.core.hookenv.config', lambda key: CONFIG.get('key')):
    from charmhelpers.contrib.hardening.os_hardening import harden

from charmhelpers.contrib.hardening.os_hardening import sysctl
from charmhelpers.contrib.hardening.templating import HardeningConfigRenderer


class OSHardeningTestCase(TestCase):

    def setUp(self):
        super(OSHardeningTestCase, self).setUp()

    @patch.object(harden.templating.HardeningConfigRenderer, 'render')
    @patch.object(harden.templating, 'log', lambda *args, **kwargs: None)
    def test_register_configs(self, mock_render):
        configs = harden.register_configs()
        self.assertEquals(type(configs), HardeningConfigRenderer)
        self.assertFalse(mock_render.called)

    @patch.object(harden.utils, 'ensure_permissions')
    @patch.object(harden, 'apt_purge')
    @patch.object(harden, 'apt_install')
    @patch.object(harden.templating, 'log', lambda *args, **kwargs: None)
    @patch.object(sysctl, 'log', lambda *args, **kwargs: None)
    def test_configs_render(self, mock_apt_install, mock_apt_purge,
                            mock_ensure_permissions):
        configs = harden.register_configs()
        for k in six.iterkeys(configs.templates['os']):
            configs.render(k)

        mock_ensure_permissions.assert_has_calls([])

    @patch.object(harden.utils, 'ensure_permissions')
    @patch.object(harden, 'apt_purge')
    @patch.object(harden, 'apt_install')
    @patch.object(harden.templating, 'log', lambda *args, **kwargs: None)
    @patch.object(sysctl, 'log', lambda *args, **kwargs: None)
    def test_configs_write(self, mock_apt_install, mock_apt_purge,
                           mock_ensure_permissions):
        configs = harden.register_configs()
        with tempfile.NamedTemporaryFile() as tmpfile:
            for k in six.iterkeys(configs.templates['os']):
                with open(tmpfile.name, 'w+') as fd:
                    r = configs.render(k)
                    try:
                        fd.write(r)
                    except UnicodeError:
                        fd.write(r.encode('utf-8').strip())

        mock_ensure_permissions.assert_has_calls([])

    @patch.object(sysctl.os.path, 'exists')
    @patch.object(sysctl, 'log', lambda *args, **kwargs: None)
    def test_sysctl(self, mock_exists):
        mock_exists.return_value = True
        ctxt = sysctl.SysCtlHardeningContext()()
        expected = {'sysctl':
                    {'fs.suid_dumpable': '0',
                     'kernel.modules_disabled': '0',
                     'kernel.randomize_va_space': '2',
                     'kernel.sysrq': '0',
                     'net.ipv4.conf.all.accept_redirects': '0',
                     'net.ipv4.conf.all.accept_source_route': '0',
                     'net.ipv4.conf.all.arp_announce': '0',
                     'net.ipv4.conf.all.arp_ignore': '1',
                     'net.ipv4.conf.all.log_martians': '0',
                     'net.ipv4.conf.all.rp_filter': '1',
                     'net.ipv4.conf.all.secure_redirects': '0',
                     'net.ipv4.conf.all.send_redirects': '0',
                     'net.ipv4.conf.all.shared_media': '1',
                     'net.ipv4.conf.default.accept_redirects': '0',
                     'net.ipv4.conf.default.accept_source_route': '0',
                     'net.ipv4.conf.default.rp_filter': '1',
                     'net.ipv4.conf.default.secure_redirects': '0',
                     'net.ipv4.conf.default.send_redirects': '0',
                     'net.ipv4.conf.default.shared_media': '1',
                     'net.ipv4.icmp_echo_ignore_broadcasts': '1',
                     'net.ipv4.icmp_ignore_bogus_error_responses': '1',
                     'net.ipv4.icmp_ratelimit': '100',
                     'net.ipv4.icmp_ratemask': '88089',
                     'net.ipv4.ip_forward': '0',
                     'net.ipv4.tcp_rfc1337': '1',
                     'net.ipv4.tcp_syncookies': '1',
                     'net.ipv4.tcp_timestamps': '0',
                     'net.ipv6.conf.all.accept_ra': '0',
                     'net.ipv6.conf.all.accept_redirects': '0',
                     'net.ipv6.conf.all.disable_ipv6': '1',
                     'net.ipv6.conf.all.forwarding': '0',
                     'net.ipv6.conf.default.accept_ra': '0',
                     'net.ipv6.conf.default.accept_ra_defrtr': '0',
                     'net.ipv6.conf.default.accept_ra_pinfo': '0',
                     'net.ipv6.conf.default.accept_ra_rtr_pref': '0',
                     'net.ipv6.conf.default.accept_redirects': '0',
                     'net.ipv6.conf.default.autoconf': '0',
                     'net.ipv6.conf.default.dad_transmits': '0',
                     'net.ipv6.conf.default.max_addresses': '1',
                     'net.ipv6.conf.default.router_solicitations': '0'}}

        self.assertEqual(ctxt, expected)

    @patch.object(sysctl.os.path, 'exists')
    @patch.object(sysctl, 'log', lambda *args, **kwargs: None)
    def test_sysctl_enoxist(self, mock_exists):
        mock_exists.return_value = False
        ctxt = sysctl.SysCtlHardeningContext()()
        expected = {'sysctl': {}}
        self.assertTrue(mock_exists.called)
        self.assertEqual(ctxt, expected)
