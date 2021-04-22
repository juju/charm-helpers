#!/usr/bin/env python3
# -*- coding: us-ascii -*-
"""Check for issues with NVME hardware devices."""

import argparse
import re
import subprocess
import sys

from nagios_plugin3 import CriticalError, UnknownError, try_check


def parse_ovs_status():
    """Check for errors in 'ovs-vsctl show' output."""
    try:
        cmd = ["/usr/bin/sudo", "/usr/bin/ovs-vsctl", "show"]
        ovs_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise UnknownError(
            "UNKNOWN: Failed to query ovs: {}".format(
                e.output.decode(errors="ignore").rstrip()
            )
        )

    ovs_vsctl_show_errors = []
    ovs_error_re = re.compile(r"^.*error: (?P<message>.+)$", re.I)
    for line in ovs_output.decode(errors="ignore").splitlines():
        m = ovs_error_re.match(line)
        if m:
            ovs_vsctl_show_errors.append(m.group("message"))

    if ovs_vsctl_show_errors:
        numerrs = len(ovs_vsctl_show_errors)
        raise CriticalError(
            "CRITICAL: Found {} error(s) in ovs-vsctl show: "
            "{}".format(numerrs, ", ".join(ovs_vsctl_show_errors))
        )

    print("OK: no errors found in openvswitch")


def parse_args(argv=None):
    """Process CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="check_openvswitch",
        description=(
            "this program checks openvswitch status and outputs an "
            "appropriate Nagios status line"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    return parser.parse_args(argv)


def main(argv):
    """Define main subroutine."""
    parse_args(argv)
    try_check(parse_ovs_status)


if __name__ == "__main__":
    main(sys.argv[1:])
