# Copyright 2016 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.
import os
import platform
import re
import subprocess

from charmhelpers.core.hookenv import (
    log,
    INFO,
    WARNING,
)
from charmhelpers.contrib.hardening import utils
from charmhelpers.contrib.hardening.audits.file import TemplatedFile
from charmhelpers.contrib.hardening.host import TEMPLATES_DIR


SYSCTL_DEFAULTS = """net.ipv4.ip_forward=%(net_ipv4_ip_forward)s
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


def get_audits():
    """Returns audits necessary for sysctl"""
    audits = []
    settings = utils.get_settings('os')

    # Apply the sysctl settings which are configured to be applied
    audits.append(SysctlConf())
    # Make sure that only root has access to the sysctl.conf file, and
    # that it is read-only.
    # TODO(wolsen) currently handled via /etc/sysctl.conf but I'm not
    # sure that's the right place? I think /etc/sysctl.d/99-hardening.conf
    # is likely a better place for our configuration options.
    # audits.append(FilePermissionAudit('/etc/sysctl.conf', user='root',
    #                                   group='root', mode=0o0440))
    # Make sure the sysctl directory is read only to users which are not
    # the root user.
    # TODO(wolsen) determine if this check is valid or if we just want
    # to restrict this to the /etc/sysctl.conf file. hardening-io doesnt
    # have it, but it makes sense? to also lock down the /etc/sysctl.d path
    # audits.append(DirectoryPermissionAudit('/etc/sysctl.d', user='root',
    #                                        group='root', mode=0o0550))

    # If module loading is not enabled, then ensure that the modules
    # file has the appropriate permissions and rebuild the initramfs
    if not settings['security']['kernel_enable_module_loading']:
        audits.append(ModulesTemplate())

    return audits


class ModulesContext(object):

    def __call__(self):
        settings = utils.get_settings('os')
        with open('/proc/cpuinfo', 'r') as fd:
            cpuinfo = fd.readlines()

        for line in cpuinfo:
            match = re.search(r"^vendor_id\s+:\s+(.+)", line)
            if match:
                vendor = match.group(1)

        if vendor == "GenuineIntel":
            vendor = "intel"
        elif vendor == "AuthenticAMD":
            vendor = "amd"

        ctxt = {'arch': platform.processor(),
                'cpuVendor': vendor,
                'desktop_enable': settings['general']['desktop_enable']}

        return ctxt


class ModulesTemplate(object):

    def __init__(self):
        super(ModulesTemplate, self).__init__('/etc/initramfs-tools/modules',
                                              ModulesContext(),
                                              templates_dir=TEMPLATES_DIR,
                                              user='root', group='root',
                                              mode=0o0440)

    def post_write(self):
        subprocess.check_call(['update-initramfs', '-u'])


class SysCtlHardeningContext(object):
    def __call__(self):
        settings = utils.get_settings('os')
        ctxt = {'sysctl': {}}

        log("Applying SYSCTL settings", level=INFO)
        extras = {'net_ipv4_ip_forward': 0,
                  'net_ipv6_conf_all_forwarding': 0,
                  'net_ipv6_conf_all_disable_ipv6': 1,
                  'net_ipv4_tcp_timestamps': 0,
                  'net_ipv4_conf_all_arp_ignore': 2,
                  'net_ipv4_conf_all_arp_announce': 0,
                  'kernel_sysrq': 0,
                  'fs_suid_dumpable': 0,
                  'kernel_modules_disabled': 1}

        if settings['sysctl']['ipv6_enable']:
            extras['net_ipv6_conf_all_disable_ipv6'] = 0

        if settings['sysctl']['forwarding']:
            extras['net_ipv4_ip_forward'] = 1
            extras['net_ipv6_conf_all_forwarding'] = 1

        if settings['sysctl']['arp_restricted']:
            extras['net_ipv4_conf_all_arp_ignore'] = 1

        if settings['security']['kernel_enable_module_loading']:
            extras['kernel_modules_disabled'] = 0

        if settings['sysctl']['kernel_enable_sysrq']:
            sysrq_val = settings['sysctl']['kernel_secure_sysrq']
            extras['kernel_sysrq'] = sysrq_val

        if settings['security']['kernel_enable_core_dump']:
            extras['fs_suid_dumpable'] = 1

        settings.update(extras)
        for d in (SYSCTL_DEFAULTS % settings).split():
            d = d.strip().partition('=')
            key = d[0].strip()
            path = os.path.join('/proc/sys', key.replace('.', '/'))
            if not os.path.exists(path):
                log("Skipping '%s' since '%s' does not exist" % (key, path),
                    level=WARNING)
                continue

            ctxt['sysctl'][key] = d[2] or None

        return ctxt


class SysctlConf(TemplatedFile):
    """An audit check for sysctl settings."""
    def __init__(self):
        self.conffile = '/etc/sysctl.conf'
        super(SysctlConf, self).__init__(self.conffile,
                                         SysCtlHardeningContext(),
                                         template_dir=TEMPLATES_DIR,
                                         user='root', group='root', mode=0o0440)

    def post_write(self):
        try:
            subprocess.check_call(['sysctl', '-p', self.conffile])
        except subprocess.CalledProcessError as e:
            # NOTE: on some systems if sysctl cannot apply all settings it
            #       will return non-zero as well.
            log("sysctl command returned an error (maybe some "
                "keys could not be set) - %s" % (e),
                level=WARNING)
