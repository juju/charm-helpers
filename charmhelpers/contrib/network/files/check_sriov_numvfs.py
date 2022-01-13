#!/usr/bin/env python3
"""
Check to verify the number of virtual functions (VFs) active on network
interfaces. Based on /sys/class/net/<interface>/device/sriov_numvfs and
/sys/class/net/<interface>/device/sriov_totalvfs.

    usage: check_sriov_numvfs.py [-h] sriov_numvfs [sriov_numvfs ...]

    Check sriov numvfs configuration

    positional arguments:
    sriov_numvfs  format: <interface>:<numvfs>

For each interfaces:numvfs pair given it verifies that:
    1. VFs are enabled
    2. VFs are configured are the same as specified in the check parameter
    3. VFs configured do not exceed the maximum available on the interface

Example: ./check_sriov_numvfs.py ens3f0:32 ens3f1:32 ens6f0:32 ens6f1:32
"""

import argparse
import os.path
import sys


DEVICE_TEMPLATE = "/sys/class/net/{0}"
SRIOV_NUMVFS_TEMPLATE = "/sys/class/net/{0}/device/sriov_numvfs"
SRIOV_TOTALVFS_TEMPLATE = "/sys/class/net/{0}/device/sriov_totalvfs"


def get_interface_setting(file):
    """ Return the value content of a setting file as int """
    with open(file) as f:
        value = f.read()
    return int(value)


def check_interface_numvfs(iface, numvfs):
    """ Check SRIOV numvfs config """
    sriov_numvfs_path = SRIOV_NUMVFS_TEMPLATE.format(iface)
    sriov_totalvfs_path = SRIOV_TOTALVFS_TEMPLATE.format(iface)
    msg = []
    if os.path.exists(DEVICE_TEMPLATE.format(iface)):
        if (not os.path.exists(sriov_totalvfs_path) or
                not os.path.exists(sriov_numvfs_path)):
            msg.append("{}: VFs are disabled or not-available".format(iface))
        else:
            sriov_numvfs = get_interface_setting(sriov_numvfs_path)
            sriov_totalvfs = get_interface_setting(sriov_totalvfs_path)
            if numvfs != sriov_numvfs:
                msg.append(
                    "{}: Number of VFs on interface ({}) does not match check ({})"
                    .format(iface, sriov_numvfs, numvfs)
                )
            if numvfs > sriov_totalvfs:
                msg.append(
                    "{}: Maximum number of VFs available on interface ({}) is lower than the check ({})"
                    .format(iface, sriov_totalvfs, numvfs)
                )
    return msg


def parse_sriov_numvfs(device_numvfs):
    """ Parse parameters and check format """
    msg = "parameter format must be '<interface>:<numvfs>', e.g. ens3f0:32, given; {}".format(device_numvfs)
    assert device_numvfs != '', msg
    parts = device_numvfs.split(':')
    assert len(parts) == 2, msg
    assert len(parts[0]) > 0, msg
    assert int(parts[1]) > 0, msg
    iface = str(device_numvfs.split(':')[0])
    numvfs = int(device_numvfs.split(':')[1])
    return (iface, numvfs)


def parse_args():
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Check sriov numvfs configuration")
    parser.add_argument("sriov_numvfs", nargs='+', help="format: <interface>:<numvfs>")
    args = parser.parse_args()
    return args


def main():
    """Parse args and check the sriov numvfs."""
    args = parse_args()
    error_msg = []

    for device_numvfs in args.sriov_numvfs:
        iface, numvfs = parse_sriov_numvfs(device_numvfs)
        error_msg += check_interface_numvfs(iface, numvfs)
    if error_msg:
        print("CRITICAL: {} problems detected\n".format(len(error_msg)) + "\n".join(error_msg))
        sys.exit(2)

    print("OK: sriov_numvfs set to " + ", ".join(args.sriov_numvfs))


if __name__ == "__main__":
    main()
