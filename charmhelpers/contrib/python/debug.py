#!/usr/bin/env python
# coding: utf-8

# Copyright 2014-2015 Canonical Limited.
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

from __future__ import print_function

import atexit
import sys

from charmhelpers.contrib.python.rpdb import Rpdb
from charmhelpers.core.hookenv import (
    open_port,
    close_port,
    ERROR,
    log
)

__author__ = "Jorge Niedbalski <jorge.niedbalski@canonical.com>"

DEFAULT_ADDR = "0.0.0.0"
DEFAULT_PORT = 4444


def _error(message):
    log(message, level=ERROR)


def set_trace(addr=DEFAULT_ADDR, port=DEFAULT_PORT):
    """
    Set a trace point using the remote debugger
    """
    atexit.register(close_port, port)
    try:
        log("Starting a remote python debugger session on %s:%s" % (addr,
                                                                    port))
        open_port(port)
        debugger = Rpdb(addr=addr, port=port)
        debugger.set_trace(sys._getframe().f_back)
    except:
        _error("Cannot start a remote debug session on %s:%s" % (addr,
                                                                 port))
