import subprocess
import yum

from charmhelpers.core.host import service


def service_available_host(service_name):
    """Determine whether a system service is available."""
    return service('is-enabled', service_name)


def add_group_host(group_name, system_group=False, gid=None):
    cmd = ['groupadd']
    if gid:
        cmd.extend(['--gid', str(gid)])
    if system_group:
        cmd.append('-r')
    cmd.append(group_name)
    subprocess.check_call(cmd)


def lsb_release_host():
    """Return /etc/os-release in a dict."""
    d = {}
    with open('/etc/os-release', 'r') as lsb:
        for l in lsb:
            if len(l.split('=')) != 2:
                continue
            k, v = l.split('=')
            d[k.strip()] = v.strip()
    return d


def cmp_pkgrevno_host(package, revno, pkgcache=None):
    """Compare supplied revno with the revno of the installed package.

    *  1 => Installed revno is greater than supplied arg
    *  0 => Installed revno is the same as supplied arg
    * -1 => Installed revno is less than supplied arg

    This function imports YumBase function if the pkgcache argument
    is None.
    """
    if not pkgcache:
        y = yum.YumBase()
        packages = y.doPackageLists()
        pck = {}
        for i in packages["installed"]:
            pck[i.Name] = i.version
            pkgcache = pck
    pkg = pkgcache[package]
    if pkg > revno:
        return 1
    if pkg < revno:
        return -1
    return 0
