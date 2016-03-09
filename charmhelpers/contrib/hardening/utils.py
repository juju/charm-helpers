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

import glob
import grp
import os
import pwd
import yaml

from charmhelpers.core.hookenv import (
    log,
    DEBUG,
    INFO,
    WARNING,
    ERROR,
)


# Global settings cache
__SETTINGS__ = None


def get_defaults(stack):
    default = os.path.join(os.path.dirname(__file__),
                           'defaults/%s.yaml' % (stack))
    return yaml.safe_load(open(default))


def get_schema(stack):
    schema = os.path.join(os.path.dirname(__file__),
                          'defaults/%s.yaml.schema' % (stack))
    return yaml.safe_load(open(schema))


def get_user_provided_overrides(stack):
    overrides = os.path.join(os.environ['JUJU_CHARM_DIR'],
                             'hardening.yaml')
    if os.path.exists(overrides):
        log("Found hardening config overrides file '%s' in charm root dir" %
            (overrides), level=DEBUG)
        settings = yaml.safe_load(open(overrides))
        if settings and settings.get(stack):
            return settings.get(stack)

        log("No '%s' overrides found in '%s'" % (stack, overrides),
            level=DEBUG)
    else:
        log("No hardening config overrides file '%s' found in charm "
            "root dir" % (overrides), level=DEBUG)

    return {}


def apply_overrides(settings, overrides, schema):
    if overrides:
        for k, v in overrides.iteritems():
            if k in schema:
                if schema[k] is None:
                    settings[k] = v
                elif type(schema[k]) is dict:
                    settings[k] = apply_overrides(settings[k], overrides[k],
                                                  schema[k])
                else:
                    raise Exception("Unexpected type found in schema '%s'" %
                                    type(schema[k]), level=ERROR)
            else:
                log("Unknown override key '%s' - ignoring" % (k), level=INFO)

    return settings


def get_settings(stack):
    global __SETTINGS__
    if type(__SETTINGS__) is dict and stack in __SETTINGS__:
        return __SETTINGS__

    schema = get_schema(stack)
    __SETTINGS__ = get_defaults(stack)
    overrides = get_user_provided_overrides(stack)
    __SETTINGS__ = apply_overrides(__SETTINGS__, overrides, schema)
    return __SETTINGS__


def ensure_permissions(path, user, group, permissions, maxdepth=-1):
    """Ensure permissions for path.

    If path is a file, apply to file and return.

    If path is a directory, recursively apply to directory contents and return.

    NOTE: a negative maxdepth e.g. -1 gives infinite recursion.
    """
    if not os.path.exists(path):
        log("File '%s' does not exist - cannot set permissions" % (path),
            level=WARNING)
        return

    _user = pwd.getpwnam(user)
    os.chown(path, _user.pw_uid, grp.getgrnam(group).gr_gid)
    os.chmod(path, permissions)

    if maxdepth == 0:
        log("Max recursion depth reached - skipping further recursion")
        return
    elif maxdepth > 0:
        maxdepth -= 1

    if os.path.isdir(path):
        contents = glob.glob("%s/*" % (path))
        for c in contents:
            ensure_permissions(c, user=user, group=group,
                               permissions=permissions, maxdepth=maxdepth)
