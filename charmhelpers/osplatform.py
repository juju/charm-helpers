# -*- coding=utf-8 -*-
try:
    # this is done primarily for convenience; if python 2 support is dropped
    # we can drop this import guard and switch to distro.name()
    from distro import linux_distribution as dist
except ImportError:
    from platform import dist


def get_platform():
    """Return the current OS platform.

    For example: if current os platform is Ubuntu then a string "ubuntu"
    will be returned (which is the name of the module).
    This string is used to decide which platform module should be imported.
    """
    distro_name, _, _ = dist()
    if distro_name.lower() in ("ubuntu", "debian"):
        return "ubuntu"
    elif distro_name.lower() == "centos":
        return distro_name.lower()
    raise RuntimeError("This module is not supported on {}."
                       .format(distro_name))
