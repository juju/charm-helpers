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
import yaml

from charmhelpers.contrib.hardening import templating
from charmhelpers.contrib.hardening.utils import (
    ensure_permissions,
)
from charmhelpers.core.hookenv import config

OS_TEMPLATES = os.path.join(os.path.dirname(__file__), 'templates')


def get_defaults():
    defaults = os.path.join(os.path.dirname(__file__),
                            'defaults/main.yaml')
    return yaml.safe_load(open(defaults))


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

        defaults = get_defaults()
        ctxt = {'arch': platform.processor(),
                'cpuVendor': vendor,
                'desktop_enable': defaults.get('os_desktop_enable', False)}

        return ctxt


class LoginContext(object):

    def __call__(self):
        defaults = get_defaults()
        ctxt = {'additional_user_paths':
                defaults.get('os_env_extra_user_paths'),
                'umask': defaults.get('os_env_umask'),
                'pwd_max_age': defaults.get('os_auth_pw_max_age'),
                'pwd_min_age': defaults.get('os_auth_pw_min_age'),
                'uid_min': defaults.get('os_auth_uid_min'),
                'sys_uid_min': defaults.get('os_auth_sys_uid_min'),
                'sys_uid_max': defaults.get('os_auth_sys_uid_max'),
                'gid_min': defaults.get('os_auth_gid_min'),
                'sys_gid_min': defaults.get('os_auth_sys_gid_min'),
                'sys_gid_max': defaults.get('os_auth_sys_gid_max'),
                'login_retries': defaults.get('os_auth_retries'),
                'login_timeout': defaults.get('os_auth_timeout'),
                'chfn_restrict': defaults.get('os_chfn_restrict'),
                'allow_login_without_home':
                defaults.get('os_auth_allow_homeless')
                }

        return ctxt


class ProfileContext(object):

    def __call__(self):
        ctxt = {}
        return ctxt


class SecureTTYContext(object):

    def __call__(self):
        defaults = get_defaults()
        ctxt = {'ttys': defaults.get('os_auth_root_ttys')}
        return ctxt


class SecurityLimitsContext(object):

    def __call__(self):
        ctxt = {}
        return ctxt


def register_os_configs():
    configs = templating.HardeningConfigRenderer(templates_dir=OS_TEMPLATES)

    confs = {'/etc/modules':
             {'contexts': [ModulesContext()],
              'service_actions': [],
              'post-hooks': [(ensure_permissions,
                              ('/etc/sysctl.conf', 'root', 0o0440), {}),
                             (ensure_permissions,
                              ('/etc/modules', 'root', 0o0440), {})]},
             '/etc/login.defs':
             {'contexts': [LoginContext()]},
             '/etc/profile.d/profile.conf':
             {'contexts': [ProfileContext()]},
             '/etc/securetty':
             {'contexts': [SecureTTYContext()]},
             '/etc/security/limits.conf':
             {'contexts': [SecurityLimitsContext()]},
             '/etc/security/limits.d/10.hardcore.conf':
             {'contexts': [SecurityLimitsContext()]}}

    for conf in confs:
        configs.register(conf, confs[conf])

    return configs


# Run on import
#if config('harden'):
OS_CONFIGS = register_os_configs()
OS_CONFIGS.write_all()


def harden_os(f):
    OS_CONFIGS.write_all()

    def _harden_os(*args, **kwargs):
        return f(*args, **kwargs)

    return _harden_os
