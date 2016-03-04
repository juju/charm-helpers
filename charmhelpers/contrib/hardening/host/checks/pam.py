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
from subprocess import check_output
from subprocess import CalledProcessError

from charmhelpers.core.hookenv import log
from charmhelpers.core.hookenv import ERROR

from charmhelpers.contrib.hardening.audits.file import TemplatedFile
from charmhelpers.contrib.hardening.audits.file import DeletedFile
from charmhelpers.contrib.hardening import utils

from charmhelpers.contrib.hardening.host import TEMPLATES_DIR

from charmhelpers.fetch import apt_install
from charmhelpers.fetch import apt_purge


def get_audits():
    """Returns the set of audits for PAM authentication."""
    audits = []

    defaults = utils.get_defaults('os')

    if defaults['auth']['pam_passwdqc_enable']:
        audits.append(PasswdqcPAM('/etc/passwdqc.conf'))

    if defaults['auth']['retries']:
        audits.append(Tally2PAM('/usr/share/pam-configs/tally2'))
    else:
        audits.append(DeletedFile('/usr/share/pam-configs/tally2'))

    return audits


class PasswdqcPAMContext(object):

    def __call__(self):
        ctxt = {}
        defaults = utils.get_defaults('os')

        ctxt['auth_pam_passwdqc_options'] = \
            defaults['auth']['pam_passwdqc_options']

        return ctxt


class PasswdqcPAM(TemplatedFile):
    """The PAM Audit verifies the linux PAM settings."""
    def __init__(self, path):
        super(PasswdqcPAM, self).__init__(path=path,
                                          template_dir=TEMPLATES_DIR,
                                          context=PasswdqcPAMContext(),
                                          user='root',
                                          group='root',
                                          mode=0o0640)

    def pre_write(self):
        # Always remove?
        apt_purge('libpam-ccreds')
        apt_purge('libpam-cracklib')
        apt_install('libpam-passwdqc')

    def post_write(self):
        """Updates the PAM configuration after the file has been written"""
        try:
            check_output(['pam-auth-update', '--package'])
        except CalledProcessError as e:
            log('Error calling pam-auth-update: %s' % e, level=ERROR)


class Tally2PAMContext(object):

    def __call__(self):
        ctxt = {}
        defaults = utils.get_defaults('os')

        ctxt['auth_lockout_time'] = defaults['auth']['lockout_time']
        ctxt['auth_retries'] = defaults['auth']['retries']

        return ctxt


class Tally2PAM(TemplatedFile):
    """The PAM Audit verifies the linux PAM settings."""
    def __init__(self, path):
        super(Tally2PAM, self).__init__(path=path,
                                        template_dir=TEMPLATES_DIR,
                                        context=Tally2PAMContext(),
                                        user='root',
                                        group='root',
                                        mode=0o0640)

    def pre_write(self):
        # Always remove?
        apt_purge('libpam-ccreds')
        apt_install('libpam-modules')

    def post_write(self):
        """Updates the PAM configuration after the file has been written"""
        try:
            check_output(['pam-auth-update', '--package'])
        except CalledProcessError as e:
            log('Error calling pam-auth-update: %s' % e, level=ERROR)
