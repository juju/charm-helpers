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

from charmhelpers.contrib.hardening import (
    templating,
    utils,
)
from charmhelpers.contrib.hardening.os_hardening.checks import (
    run_os_checks,
)
from charmhelpers.core.hookenv import (
    log,
    DEBUG,
    INFO,
    config,
)
from charmhelpers.fetch import (
    apt_install,
    apt_purge,
)
from charmhelpers.contrib.hardening.os_hardening.sysctl import (
    SysCtlHardeningContext,
)
from charmhelpers.contrib.hardening.os_hardening.suid_guid import (
    suid_guid_harden,
)
from charmhelpers.contrib.hardening.os_hardening.apthardening import (
    apt_harden,
)

TEMPLATES = os.path.join(os.path.dirname(__file__), 'templates')


class PAMContext(object):

    def __init__(self, pam_name):
        self.pam_name = pam_name

    def __call__(self):
        ctxt = {}
        defaults = utils.get_defaults('os')

        # Always remove?
        apt_purge('libpam-ccreds')

        if self.pam_name == 'passwdqc':
            # NOTE: see man passwdqc.conf
            if defaults.get('auth_pam_passwdqc_enable'):
                apt_purge('libpam-cracklib')
                apt_install('libpam-passwdqc')
                ctxt['auth_pam_passwdqc_options'] = \
                    defaults.get('auth_pam_passwdqc_options')
            else:
                apt_purge('libpam-passwdqc')
        elif self.pam_name == 'tally2':
            ctxt['auth_lockout_time'] = defaults.get('auth_lockout_time')
            if defaults.get('auth_retries'):
                ctxt['auth_retries'] = defaults.get('auth_retries')
                apt_install('libpam-modules')
            else:
                os.remove('/usr/share/pam-configs/tally2')
                # Stop template frombeing written since we want to disable
                # tally2
                ctxt['__disable__'] = True
        else:
            raise Exception("Unrecognised PAM name '%s'" % (self.pam_name))

        return ctxt


class ModulesContext(object):

    def __call__(self):
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

        defaults = utils.get_defaults('os')
        ctxt = {'arch': platform.processor(),
                'cpuVendor': vendor,
                'desktop_enable': defaults.get('desktop_enable', False)}

        return ctxt


class LoginContext(object):

    def __call__(self):
        defaults = utils.get_defaults('os')
        ctxt = {'additional_user_paths':
                defaults.get('env_extra_user_paths'),
                'umask': defaults.get('env_umask'),
                'pwd_max_age': defaults.get('auth_pw_max_age'),
                'pwd_min_age': defaults.get('auth_pw_min_age'),
                'uid_min': defaults.get('auth_uid_min'),
                'sys_uid_min': defaults.get('auth_sys_uid_min'),
                'sys_uid_max': defaults.get('auth_sys_uid_max'),
                'gid_min': defaults.get('auth_gid_min'),
                'sys_gid_min': defaults.get('auth_sys_gid_min'),
                'sys_gid_max': defaults.get('auth_sys_gid_max'),
                'login_retries': defaults.get('auth_retries'),
                'login_timeout': defaults.get('auth_timeout'),
                'chfn_restrict': defaults.get('chfn_restrict'),
                'allow_login_without_home':
                defaults.get('auth_allow_homeless')
                }

        if 'change_user' not in defaults.get('security_users_allow', []):
            utils.ensure_permissions('/bin/su', 'root', 'root', 0o0750)

        return ctxt


class ProfileContext(object):

    def __call__(self):
        ctxt = {}
        return ctxt


class SecureTTYContext(object):

    def __call__(self):
        defaults = utils.get_defaults('os')
        ctxt = {'ttys': defaults.get('auth_root_ttys')}
        return ctxt


class SecurityLimitsContext(object):

    def __call__(self):
        defaults = utils.get_defaults('os')
        ctxt = {'disable_core_dump':
                not defaults.get('enable_core_dump', False)}
        return ctxt


def register_configs():
    configs = templating.HardeningConfigRenderer('os',
                                                 templates_dir=TEMPLATES)
    # See templating.TemplateContext for schema
    confs = {'/etc/initramfs-tools/modules':
             {'contexts': [ModulesContext()],
              'permissions': [('/etc/initramfs-tools/modules', 'root', 'root',
                               0o0440)]},
             '/etc/login.defs':
             {'contexts': [LoginContext()],
              'permissions': [('/etc/login.defs', 'root', 'root', 0o0444),
                              ('/etc/shadow', 'root', 'root', 0o0600)]},
             '/etc/profile.d/pinerolo_profile.sh':
             {'contexts': [ProfileContext()],
              'permissions': [('/etc/profile.d/pinerolo_profile.sh', 'root',
                               'root', 0o0755)]},
             '/etc/securetty':
             {'contexts': [SecureTTYContext()],
              'permissions': [('/etc/securetty', 'root', 'root', 0o0400)]
              },
             '/etc/security/limits.d/10.hardcore.conf':
             {'contexts': [SecurityLimitsContext()],
              'permissions': [('/etc/security/limits.d', 'root', 'root',
                               0o0755),
                              ('/etc/security/limits.d/10.hardcore.conf',
                               'root', 'root', 0o0440)]},
             '/usr/share/pam-configs/tally2':
             {'contexts': [PAMContext('tally2')],
              'permissions': [('/usr/share/pam-configs/tally2', 'root',
                               'root', 0o0640)],
              'posthooks': [(subprocess.check_output,
                            [['pam-auth-update', '--package']], {})]},
             '/etc/passwdqc.conf':
             {'contexts': [PAMContext('passwdqc')],
              'permissions': [('/etc/passwdqc.conf', 'root',
                               'root', 0o0640)],
              'posthooks': [(subprocess.check_output,
                            [['pam-auth-update', '--package']], {})]
              },
             '/etc/sysctl.conf':
             {'contexts': [SysCtlHardeningContext()],
              'permissions': [('/etc/sysctl.conf', 'root', 'root', 0o0440)],
              'posthooks': [(subprocess.check_output,
                            [['sysctl', '-p', '/etc/sysctl.conf']], {})]}
             }

    for conf in confs:
        configs.register('os', conf, confs[conf])

    return configs


OS_CONFIGS = register_configs()


def harden_os():
    log("Hardening OS", level=INFO)
    log("Applying configs", level=DEBUG)
    OS_CONFIGS.write_all()
    suid_guid_harden()
    apt_harden()
    log("Running checks", level=DEBUG)
    run_os_checks()
    log("OS hardening complete", level=INFO)


def dec_harden_os(f):
    if config('harden'):
        harden_os()

    def _harden_os(*args, **kwargs):
        return f(*args, **kwargs)

    return _harden_os


# Run on import
if config('harden'):
    harden_os()
