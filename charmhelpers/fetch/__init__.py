from yaml import safe_load
from core.hookenv import config_get
from subprocess import check_call


def add_source(source, key=None):
    if ((source.startswith('ppa:') or
         source.startswith('cloud:') or
         source.startswith('http:'))):
        check_call('add-apt-repository', source)
    if key:
        check_call('apt-key', 'import', key)


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
    sources = safe_load(config_get(sources_var))
    keys = safe_load(config_get(keys_var))
    if isinstance(sources, basestring) and isinstance(keys, basestring):
        add_source(sources, keys)
    else:
        if not len(sources) == len(keys):
            msg = 'Install sources and keys lists are different lengths'
            raise SourceConfigError(msg)
        for src_num in range(len(sources)):
            add_source(sources[src_num], sources[src_num])
    if update:
        check_call(('apt-get', 'update'))
