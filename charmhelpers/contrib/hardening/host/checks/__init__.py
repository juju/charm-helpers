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

from charmhelpers.contrib.hardening.host.checks import apt
from charmhelpers.contrib.hardening.host.checks import limits
from charmhelpers.contrib.hardening.host.checks import login
from charmhelpers.contrib.hardening.host.checks import minimize_access
from charmhelpers.contrib.hardening.host.checks import pam
from charmhelpers.contrib.hardening.host.checks import profile
from charmhelpers.contrib.hardening.host.checks import securetty
from charmhelpers.contrib.hardening.host.checks import suid_sgid
from charmhelpers.contrib.hardening.host.checks import sysctl


def run_os_checks():
    log("Starting OS hardening checks.", level=DEBUG)

    audits = []

    audits.extend(apt.get_audits())
    audits.extend(limits.get_audits())
    audits.extend(login.get_audits())
    audits.extend(minimize_access.get_audits())
    audits.extend(pam.get_audits())
    audits.extend(profile.get_audits())
    audits.extend(securetty.get_audits())
    audits.extend(suid_sgid.get_audits())
    audits.extend(sysctl.get_audits())

    for audit in audits:
        audit.ensure_compliance()

    log("OS hardening checks complete.", level=DEBUG)
