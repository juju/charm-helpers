#!/usr/bin/env python
# coding: utf-8

from __future__ import absolute_import

from unittest import TestCase

from charmhelpers.fetch.python import debug
from charmhelpers.fetch.python import packages
from charmhelpers.fetch.python import rpdb
from charmhelpers.fetch.python import version
from charmhelpers.contrib.python import debug as contrib_debug
from charmhelpers.contrib.python import packages as contrib_packages
from charmhelpers.contrib.python import rpdb as contrib_rpdb
from charmhelpers.contrib.python import version as contrib_version


class ContribDebugTestCase(TestCase):
    def test_aliases(self):
        assert contrib_debug is debug
        assert contrib_packages is packages
        assert contrib_rpdb is rpdb
        assert contrib_version is version
