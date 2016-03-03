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

from charmhelpers.contrib.hardening import (
    apache,
    host,
    mysql,
    ssh,
)

from charmhelpers.core.hookenv import (
    log,
    DEBUG,
    INFO,
    WARNING,
    config,
)


def harden(overrides=None):
    """Hardening decorator.

    Calls hardening stacks requested via charm config prior to decorated
    function being called. Note that stacks will be called in the order
    provided in the config.

    @param overrides: optional list of stacks used to override those provided
                      with 'harden' config.
    """
    def _harden_inner1(f):
        log("Hardening function '%s'" % (f.__name__), level=DEBUG)
        def _harden_inner2(*args, **kwargs):
            harden = overrides or (config("harden") or "").split()
            if harden:
                stacks = []
                for stack in harden:
                    if stack == 'ssh':
                        stacks.append(ssh.harden.harden_ssh)
                    elif stack == 'mysql':
                        stacks.append(mysql.harden.harden_mysql)
                    elif stack == 'apache':
                        stacks.append(apache.harden.harden_apache)
                    elif stack == 'host':
                        stacks.append(host.harden.harden_os)
                    else:
                        log("Unknown hardener '%s' - ignoring" % (stack),
                            level=WARNING)

                for hardener in stacks:
                    log("Executing hardener '%s'" % (hardener.__name__))
                    hardener()
            else:
                log("No hardening applied to '%s'" % (f.__name__), level=INFO)    

            return f(*args, **kwargs)
        return _harden_inner2

    return _harden_inner1
