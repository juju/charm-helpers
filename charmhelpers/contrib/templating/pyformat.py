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

'''
Templating using standard Python str.format() method.
'''

from charmhelpers.core import hookenv


def render(template, extra={}, **kwargs):
    """Return the template rendered using Python's str.format()."""
    context = hookenv.execution_environment()
    context.update(extra)
    context.update(kwargs)
    return template.format(**context)
