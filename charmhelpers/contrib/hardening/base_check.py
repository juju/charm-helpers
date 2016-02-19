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
import os
import pwd

from charmhelpers.core.hookenv import ERROR
from charmhelpers.core.hookenv import INFO
from charmhelpers.core.hookenv import log


class BaseCheck(object):  # NO-QA
    """Base class for hardening checks.

    The lifecycle of a hardening check is to first check to see if the system
    is in compliance for the specified check. If it is not in compliance, the
    check method will return a value which will be supplied to the.
    """
    def __init__(self, *args, **kwargs):
        self.unless = kwargs['unless'] if 'unless' in kwargs else None
        super(BaseCheck, self).__init__(*args, **kwargs)

    def ensure_compliance(self):
        """Checks to see if the current hardening check is in compliance or not.

        If the check that is performed is not in compliance, then an exception
        should be raised.
        """
        pass

    def _take_action(self):
        """Determines whether to perform the action or not.

        Checks whether or not an action should be taken. This is determined by
        the truthy value for the unless parameter. If unless is a callback
        method, it will be invoked with no parameters in order to determine
        whether or not the action should be taken. Otherwise, the truthy value
        of the unless attribute will determine if the action should be
        performed.
        """
        # Do the action if there isn't an unless override.
        if self.unless is None:
            return True

        # Invoke the callback if there is one.
        if hasattr(self.unless, '__call__'):
            results = self.unless()
            if results:
                return False
            else:
                return True

        if self.unless:
            return False
        else:
            return True


class BaseFileCheck(BaseCheck):
    """Implements base file checks."""

    def __init__(self, paths, *args, **kwargs):
        super(BaseFileCheck, self).__init__(*args, **kwargs)
        self.paths = paths if hasattr(paths, '__iter__') else [paths]

    def ensure_compliance(self):
        for p in self.paths:
            # Skip any paths which do not exist.
            if not os.path.exists(p):
                continue

            # Skip any paths which are compliant.
            if self.is_compliant(p):
                continue

            log('File %s is not in compliance.' % p, level=INFO)
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

    def _get_stat(self, path):
        """Returns the Posix st_stat information for the specified file path.

        :param path: the path to get the st_stat information for.
        :return: an st_stat object for the path or None if the path doesn't
                 exist.
        """
        return os.stat(path)


class FilePermissionCheck(BaseFileCheck):
    """Implements a check for file permissions and ownership for a user.

    This class implements functionality that ensures that a specific user/group
    will own the file(s) specified and that the permissions specified are
    applied properly to the file.
    """
    def __init__(self, paths, user, group=None, mode=0o600, **kwargs):
        self.paths = paths if hasattr(paths, '__iter__') else [paths]
        self.user = user
        self.group = group
        self.mode = mode
        super(FilePermissionCheck, self).__init__(**kwargs)

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
        :return: True if the path is compliant, False otherwise.
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
        # file type and file permission bits, where the least significant 9
        # bits (0777) are the 'file permission bits'
        perms = stat.st_mode & 0o777
        if perms != self.mode:
            log('File %s has incorrect permissions, currently set to %s' %
                (path, oct(perms)), level=INFO)
            compliant = False

        return compliant

    def comply(self, path):
        """Issues a chown and chmod to the file paths specified."""
        os.chown(path, self.user.pw_uid, self.group.gr_gid)
        os.chmod(path, self.mode)


class DirectoryPermissionCheck(FilePermissionCheck):
    """Performs a permission check for the  specified directory path.

    """
    def __init__(self, *args, **kwargs):
        super(DirectoryPermissionCheck, self).__init__(self, *args, **kwargs)

    def is_compliant(self, path):
        """Checks if the directory is compliant.

        Used to determine if the path specified and all of its children
        directories are in compliance with the check itself.

        :param path: the directory path to check
        :param: True if the directory tree is compliant, False otherewise.
        """
        if not os.path.isdir(path):
            log('Path specified %s is not a directory.' % path, level=ERROR)
            raise ValueError("%s is not a directory." % path)

        compliant = True
        for root, dirs, files in os.walk(path):
            if len(dirs) > 0:
                continue
            if super(DirectoryPermissionCheck, self).is_compliant(root):
                compliant = False
                continue

        return compliant

    def comply(self, path):
        for root, dirs, files in os.walk(path):
            if len(dirs) > 0:
                super(DirectoryPermissionCheck, self).comply(root)
