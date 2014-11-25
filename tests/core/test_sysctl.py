#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Jorge Niedbalski R. <jorge.niedbalski@canonical.com>'

from charmhelpers.core.sysctl import create
from mock import patch, MagicMock

import unittest
import tempfile

TO_PATCH = [
    'log',
    'check_call',
]


class SysctlTests(unittest.TestCase):
    def setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile(delete=False)
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))

    def _patch(self, method):
        _m = patch('charmhelpers.core.sysctl.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    @patch('__builtin__.open')
    def test_create(self, mock_open):
        """Test create sysctl method"""
        _file = MagicMock(spec=file)
        mock_open.return_value = _file

        create('{"kernel.max_pid": 1337}', "/etc/sysctl.d/test-sysctl.conf")

        _file.__enter__().write.assert_called_with("kernel.max_pid=1337\n")

        self.log.assert_called_with(
            "Updating sysctl_file: /etc/sysctl.d/test-sysctl.conf"
            " values: {'kernel.max_pid': 1337}",
            level='DEBUG')

        self.check_call.assert_called_with([
            "sysctl", "-p",
            "/etc/sysctl.d/test-sysctl.conf"])
