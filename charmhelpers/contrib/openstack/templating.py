import os

from charmhelpers.core.host import log, apt_install


try:
    from jinja2 import FileSystemLoader, ChoiceLoader, Environment
except ImportError:
    # python-jinja2 may not be installed yet, or we're running unittests.
    FileSystemLoader = ChoiceLoader = Environment = None


class OSConfigException(Exception):
    pass


def get_loader(templates_dir, os_release):
    """
    Create a jinja2.ChoiceLoader containing template dirs up to
    and including os_release.  If directory template directory
    is missing at templates_dir, it will be omitted from the loader.
    templates_dir is added to the bottom of the search list as a base
    loading dir.

    A charm may also ship a templates dir with this module
    and it will be appended to the bottom of the search list, eg:
    hooks/charmhelpers/contrib/openstack/templates.

    :param templates_dir: str: Base template directory containing release
                               sub-directories.
    :param os_release   : str: OpenStack release codename to construct template
                               loader.

    :returns            : jinja2.ChoiceLoader constructed with a list of
                          jinja2.FilesystemLoaders, ordered in descending
                          order by OpenStack release.
    """
    tmpl_dirs = (
        ('essex', os.path.join(templates_dir, 'essex')),
        ('folsom', os.path.join(templates_dir, 'folsom')),
        ('grizzly', os.path.join(templates_dir, 'grizzly')),
        ('havana', os.path.join(templates_dir, 'havana')),
        ('icehouse', os.path.join(templates_dir, 'icehouse')),
    )

    if not os.path.isdir(templates_dir):
        log('Templates directory not found @ %s.' % templates_dir,
            level='ERROR')
        raise OSConfigException

    # the bottom contains tempaltes_dir and possibly a common templates dir
    # shipped with the helper.
    loaders = [FileSystemLoader(templates_dir)]
    helper_templates = os.path.join(os.path.dirname(__file__), 'templates')
    if os.path.isdir(helper_templates):
        loaders.append(FileSystemLoader(helper_templates))

    for rel, tmpl_dir in tmpl_dirs:
        if os.path.isdir(tmpl_dir):
            loaders.insert(0, FileSystemLoader(tmpl_dir))
        if rel == os_release:
            break
    log('Creating choice loader with dirs: %s' %
        [l.searchpath for l in loaders], level='INFO')
    return ChoiceLoader(loaders)


class OSConfigTemplate(object):
    def __init__(self, config_file, contexts):
        self.config_file = config_file

        if hasattr(contexts, '__call__'):
            self.contexts = [contexts]
        else:
            self.contexts = contexts

        self._complete_contexts = []

    def context(self):
        ctxt = {}
        for context in self.contexts:
            _ctxt = context()
            if _ctxt:
                ctxt.update(_ctxt)
                # track interfaces for every complete context.
                [self._complete_contexts.append(interface)
                 for interface in context.interfaces
                 if interface not in self._complete_contexts]
        return ctxt

    def complete_contexts(self):
        '''
        Return a list of interfaces that have atisfied contexts.
        '''
        if self._complete_contexts:
            return self._complete_contexts
        self.context()
        return self._complete_contexts


class OSConfigRenderer(object):
    def __init__(self, templates_dir, openstack_release):
        if not os.path.isdir(templates_dir):
            log('Could not locate templates dir %s' % templates_dir,
                level='ERROR')
            raise OSConfigException

        self.templates_dir = templates_dir
        self.openstack_release = openstack_release
        self.templates = {}
        self._tmpl_env = None

        if None in [Environment, ChoiceLoader, FileSystemLoader]:
            # if this code is running, the object is created pre-install hook.
            # jinja2 shouldn't get touched until the module is reloaded on next
            # hook execution, with proper jinja2 bits successfully imported.
            apt_install('python-jinja2')

    def register(self, config_file, contexts):
        self.templates[config_file] = OSConfigTemplate(config_file=config_file,
                                                       contexts=contexts)
        log('Registered config file: %s' % config_file, level='INFO')

    def _get_tmpl_env(self):
        if not self._tmpl_env:
            loader = get_loader(self.templates_dir, self.openstack_release)
            self._tmpl_env = Environment(loader=loader)

    def _get_template(self, template):
        self._get_tmpl_env()
        template = self._tmpl_env.get_template(template)
        log('Loaded template from %s' % template.filename, level='INFO')
        return template

    def render(self, config_file):
        if config_file not in self.templates:
            log('Config not registered: %s' % config_file, level='ERROR')
            raise OSConfigException
        ctxt = self.templates[config_file].context()
        _tmpl = os.path.basename(config_file)
        log('Rendering from template: %s' % _tmpl, level='INFO')
        template = self._get_template(_tmpl)
        return template.render(ctxt)

    def write(self, config_file):
        if config_file not in self.templates:
            log('Config not registered: %s' % config_file, level='ERROR')
            raise OSConfigException
        with open(config_file, 'wb') as out:
            out.write(self.render(config_file))
        log('Wrote template %s.' % config_file, level='INFO')

    def write_all(self):
        [self.write(k) for k in self.templates.iterkeys()]

    def set_release(self, openstack_release):
        """
        Resets the template environment and generates a new template loader
        based on a the new openstack release.
        """
        self._tmpl_env = None
        self.openstack_release = openstack_release
        self._get_tmpl_env()

    def complete_contexts(self):
        '''
        Returns a list of context interfaces that yield a complete context.
        '''
        interfaces = []
        [interfaces.extend(i.complete_contexts())
         for i in self.templates.itervalues()]
        return interfaces
