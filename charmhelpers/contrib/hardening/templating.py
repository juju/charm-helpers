# Copyright 2016 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

import os
import six
import subprocess

from charmhelpers.fetch import apt_install, apt_update
from charmhelpers.core.hookenv import (
    log,
    ERROR,
    INFO
)
from charmhelpers.contrib.hardening.utils import (
    ensure_permissions,
)

try:
    from jinja2 import FileSystemLoader, Environment
except ImportError:
    apt_update(fatal=True)
    apt_install('python-jinja2', fatal=True)
    from jinja2 import FileSystemLoader, Environment


class HardeningConfigException(Exception):
    pass


class TemplateContext(object):
    """
    SCHEMA:

        {config_file_path:
         {'contexts': [MyContext()],
          'service-actions': [(service, action)],
          'permissions': [(path, user, group, permissions)],
          'posthooks': [(function, args, kwargs)]}
        }
    """
    def __init__(self, target, context):
        self.contexts = context['contexts']
        self.permissions = context.get('permissions')
        self.service_actions = context.get('service_actions')
        self.post_hooks = context.get('posthooks')

    @property
    def context(self):
        self.enabled = True
        _context = {}
        for ctxt in self.contexts:
            c = ctxt()
            if c and not c.get('__disabled__'):
                _context.update()

            if c.get('__disabled__'):
                self.enabled = False

        return _context


class HardeningConfigRenderer(object):

    # NOTE(dosaboy): we maintain template catalog in class context to provide
    #                access to whoever instantiates this class.
    templates = {}

    def __init__(self, harden_type, templates_dir):
        if not os.path.isdir(templates_dir):
            msg = ("Could not find templates dir '%s'" % templates_dir)
            log(msg, level=ERROR)
            raise HardeningConfigException(msg)

        self.harden_type = harden_type
        self.templates_dir = templates_dir

    @classmethod
    def register(cls, harden_type, target, context):
        if harden_type not in cls.templates:
            cls.templates[harden_type] = {}

        cls.templates[harden_type][target] = TemplateContext(target, context)

    def render(self, target):
        context = self.templates[self.harden_type][target].context
        if not self.templates[self.harden_type][target].enabled:
            log("Template context for '%s' disabled - skipping" %
                (target), level=INFO)
            return

        env = Environment(loader=FileSystemLoader(self.templates_dir))
        template = env.get_template(os.path.basename(target))
        log('Rendering from template: %s' % template.name, level=INFO)
        return template.render(context)

    def write(self, config_file):
        """Render template and write to config file"""
        if config_file not in self.templates[self.harden_type]:
            msg = ("Config template '%s' is not registered" % config_file)
            log(msg, level=ERROR)
            raise HardeningConfigException(msg)

        rendered = self.render(config_file)
        if not rendered:
            log("Render returned None - skipping '%s'" % (config_file))
            return

        with open(config_file, 'wb') as out:
            out.write(rendered)

        log('Wrote template %s.' % config_file, level=INFO)
        service_actions = self.templates[self.harden_type][config_file].\
            service_actions
        if service_actions:
            log('Running service action(s)', level=INFO)
            cmd = ['sudo', 'service']
            # This will intentionally fail if any actions fail to complete
            [subprocess.check_call(cmd + [s, a]) for s, a in service_actions]

        # Permissions
        perms = self.templates[self.harden_type][config_file].permissions
        if perms:
            log('Applying permissions', level=INFO)
            [ensure_permissions(*args) for args in perms]

        # Post hooks
        hooks = self.templates[self.harden_type][config_file].post_hooks
        if hooks:
            log('Running post hook(s)', level=INFO)
            [f(*args, **kwargs) for f, args, kwargs in hooks]

    def write_all(self):
        """Write out all registered config files."""
        [self.write(k) for k in six.iterkeys(self.templates[self.harden_type])]
