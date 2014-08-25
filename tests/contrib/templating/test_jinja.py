import tempfile
import os

from shutil import rmtree
from testtools import TestCase

from charmhelpers.contrib.templating.jinja import render


SIMPLE_TEMPLATE = "{{ somevar }}"


LOOP_TEMPLATE = "{% for i in somevar %}{{ i }}{% endfor %}"


class Jinja2Test(TestCase):

    def setUp(self):
        super(Jinja2Test, self).setUp()
        # Create a "templates directory" in temp
        self.templates_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(Jinja2Test, self).tearDown()
        # Remove the temporary directory so as not to pollute /tmp
        rmtree(self.templates_dir)

    def _write_template_to_file(self, name, contents):
        path = os.path.join(self.templates_dir, name)
        with open(path, "w") as thefile:
            thefile.write(contents)

    def test_render_simple_template(self):
        name = "simple"
        self._write_template_to_file(name, SIMPLE_TEMPLATE)
        expected = "hello"
        result = render(
            name, {"somevar": expected}, template_dir=self.templates_dir)
        self.assertEqual(expected, result)

    def test_render_loop_template(self):
        name = "loop"
        self._write_template_to_file(name, LOOP_TEMPLATE)
        expected = "12345"
        result = render(
            name, {"somevar": ["1", "2", "3", "4", "5"]},
            template_dir=self.templates_dir)
        self.assertEqual(expected, result)
