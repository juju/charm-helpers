import importlib
from yaml import safe_load
from subprocess import check_call
from urlparse import (
    urlparse,
    urlunparse,
)

from charmhelpers.core.hookenv import (
    config,
    log,
)


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
    charm_config = config()
    sources = safe_load(charm_config[sources_var])
    keys = safe_load(charm_config[keys_var])
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

# The order of this list is very important. Handlers should be listed in from
# least- to most-specific URL matching.
FETCH_HANDLERS = (
    'charmhelpers.fetch.archive.UrlArchiveFetchHandler',
)


class UnhandledSource(Exception):
    pass


def install_remote(source):
    """
    Install a file tree from a remote source

    The specified source should be a url of the form:
        scheme://[host]/path[#[option=value][&...]]

    Schemes supported are based on this modules submodules
    Options supported are submodule-specific"""
    # We ONLY check for True here because can_handle may return a string
    # explaining why it can't handle a given source.
    handlers = [h for h in plugins() if h.can_handle(source) is True]
    for handler in handlers:
        try:
            installed_to = handler.install(source)
        except UnhandledSource:
            pass
    if not installed_to:
        raise UnhandledSource("No handler found for source {}".format(source))
    return installed_to


def install_from_config(config_var_name):
    charm_config = config()
    source = charm_config[config_var_name]
    return install_remote(source)


class BaseFetchHandler(object):
    """Base class for FetchHandler implementations in fetch plugins"""
    def can_handle(self, source):
        """Returns True if the source can be handled. Otherwise returns
        a string explaining why it cannot"""
        return "Wrong source type"

    def install(self, source):
        """Try to download and unpack the source. Return the path to the
        unpacked files or raise UnhandledSource."""
        raise UnhandledSource("Wrong source type {}".format(source))

    def parse_url(self, url):
        return urlparse(url)

    def base_url(self, url):
        """Return url without querystring or fragment"""
        parts = list(self.parse_url(url))
        parts[4:] = ['' for i in parts[4:]]
        return urlunparse(parts)


def plugins(fetch_handlers=None):
    if not fetch_handlers:
        fetch_handlers = FETCH_HANDLERS
    plugin_list = []
    for handler_name in fetch_handlers:
        package, classname = handler_name.rsplit('.', 1)
        try:
            handler_class = getattr(importlib.import_module(package), classname)
            plugin_list.append(handler_class())
        except (ImportError, AttributeError):
            # Skip missing plugins so that they can be ommitted from
            # installation if desired
            log("FetchHandler {} not found, skipping plugin".format(handler_name))
    return plugin_list
