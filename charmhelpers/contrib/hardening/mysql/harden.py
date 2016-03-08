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

from charmhelpers.contrib.hardening.mysql.checks import (
    run_mysql_checks,
)
from charmhelpers.core.hookenv import (
    log,
    INFO,
)

TEMPLATES = os.path.join(os.path.dirname(__file__), 'templates')


def harden_mysql():
    log("Hardening MySQL", level=INFO)
    run_mysql_checks()
    log("MySQL hardening complete", level=INFO)
