import subprocess
import os

from charmhelpers.core.strutils import BasicStringComparator


class CompareHostReleases(BasicStringComparator):
    """Provide comparisons of Host releases.

    Use in the form of

    if CompareHostReleases(release) > 'trusty':
        # do something with mitaka
    """

    def __init__(self, item):
        raise NotImplementedError(
            "CompareHostReleases() is not implemented for CentOS")


def service_available(service_name):
    # """Determine whether a system service is available."""
    if os.path.isdir('/run/systemd/system'):
        cmd = ['systemctl', 'is-enabled', service_name]
    else:
        cmd = ['service', service_name, 'is-enabled']
    return subprocess.call(cmd) == 0


def add_new_group(group_name, system_group=False, gid=None):
    cmd = ['groupadd']
    if gid:
        cmd.extend(['--gid', str(gid)])
    if system_group:
        cmd.append('-r')
    cmd.append(group_name)
    subprocess.check_call(cmd)


def lsb_release():
    """Return /etc/os-release in a dict."""
    d = {}
    with open('/etc/os-release', 'r') as lsb:
        for l in lsb:
            s = l.split('=')
            if len(s) != 2:
                continue
            d[s[0].strip()] = s[1].strip()
    return d


def cmp_pkgrevno(package, revno, pkgcache=None):
    """Compare supplied revno with the revno of the installed package.

    *  1 => Installed revno is greater than supplied arg
    *  0 => Installed revno is the same as supplied arg
    * -1 => Installed revno is less than supplied arg

    This function imports YumBase function if the pkgcache argument
    is None.
    """
    if not pkgcache:
        pkgcache = dict()
        rpm_cmd = ['rpm', '-q', package, '--qf', '%{VERSION}']
        rpm_process = subprocess.Popen(rpm_cmd, universal_newlines=True, stdout=subprocess.PIPE)
        (rpm_out, rpm_err) = rpm_process.communicate()
        # wait() returns 1 if 'package' isn't installed
        if rpm_process.wait() == 0:
            # pick up version number
            pkgcache[package] = rpm_out
    # Will throw KeyError if 'package' isn't installed, as before
    pkg = pkgcache[package]
    if pkg > revno:
        return 1
    if pkg < revno:
        return -1
    return 0
