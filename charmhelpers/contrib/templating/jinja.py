"""
Templating using the python-jinja2 package.
"""
from charmhelpers.fetch import (
    apt_install,
)


DEFAULT_TEMPLATES_DIR = 'templates'


try:
    import jinja2
except ImportError:
    apt_install(["python-jinja2"])
    import jinja2


def render(template_name, context, template_dir=DEFAULT_TEMPLATES_DIR):
    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir))
    template = templates.get_template(template_name)
    return template.render(context)
