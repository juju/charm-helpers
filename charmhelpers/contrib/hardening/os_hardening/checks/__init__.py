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
from charmhelpers.core.hookenv import DEBUG
from charmhelpers.core.hookenv import log

from charmhelpers.contrib.hardening.os_hardening.checks import apt
from charmhelpers.contrib.hardening.os_hardening.checks import limits
from charmhelpers.contrib.hardening.os_hardening.checks import minimize_access
from charmhelpers.contrib.hardening.os_hardening.checks import suid_guid


def run_os_checks():
    log("Starting OS hardening checks.", level=DEBUG)

    checks = []

    checks.extend(apt.get_audits())
    checks.extend(limits.get_audits())
    checks.extend(minimize_access.get_audits())
    checks.extend(suid_guid.get_audits())

    for check in checks:
        check.ensure_compliance()

    log("OS hardening checks complete.", level=DEBUG)
