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
import grp
import hashlib
import os
import pwd

from subprocess import CalledProcessError
from subprocess import check_output
from traceback import format_exc

from six import string_types

from stat import S_ISGID
from stat import S_ISUID

from charmhelpers.core.hookenv import DEBUG
from charmhelpers.core.hookenv import ERROR
from charmhelpers.core.hookenv import INFO
from charmhelpers.core.hookenv import log

from charmhelpers.contrib.hardening.audits import BaseAudit
from charmhelpers.contrib.hardening.templating import HardeningConfigRenderer


class BaseFileAudit(BaseAudit):
    """Implements base file audits."""

    def __init__(self, paths, *args, **kwargs):
        super(BaseFileAudit, self).__init__(*args, **kwargs)
        if isinstance(paths, string_types) or not hasattr(paths, '__iter__'):
            self.paths = [paths]
        else:
            self.paths = paths

    def ensure_compliance(self):
        for p in self.paths:
            # Skip any paths which do not exist.
            if not os.path.exists(p):
                continue

            # Skip any paths which are compliant.
            if self.is_compliant(p):
                continue

            log('File %s is not in compliance.' % p, level=DEBUG)
            if self._take_action():
                self.comply(p)

    def is_compliant(self, path):
        """Audits the path to see if it is compliance.

        :param path: the path to the file that should be checked.
        """
        raise NotImplementedError

    def comply(self, path):
        """Enforces the compliance of a path.

        :param path: the path to the file that should be enforced.
        """
        raise NotImplementedError

    @classmethod
    def _get_stat(cls, path):
        """Returns the Posix st_stat information for the specified file path.

        :param path: the path to get the st_stat information for.
        :returns: an st_stat object for the path or None if the path doesn't
                  exist.
        """
        return os.stat(path)


class FilePermissionAudit(BaseFileAudit):
    """Implements an audit for file permissions and ownership for a user.

    This class implements functionality that ensures that a specific user/group
    will own the file(s) specified and that the permissions specified are
    applied properly to the file.
    """
    def __init__(self, paths, user, group=None, mode=0o600, **kwargs):
        self.user = user
        self.group = group
        self.mode = mode
        super(FilePermissionAudit, self).__init__(paths, user, group, mode,
                                                  **kwargs)

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, name):
        try:
            user = pwd.getpwnam(name)
        except KeyError:
            log('Unknown user %s' % name, level=ERROR)
            user = None
        self._user = user

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, name):
        try:
            group = None
            if name:
                group = grp.getgrnam(name)
            elif self.user is not None:
                group = grp.getgrgid(self.user.pw_gid)
        except KeyError:
            log('Unknown group %s' % name, level=ERROR)
        self._group = group

    def is_compliant(self, path):
        """Checks if the path is in compliance.

        Used to determine if the path specified meets the necessary
        requirements to be in compliance with the check itself.

        :param path: the file path to check
        :returns: True if the path is compliant, False otherwise.
        """
        stat = self._get_stat(path)
        user = self.user
        group = self.group

        compliant = True
        if stat.st_uid != user.pw_uid or stat.st_gid != group.gr_gid:
            log('File %s is not owned by %s:%s.' % (path, user.pw_name,
                                                    group.gr_name),
                level=INFO)
            compliant = False

        # POSIX refers to the st_mode bits as corresponding to both the
        # file type and file permission bits, where the least significant 12
        # bits (o7777) are the suid (11), guid (10), sticky bits (9), and the
        # file permission bits (8-0)
        perms = stat.st_mode & 0o7777
        if perms != self.mode:
            log('File %s has incorrect permissions, currently set to %s' %
                (path, oct(stat.st_mode & 0o7777)), level=INFO)
            compliant = False

        return compliant

    def comply(self, path):
        """Issues a chown and chmod to the file paths specified."""
        os.chown(path, self.user.pw_uid, self.group.gr_gid)
        os.chmod(path, self.mode)


class DirectoryPermissionAudit(FilePermissionAudit):
    """Performs a permission check for the  specified directory path."""

    def __init__(self, paths, user, group=None, mode=0o600, **kwargs):
        super(DirectoryPermissionAudit, self).__init__(paths, user, group,
                                                       mode, **kwargs)

    def is_compliant(self, path):
        """Checks if the directory is compliant.

        Used to determine if the path specified and all of its children
        directories are in compliance with the check itself.

        :param path: the directory path to check
        :returns: True if the directory tree is compliant, False otherewise.
        """
        if not os.path.isdir(path):
            log('Path specified %s is not a directory.' % path, level=ERROR)
            raise ValueError("%s is not a directory." % path)

        compliant = True
        for root, dirs, _ in os.walk(path):
            if len(dirs) > 0:
                continue

            if not super(DirectoryPermissionAudit, self).is_compliant(root):
                compliant = False
                continue

        return compliant

    def comply(self, path):
        for root, dirs, _ in os.walk(path):
            if len(dirs) > 0:
                super(DirectoryPermissionAudit, self).comply(root)


class ReadOnlyAudit(BaseFileAudit):
    """Audits that files and folders are read only."""
    def __init__(self, paths, *args, **kwargs):
        super(ReadOnlyAudit, self).__init__(paths=paths, *args, **kwargs)

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

    def comply(self, path):
        try:
            check_output(['chmod', 'go-w', '-R', path])
        except CalledProcessError as e:
            log('Error occurred removing writeable permissions for %s. '
                'Error information is: command %s failed with returncode '
                '%d and output %s.\n%s' % (path, e.cmd, e.returncode, e.output,
                                           format_exc(e)), level=ERROR)


class NoSUIDGUIDAudit(BaseFileAudit):
    """Audits that specified files do not have SUID/GUID bits set."""
    def __init__(self, paths, *args, **kwargs):
        super(NoSUIDGUIDAudit, self).__init__(paths=paths, *args, **kwargs)

    def is_compliant(self, path):
        stat = self._get_stat(path)
        if (stat.st_mode & (S_ISGID | S_ISUID)) != 0:
            return False
        else:
            return True

    def comply(self, path):
        try:
            log('Removing suid/guid from %s.' % path)
            check_output(['chmod', '-s', path])
        except CalledProcessError as e:
            log('Error occurred removing suid/sgid from %s.'
                'Error information is: command %s failed with returncode '
                '%d and output %s.\n%s' % (path, e.cmd, e.returncode, e.output,
                                           format_exc(e)), level=ERROR)


class TemplatedFileAudit(BaseFileAudit):
    """The TemplatedFileAudit audits the contents of a templated file.

    This audit renders a file from a template, sets the appropriate file
    permissions, then generates a hashsum with which to check the content
    changed.
    """
    def __init__(self, path, context, user, group, mode, **kwargs):
        self.context = context
        self.user = user
        self.group = group
        self.mode = mode
        if path not in HardeningConfigRenderer.templates['os']:
            render_context = {
                'contexts': [context],
                'permissions': [(path, user, group, mode)],
            }
            HardeningConfigRenderer.register('os', path, render_context)
        super(TemplatedFileAudit, self).__init__(paths=path, **kwargs)

    def is_compliant(self, path):
        """Determines if the templated file is compliant.

        A templated file is only compliant if it has not changed (as
        determined by its sha256 hashsum) AND its file permissions are set
        appropriately.

        :param path: the path to check compliance.
        """
        same_content = self.contents_match(path)
        same_permissions = self.permissions_match(path)

        if same_content and same_permissions:
            return True
        else:
            return False

    def comply(self, path):
        """Ensures the contents and the permissions of the file.

        :param path: the path to correct
        """
        # It should be as simple as this:
        #HardeningConfigRenderer.render(path)
        self.post_hooks()
        pass

    def post_hooks(self):
        """Invoked after templates have been rendered."""
        pass

    def contents_match(self, path):
        """Determines if the file content is the same.

        This is determined by comparing hashsum of the file contents and
        the saved hashsum. If there is no hashsum, then the content cannot
        be sure to be the same so treat them as if they are not the same.
        Otherwise, return True if the hashsums are the same, False if they
        are not the same.

        :param path: the file to check.
        """
        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            BLK_SZ = 65535 # 65K ought to be good enough
            buf = f.read(BLK_SZ)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(BLK_SZ)
        content_cksum = hasher.hexdigest()

        # TODO(wolsen) save the hashsum to the unitdata store.
        return False

    def permissions_match(self, path):
        """Determines if the file owner and permissions match.

        :param path: the path to check.
        """
        _, user, group, perms = self.permissions
        audit = FilePermissionAudit(path, user, group, perms)
        return audit.is_compliant(path)
