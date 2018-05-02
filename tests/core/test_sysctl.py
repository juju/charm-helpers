#!/usr/bin/env python
# -*- coding: utf-8 -*-

from charmhelpers.core.sysctl import create
import io
from mock import patch, MagicMock
import unittest
import tempfile

import six
if not six.PY3:
    builtin_open = '__builtin__.open'
else:
    builtin_open = 'builtins.open'

__author__ = 'Jorge Niedbalski R. <jorge.niedbalski@canonical.com>'


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

    @patch(builtin_open)
    def test_create(self, mock_open):
        """Test create sysctl method"""
        _file = MagicMock(spec=io.FileIO)
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

    @patch(builtin_open)
    def test_create_with_dict(self, mock_open):
        """Test create sysctl method"""
        _file = MagicMock(spec=io.FileIO)
        mock_open.return_value = _file

        create({"kernel.max_pid": 1337}, "/etc/sysctl.d/test-sysctl.conf")

        _file.__enter__().write.assert_called_with("kernel.max_pid=1337\n")

        self.log.assert_called_with(
            "Updating sysctl_file: /etc/sysctl.d/test-sysctl.conf"
            " values: {'kernel.max_pid': 1337}",
            level='DEBUG')

        self.check_call.assert_called_with([
            "sysctl", "-p",
            "/etc/sysctl.d/test-sysctl.conf"])

    @patch(builtin_open)
    def test_create_invalid_argument(self, mock_open):
        """Test create sysctl with an invalid argument"""
        _file = MagicMock(spec=io.FileIO)
        mock_open.return_value = _file

        create('{"kernel.max_pid": 1337 xxxx', "/etc/sysctl.d/test-sysctl.conf")

        self.log.assert_called_with(
            'Error parsing YAML sysctl_dict: {"kernel.max_pid": 1337 xxxx',
            level='ERROR')
