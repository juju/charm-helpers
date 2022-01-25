#!/usr/bin/env python3
"""Check for known error statuses in OVS.

This script currently checks through the Interface table in OVSDB
for errors. The script is named generically to allow for expanded
status checks in the future.
"""

import argparse
import json
import subprocess
import sys

# This depends on nagios_plugin3 being installed by charm-nrpe
from nagios_plugin3 import CriticalError, UnknownError, try_check


def parse_ovs_interface_errors():
    """Check for errors in OVSDB Interface table."""
    try:
        cmd = [
            "/usr/bin/sudo",
            "/usr/bin/ovs-vsctl",
            "--format=json",
            "list",
            "Interface",
        ]
        ovs_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise UnknownError(
            "UNKNOWN: OVS command '{}' failed.  Output: {}".format(
                " ".join(cmd), e.output.decode(errors="ignore").rstrip(),
            )
        )
    ovs_interfaces = json.loads(ovs_output.decode(errors="ignore"))
    ovs_interface_errors = []
    for i in ovs_interfaces["data"]:
        # OVSDB internal data is formatted per RFC 7047 5.1
        iface = dict(zip(ovs_interfaces["headings"], i))
        error = iface["error"]
        if isinstance(error, list) and len(error) == 2 and error[0] == "set":
            # deserialize the set data into csv string elements
            error = ",".join(error[1])
        if error:
            ovs_interface_errors.append(
                "Error on iface {}: {}".format(iface["name"], error)
            )

    if ovs_interface_errors:
        raise CriticalError(
            "CRITICAL: Found {} interface error(s) in OVSDB: "
            "{}".format(len(ovs_interface_errors), ", ".join(ovs_interface_errors))
        )

    print(
        "OK: No errors found across {} interfaces in openvswitch".format(
            len(ovs_interfaces["data"])
        )
    )


def parse_args(argv=None):
    """Process CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="check_openvswitch",
        description=(
            "this program checks openvswitch interface status and outputs "
            "an appropriate Nagios status line"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    return parser.parse_args(argv)


def main(argv):
    """Define main subroutine."""
    parse_args(argv)
    try_check(parse_ovs_interface_errors)


if __name__ == "__main__":
    main(sys.argv[1:])
