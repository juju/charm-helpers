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
import pwd

from charmhelpers.core.hookenv import (
    log,
    WARNING,
)


def ensure_permissions(filename, user, permissions):
    if not os.path.exists(filename):
        log("File '%s' does not exist - cannot set permissions" % (filename),
            level=WARNING)
        return

    user = pwd.getpwnam(user)
    os.chown(filename, user.pw_uid, user.pw_gid)
    os.chmod(filename, permissions)
