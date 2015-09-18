# Copyright 2014-2015 Canonical Limited.
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

"""
Templating using the python-jinja2 package.
"""
import six
from charmhelpers.fetch import apt_install, apt_update
try:
    import jinja2
except ImportError:
    apt_update(fatal=True)
    if six.PY3:
        apt_install(["python3-jinja2"], fatal=True)
    else:
        apt_install(["python-jinja2"], fatal=True)
    import jinja2


DEFAULT_TEMPLATES_DIR = 'templates'


def render(template_name, context, template_dir=DEFAULT_TEMPLATES_DIR):
    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir))
    template = templates.get_template(template_name)
    return template.render(context)
