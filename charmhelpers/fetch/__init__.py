from yaml import safe_load
from charmhelpers.core.hookenv import config
from charmhelpers.core.host import (
    apt_install, apt_update, filter_installed_packages
)
import subprocess

CLOUD_ARCHIVE = 'deb http://ubuntu-cloud.archive.canonical.com/ubuntu {} main'


def add_source(source, key=None):
    if ((source.startswith('ppa:') or
         source.startswith('http:'))):
        subprocess.check_call(['add-apt-repository', source])
    elif source.startswith('cloud:'):
        apt_install(filter_installed_packages(['ubuntu-cloud-keyring']),
                    fatal=True)
        pocket = source.split(':')[-1]
        with open('/etc/apt/sources.list.d/cloud-archive.list', 'w') as apt:
            apt.write(CLOUD_ARCHIVE.format(pocket))
    if key:
        subprocess.check_call(['apt-key', 'import', key])


class SourceConfigError(Exception):
    pass


def configure_sources(update=False,
                      sources_var='install_sources',
                      keys_var='install_keys'):
    """
    Configure multiple sources from charm configuration

    Example config:
        install_sources:
          - "ppa:foo"
          - "http://example.com/repo precise main"
        install_keys:
          - null
          - "a1b2c3d4"

    Note that 'null' (a.k.a. None) should not be quoted.
    """
    sources = safe_load(config(sources_var))
    keys = safe_load(config(keys_var))
    if isinstance(sources, basestring) and isinstance(keys, basestring):
        add_source(sources, keys)
    else:
        if not len(sources) == len(keys):
            msg = 'Install sources and keys lists are different lengths'
            raise SourceConfigError(msg)
        for src_num in range(len(sources)):
            add_source(sources[src_num], keys[src_num])
    if update:
        apt_update(fatal=True)
