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

from charmhelpers.core.hookenv import ERROR
from charmhelpers.core.hookenv import log

from charmhelpers.contrib.hardening.base_check import BaseFileCheck
# from charmhelpers.contrib.hardening.base_check import FilePermissionCheck

from subprocess import CalledProcessError
from subprocess import check_output
from traceback import format_exc


class NoWritePermsForPathFolders(BaseFileCheck):
    """Checks that folders on $PATH is not writeable.

    Checks that folders on the $PATH variable is not writeable.
    """
    def __init__(self, *args, **kwargs):
        # TODO(wolsen) Append user-driven paths to these restricted paths.
        paths = ['/usr/local/sbin',
                 '/usr/local/bin',
                 '/usr/sbin',
                 '/usr/bin',
                 '/bin']
        super(NoWritePermsForPathFolders, self).__init__(paths=paths,
                                                         *args, **kwargs)

    def is_compliant(self, path):
        try:
            output = check_output(['find', path, '-perm', '-go+w',
                                   '-type', 'f']).strip()

            # The find above will find any files which have permission sets
            # which allow too broad of write access. As such, the path is
            # compliant if there is no output.
            if output:
                return False
            else:
                return True
        except CalledProcessError as e:
            log('Error occurred checking write permissions for %s. '
                'Error information is: command %s failed with returncode '
                '%d and output %s.\n%s' % (path, e.cmd, e.returncode, e.output,
                                           format_exc(e)), level=ERROR)
            # TODO(wolsen) not sure if we can safely assume that the file
            # shouldn't be modified, however this will prevent the code from
            # continually looping on the failure.
            return True

    def become_compliant(self, path):
        try:
            check_output(['chmod', 'go-w', '-R', path])
        except CalledProcessError as e:
            log('Error occurred removing writeable permissions for %s. '
                'Error information is: command %s failed with returncode '
                '%d and output %s.\n%s' % (path, e.cmd, e.returncode, e.output,
                                           format_exc(e)), level=ERROR)

# TODO(wolsen) need to clearly feel for how we're going to include these
# modules so that they are run properly. There's various ways, but I do think
# we want to have the ability to disable or enable some of them. Dynamic
# loading provides some advantages and has some disadvantages/risks. I think it
# might look something like the following:
#
# register_checks(
#     # Check no permissions to write and modify files in folders that
#     # exist on the standard $PATH.
#     NoWritePermsForPathFolders(),
#
#     # Make sure that only the root user can read/write the shadow file
#     FilePermissionCheck('/etc/shadow', 'root', 'root', 0o600),
#
#     # Make sure that only the root user can access the su file,
#     FilePermissionCheck('/bin/su', 'root', 'root', 0o600,
#                         unless=config('security.users.allow.change_user')),
# )
