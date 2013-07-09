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
