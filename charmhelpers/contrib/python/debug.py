#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

__author__ = "Jorge Niedbalski <jorge.niedbalski@canonical.com>"

import atexit
import sys

from charmhelpers.contrib.python.rpdb import Rpdb
from charmhelpers.core.hookenv import (
    open_port,
    close_port,
    ERROR,
    log
)

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
