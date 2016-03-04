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
from charmhelpers.contrib.hardening.audits.file import TemplatedFile
from charmhelpers.contrib.hardening.host import TEMPLATES_DIR
from charmhelpers.contrib.hardening import utils


def get_audits():
    """Returns the audits used to verify the login.defs file"""
    audits = [TemplatedFile('/etc/login.defs', LoginContext(),
                            template_dir=TEMPLATES_DIR,
                            user='root', group='root', mode=0o0444)]
    return audits


class LoginContext(object):

    def __call__(self):
        defaults = utils.get_defaults('os')
        ctxt = {
            'additional_user_paths': defaults.get('env_extra_user_paths'),
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
            'allow_login_without_home': defaults.get('auth_allow_homeless')
        }

        return ctxt
