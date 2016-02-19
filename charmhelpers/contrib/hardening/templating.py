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

try:
    from jinja2 import FileSystemLoader, Environment
except ImportError:
    apt_update(fatal=True)
    apt_install('python-jinja2', fatal=True)
    from jinja2 import FileSystemLoader, Environment


class HardeningConfigException(Exception):
    pass


class TemplateContext(object):
    def __init__(self, target, context):
        self.context = {}
        for ctxt in context['contexts']:
            self.context.update(ctxt())

        self.service_actions = context.get('service_actions')
        self.post_hooks = context.get('post-hooks')


class HardeningConfigRenderer(object):

    def __init__(self, templates_dir):
        if not os.path.isdir(templates_dir):
            msg = ("Could not find templates dir '%s'" % templates_dir)
            log(msg, level=ERROR)
            raise HardeningConfigException(msg)

        self.templates_dir = templates_dir
        self.templates = {}

    def register(self, target, context):
        self.templates[target] = TemplateContext(target, context)

    def render(self, target):
        ctxt = self.templates[target].context
        env = Environment(loader=FileSystemLoader(self.templates_dir))
        template = env.get_template(os.path.basename(target))
        log('Rendering from template: %s' % template.name, level=INFO)
        return template.render(ctxt)

    def write(self, config_file):
        """Render template and write to config file"""
        if config_file not in self.templates:
            msg = ("Config template '%s' is not registered" % config_file)
            log(msg, level=ERROR)
            raise HardeningConfigException(msg)

        rendered = self.render(config_file)
        with open(config_file, 'wb') as out:
            out.write(rendered)

        log('Wrote template %s.' % config_file, level=INFO)
        service_actions = self.templates[config_file].service_actions
        if service_actions:
            log('Running service action(s)', level=INFO)
            cmd = ['sudo', 'service']
            # This will intentionally fail if any actions fail to complete
            [subprocess.check_call(cmd + [s, a]) for s, a in service_actions]

        hooks = self.templates[config_file].post_hooks
        if hooks:
            log('Running post hook(s)', level=INFO)
            [f(*a, **kwa) for f, a, kwa in hooks]

    def write_all(self):
        """Write out all registered config files."""
        [self.write(k) for k in six.iterkeys(self.templates)]
