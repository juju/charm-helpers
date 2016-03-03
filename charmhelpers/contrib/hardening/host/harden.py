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
import subprocess

from charmhelpers.contrib.hardening import (
    templating,
    utils,
)
from charmhelpers.contrib.hardening.host.checks import (
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
from charmhelpers.contrib.hardening.host.suid_guid import (
    suid_guid_harden,
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


def register_configs():
    configs = templating.HardeningConfigRenderer('os',
                                                 templates_dir=TEMPLATES)
    # See templating.TemplateContext for schema
    confs = {'/usr/share/pam-configs/tally2':
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
              }
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
