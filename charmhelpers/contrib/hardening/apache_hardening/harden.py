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

from charmhelpers.contrib.hardening.apache_hardening.checks import (
    run_apache_checks,
)
from charmhelpers.core.hookenv import (
    log,
    DEBUG,
    INFO,
    config,
)

TEMPLATES = os.path.join(os.path.dirname(__file__), 'templates')


def harden_apache():
    log("Hardening Apache", level=INFO)
    log("Running checks", level=DEBUG)
    run_apache_checks()
    log("Apache hardening complete", level=INFO)


def dec_harden_apache(f):
    if config('harden'):
        harden_apache()

    def _harden_apache(*args, **kwargs):
        return f(*args, **kwargs)

    return _harden_apache


# Run on import
if config('harden'):
    harden_apache()
