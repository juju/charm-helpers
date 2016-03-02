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

from subprocess import check_output
from subprocess import CalledProcessError

from charmhelpers.core.hookenv import log
from charmhelpers.core.hookenv import ERROR

from charmhelpers.contrib.hardening.audits.file import TemplatedFileAudit
from charmhelpers.contrib.hardening import utils

from charmhelpers.fetch import apt_install
from charmhelpers.fetch import apt_purge


def get_audits():
    """Returns the set of audits for PAM authentication."""
    audits = []

    audits.append(PAMAudit('/etc/passwdqc.conf', PasswdqcPAMContext()))
    audits.append(PAMAudit('/usr/share/pam-configs/tally2',
                           Tally2PAMContext()))

    return audits


class PasswdqcPAMContext(object):

    def __call__(self):
        ctxt = {}
        defaults = utils.get_defaults('os')

        # Always remove?
        apt_purge('libpam-ccreds')

        # NOTE: see man passwdqc.conf
        if defaults.get('auth_pam_passwdqc_enable'):
            apt_purge('libpam-cracklib')
            apt_install('libpam-passwdqc')
            ctxt['auth_pam_passwdqc_options'] = \
                defaults.get('auth_pam_passwdqc_options')
        else:
            apt_purge('libpam-passwdqc')

        return ctxt


class Tally2PAMContext(object):

    def __call__(self):
        ctxt = {}
        defaults = utils.get_defaults('os')

        # Always remove?
        apt_purge('libpam-ccreds')

        ctxt['auth_lockout_time'] = defaults.get('auth_lockout_time')
        if defaults.get('auth_retries'):
            ctxt['auth_retries'] = defaults.get('auth_retries')
            apt_install('libpam-modules')
        else:
            if os.path.exists('/usr/share/pam-configs/tally2'):
                os.remove('/usr/share/pam-configs/tally2')
            # Stop template from being written since we want to disable
            # tally2
            ctxt['__disable__'] = True

        return ctxt


class PAMAudit(TemplatedFileAudit):
    """The PAM Audit verifies the linux PAM settings."""
    def __init__(self, path, context):
        super(PAMAudit, self).__init__(paths=path, context=context,
                                       user='root', group='root', mode=0o0640)

    def post_hooks(self):
        """Updates the PAM configuration after the file has been written"""
        try:
            check_output(['pam-auth-update', '--package'])
        except CalledProcessError as e:
            log('Error calling pam-auth-update: %s' % e, level=ERROR)