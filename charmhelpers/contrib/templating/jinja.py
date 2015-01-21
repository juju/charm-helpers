"""
Templating using the python-jinja2 package.
"""
import six
from charmhelpers.fetch import apt_install
try:
    import jinja2
except ImportError:
    if six.PY3:
        apt_install(["python3-jinja2"])
    else:
        apt_install(["python-jinja2"])
    import jinja2


DEFAULT_TEMPLATES_DIR = 'templates'


def render(template_name, context, template_dir=DEFAULT_TEMPLATES_DIR):
    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir))
    template = templates.get_template(template_name)
    return template.render(context)
