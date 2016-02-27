import apt

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


def delete_package(pkg, manager):
    if is_virtual(pkg):
        log("Package '%s' appears to be virtual - purging provides" %
            (pkg.name), level=DEBUG)
        for _p in pkg.provides_list:
            delete_package(_p[2].parent_pkg, manager)
    elif not pkg.current_ver:
        log("Package '%s' not installed" % (pkg.name), level=DEBUG)
        return

    log("Purging package '%s'" % (pkg.name), level=DEBUG)
    manager.remove(pkg.name, purge=True)


def apt_harden():
    log("Hardening packages", level=INFO)
    defaults = utils.get_defaults('os')
    apt.apt_pkg.init()

    clean = defaults.get('security_packages_clean')
    security_packages = defaults.get('security_packages_list', [])
    cache = apt.apt_pkg.Cache()

    if clean:
        pm = apt.apt_pkg.PackageManager(apt.apt_pkg.DepCache(cache))
        for pkg in security_packages:
            if pkg in cache:
                delete_package(cache[pkg], pm)
