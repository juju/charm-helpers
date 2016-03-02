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
import apt
import subprocess

from six import string_types
from charmhelpers.contrib.hardening.audits import BaseAudit

from charmhelpers.core.hookenv import DEBUG
from charmhelpers.core.hookenv import INFO
from charmhelpers.core.hookenv import WARNING
from charmhelpers.core.hookenv import log


class RestrictedPackages(BaseAudit):
    """Class used to audit restricted packages on the system."""

    def __init__(self, pkgs, **kwargs):
        super(RestrictedPackages, self).__init__(**kwargs)
        if isinstance(pkgs, string_types) or not hasattr(pkgs, '__iter__'):
            self.pkgs = [pkgs]
        else:
            self.pkgs = pkgs

    def ensure_compliance(self):
        apt.apt_pkg.init()
        cache = apt.apt_pkg.Cache(apt.progress.base.OpProgress())

        for p in self.pkgs:
            if p not in cache:
                continue

            pkg = cache[p]
            if not self.is_virtual_package(pkg) and not pkg.current_ver:
                log("Package '%s' is not installed." % pkg.name, level=DEBUG)
                continue

            log("Restricted package '%s' is installed" % pkg.name,
                level=WARNING)
            self.delete_package(pkg)

    def delete_package(self, pkg):
        """Deletes the package from the system.

        Deletes the package form the system, properly handling virtual
        packages.
        """
        if self.is_virtual_package(pkg):
            log("Package '%s' appears to be virtual - purging provides" %
                pkg.name, level=DEBUG)
            for _p in pkg.provides_list:
                self.delete_package(_p[2].parent_pkg)
        elif not pkg.current_ver:
            log("Package '%s' not installed" % pkg.name, level=DEBUG)
            return

        log("Purging package '%s'" % pkg.name, level=DEBUG)
        cmd = ['apt-get', '--assume-yes', 'purge', pkg.name]
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError:
            log("Failed to delete package '%s'" % pkg.name, level=INFO)

    def is_virtual_package(self, pkg):
        """Determines if the package is a virtual package or not."""
        return pkg.has_provides and not pkg.has_versions
