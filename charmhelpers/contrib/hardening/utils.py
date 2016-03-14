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


def _get_defaults(section):
    """Load the default config for the provided section.

    :param section: stack section config defaults to lookup.
    :returns: section default config dictionary.
    """
    default = os.path.join(os.path.dirname(__file__),
                           'defaults/%s.yaml' % (section))
    return yaml.safe_load(open(default))


def _get_schema(section):
    """Load the config schema for the provided section.

    NOTE: this schema is intended to have 1-1 relationship with they keys in
    the default config and is used a means to verify valid overrides provided
    by the user.

    :param section: stack section config schema to lookup.
    :returns: section default schema dictionary.
    """
    schema = os.path.join(os.path.dirname(__file__),
                          'defaults/%s.yaml.schema' % (section))
    return yaml.safe_load(open(schema))


def _get_user_provided_overrides(section):
    """Load user-provided config overrides.

    :param section: stack section to lookup in user overrides yaml file.
    :returns: overrides dictionary.
    """
    overrides = os.path.join(os.environ['JUJU_CHARM_DIR'],
                             'hardening.yaml')
    if os.path.exists(overrides):
        log("Found user-provided config overrides file '%s'" %
            (overrides), level=DEBUG)
        settings = yaml.safe_load(open(overrides))
        if settings and settings.get(section):
            log("Applying '%s' overrides" % (section), level=DEBUG)
            return settings.get(section)

        log("No overrides found for '%s'" % (section), level=DEBUG)
    else:
        log("No hardening config overrides file '%s' found in charm "
            "root dir" % (overrides), level=DEBUG)

    return {}


def _apply_overrides(settings, overrides, schema):
    """Get overrides config overlayed onto section defaults.

    :param section: require stack section config.
    :returns: dictionary of section config with user overrides applied.
    """
    if overrides:
        for k, v in overrides.iteritems():
            if k in schema:
                if schema[k] is None:
                    settings[k] = v
                elif type(schema[k]) is dict:
                    settings[k] = _apply_overrides(settings[k], overrides[k],
                                                   schema[k])
                else:
                    raise Exception("Unexpected type found in schema '%s'" %
                                    type(schema[k]), level=ERROR)
            else:
                log("Unknown override key '%s' - ignoring" % (k), level=INFO)

    return settings


def get_settings(section):
    global __SETTINGS__
    if type(__SETTINGS__) is dict and section in __SETTINGS__:
        return __SETTINGS__

    schema = _get_schema(section)
    __SETTINGS__ = _get_defaults(section)
    overrides = _get_user_provided_overrides(section)
    __SETTINGS__ = _apply_overrides(__SETTINGS__, overrides, schema)
    return __SETTINGS__


def ensure_permissions(path, user, group, permissions, maxdepth=-1):
    """Ensure permissions for path.

    If path is a file, apply to file and return. If path is a directory,
    apply recursively (if required) to directory contents and return.

    :param user: user name
    :param group: group name
    :param permissions: octal permissions
    :param maxdepth: maximum recursion depth. A negative maxdepth allows
                     infinite recursion and maxdepth=0 means no recursion.
    :returns: None
    """
    if not os.path.exists(path):
        log("File '%s' does not exist - cannot set permissions" % (path),
            level=WARNING)
        return

    _user = pwd.getpwnam(user)
    os.chown(path, _user.pw_uid, grp.getgrnam(group).gr_gid)
    os.chmod(path, permissions)

    if maxdepth == 0:
        log("Max recursion depth reached - skipping further recursion",
            level=DEBUG)
        return
    elif maxdepth > 0:
        maxdepth -= 1

    if os.path.isdir(path):
        contents = glob.glob("%s/*" % (path))
        for c in contents:
            ensure_permissions(c, user=user, group=group,
                               permissions=permissions, maxdepth=maxdepth)
