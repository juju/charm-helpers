#!/usr/bin/env python
# -*- coding: utf-8 -*-

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


__author__ = "Jorge Niedbalski <jorge.niedbalski@canonical.com>"

from charmhelpers.fetch import (
    apt_install,
    apt_update,
)

from charmhelpers.core.hookenv import (
    log,
    INFO,
)

try:
    from netifaces import interfaces as network_interfaces
except ImportError:
    apt_install('python-netifaces')
    from netifaces import interfaces as network_interfaces

import os
import re
import subprocess

from charmhelpers.core.kernel import modprobe

REQUIRED_MODULES = (
    "mlx4_ib",
    "mlx4_en",
    "mlx4_core",
    "ib_ipath",
    "ib_mthca",
    "ib_srpt",
    "ib_srp",
    "ib_ucm",
    "ib_isert",
    "ib_iser",
    "ib_ipoib",
    "ib_cm",
    "ib_uverbs"
    "ib_umad",
    "ib_sa",
    "ib_mad",
    "ib_core",
    "ib_addr",
    "rdma_ucm",
)

REQUIRED_PACKAGES = (
    "ibutils",
    "infiniband-diags",
    "ibverbs-utils",
)

IPOIB_DRIVERS = (
    "ib_ipoib",
)

ABI_VERSION_FILE = "/sys/class/infiniband_mad/abi_version"


class DeviceInfo(object):
    pass


def install_packages():
    apt_update()
    apt_install(REQUIRED_PACKAGES, fatal=True)


def load_modules():
    for module in REQUIRED_MODULES:
        modprobe(module, persist=True)


def is_enabled():
    """Check if infiniband is loaded on the system"""
    return os.path.exists(ABI_VERSION_FILE)


def stat():
    """Return full output of ibstat"""
    return subprocess.check_output(["ibstat"])


def devices():
    """Returns a list of IB enabled devices"""
    return subprocess.check_output(['ibstat', '-l']).splitlines()


def device_info(device):
    """Returns a DeviceInfo object with the current device settings"""

    status = subprocess.check_output([
        'ibstat', device, '-s']).splitlines()

    regexes = {
        "CA type: (.*)": "device_type",
        "Number of ports: (.*)": "num_ports",
        "Firmware version: (.*)": "fw_ver",
        "Hardware version: (.*)": "hw_ver",
        "Node GUID: (.*)": "node_guid",
        "System image GUID: (.*)": "sys_guid",
    }

    device = DeviceInfo()

    for line in status:
        for expression, key in regexes.items():
            matches = re.search(expression, line)
            if matches:
                setattr(device, key, matches.group(1))

    return device


def ipoib_interfaces():
    """Return a list of IPOIB capable ethernet interfaces"""
    interfaces = []

    for interface in network_interfaces():
        try:
            driver = re.search('^driver: (.+)$', subprocess.check_output([
                'ethtool', '-i',
                interface]), re.M).group(1)

            if driver in IPOIB_DRIVERS:
                interfaces.append(interface)
        except:
            log("Skipping interface %s" % interface, level=INFO)
            continue

    return interfaces
