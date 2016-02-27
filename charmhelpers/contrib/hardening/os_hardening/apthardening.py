import apt
import subprocess

from charmhelpers.core.hookenv import (
    log,
    DEBUG,
    INFO,
)
from charmhelpers.contrib.hardening import (
    utils,
)


def is_virtual(pkg):
    return pkg.has_provides and not pkg.has_versions


def delete_package(pkg):
    if is_virtual(pkg):
        log("Package '%s' appears to be virtual - purging provides" %
            (pkg.name), level=DEBUG)
        for _p in pkg.provides_list:
            delete_package(_p[2].parent_pkg)
    elif not pkg.current_ver:
        log("Package '%s' not installed" % (pkg.name), level=DEBUG)
        return

    log("Purging package '%s'" % (pkg.name), level=DEBUG)
    cmd = ['apt-get', '--assume-yes', 'purge', pkg.name]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        log("Failed to delete package '%s'" % (pkg.name), level=INFO)


def apt_harden():
    log("Hardening packages", level=INFO)
    defaults = utils.get_defaults('os')

    clean = defaults.get('security_packages_clean')
    security_packages = defaults.get('security_packages_list', [])
    cache = apt.Cache()
    cache.update()

    if clean:
        for pkg in security_packages:
            if pkg in cache:
                delete_package(cache[pkg])
                cache.update()
