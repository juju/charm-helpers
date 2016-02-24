import os

from charmhelpers.core.hookenv import (
    log,
    INFO,
    WARNING,
)
from charmhelpers.contrib.hardening import (
    utils,
)


class SysCtlHardeningContext(object):
    def __call__(self):
        ctxt = {'sysctl': {}}

        log("Applying SYSCTL settings", level=INFO)
        defaults = utils.get_defaults('os')
        extras = {'net_ipv4_ip_forward': 0,
                  'net_ipv6_conf_all_forwarding': 0,
                  'net_ipv6_conf_all_disable_ipv6': 1,
                  'net_ipv4_tcp_timestamps': 0,
                  'net_ipv4_conf_all_arp_ignore': 0,
                  'net_ipv4_conf_all_arp_announce': 0,
                  'kernel_sysrq': 0,
                  'fs_suid_dumpable': 0,
                  'kernel_modules_disabled': 1}

        if defaults.get('network_ipv6_enable'):
            extras['net_ipv6_conf_all_disable_ipv6'] = 0

        if defaults.get('network_forwarding'):
            extras['net_ipv4_ip_forward'] = 1
            extras['net_ipv6_conf_all_forwarding'] = 1

        if defaults.get('network_arp_restricted'):
            extras['net_ipv4_conf_all_arp_ignore'] = 1

        if defaults.get('security_kernel_enable_module_loading'):
            extras['kernel_modules_disabled'] = 0

        if defaults.get('security_kernel_enable_sysrq'):
            sysrq_val = defaults.get('security_kernel_secure_sysrq')
            extras['kernel_sysrq'] = sysrq_val

        if defaults.get('security_kernel_enable_core_dump'):
            extras['fs_suid_dumpable'] = 1

        sysctl_defaults = """
        net.ipv4.ip_forward=%(net_ipv4_ip_forward)s
        net.ipv6.conf.all.forwarding=%(net_ipv6_conf_all_forwarding)s
        net.ipv4.conf.all.rp_filter=1
        net.ipv4.conf.default.rp_filter=1
        net.ipv4.icmp_echo_ignore_broadcasts=1
        net.ipv4.icmp_ignore_bogus_error_responses=1
        net.ipv4.icmp_ratelimit=100
        net.ipv4.icmp_ratemask=88089
        net.ipv6.conf.all.disable_ipv6=%(net_ipv6_conf_all_disable_ipv6)s
        net.ipv4.tcp_timestamps=%(net_ipv4_tcp_timestamps)s
        net.ipv4.conf.all.arp_ignore=%(net_ipv4_conf_all_arp_ignore)s
        net.ipv4.conf.all.arp_announce=%(net_ipv4_conf_all_arp_announce)s
        net.ipv4.tcp_rfc1337=1
        net.ipv4.tcp_syncookies=1
        net.ipv4.conf.all.shared_media=1
        net.ipv4.conf.default.shared_media=1
        net.ipv4.conf.all.accept_source_route=0
        net.ipv4.conf.default.accept_source_route=0
        net.ipv4.conf.all.accept_redirects=0
        net.ipv4.conf.default.accept_redirects=0
        net.ipv6.conf.all.accept_redirects=0
        net.ipv6.conf.default.accept_redirects=0
        net.ipv4.conf.all.secure_redirects=0
        net.ipv4.conf.default.secure_redirects=0
        net.ipv4.conf.all.send_redirects=0
        net.ipv4.conf.default.send_redirects=0
        net.ipv4.conf.all.log_martians=0
        net.ipv6.conf.default.router_solicitations=0
        net.ipv6.conf.default.accept_ra_rtr_pref=0
        net.ipv6.conf.default.accept_ra_pinfo=0
        net.ipv6.conf.default.accept_ra_defrtr=0
        net.ipv6.conf.default.autoconf=0
        net.ipv6.conf.default.dad_transmits=0
        net.ipv6.conf.default.max_addresses=1
        net.ipv6.conf.all.accept_ra=0
        net.ipv6.conf.default.accept_ra=0
        kernel.modules_disabled=%(kernel_modules_disabled)s
        kernel.sysrq=%(kernel_sysrq)s
        fs.suid_dumpable=%(fs_suid_dumpable)s
        kernel.randomize_va_space=2
        """
        defaults.update(extras)
        for d in (sysctl_defaults % defaults).split():
            d = d.strip().partition('=')
            key = d[0].strip()
            path = os.path.join('/proc/sys', key.replace('.', '/'))
            if not os.path.exists(path):
                log("Skipping '%s' since '%s' does not exist" % (key, path),
                    level=WARNING)
                continue

            ctxt['sysctl'][key] = d[2] or None

        return ctxt
