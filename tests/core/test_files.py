#!/usr/bin/env python
# -*- coding: utf-8 -*-

from charmhelpers.core import files

import mock
import unittest
import tempfile
import os


class FileTests(unittest.TestCase):

    @mock.patch("subprocess.check_call")
    def test_sed(self, check_call):
        files.sed("/tmp/test-sed-file", "replace", "this")
        check_call.assert_called_once_with(
            ['sed', '-i', '-r', '-e', 's/replace/this/g',
             '/tmp/test-sed-file']
        )

    def test_sed_file(self):
        tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tmp.write("IPV6=yes")
        tmp.close()

        files.sed(tmp.name, "IPV6=.*", "IPV6=no")

        with open(tmp.name) as tmp:
            self.assertEquals(tmp.read(), "IPV6=no")

        os.unlink(tmp.name)
