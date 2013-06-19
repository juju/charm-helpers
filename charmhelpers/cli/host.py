from . import cmdline
from charmhelpers.core import host


@cmdline.subcommand()
def mounts():
    "List mounts"
    for mount in host.mounts():
        print mount


@cmdline.subcommand_builder('service', description="Control system services")
def service(subparser):
    subparser.add_argument("action", help="The action to perform (start, stop, etc...)")
    subparser.add_argument("service_name", help="Name of the service to control")
    return host.service
