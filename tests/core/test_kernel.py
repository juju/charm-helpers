#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mock import patch
import unittest

from tests.helpers import patch_open
from charmhelpers.core import kernel

TO_PATCH = [
    'log',
    'check_call',
    'check_output',
]


class TestKernel(unittest.TestCase):

    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))

    def _patch(self, method):
        _m = patch('charmhelpers.core.kernel.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_modprobe_persistent(self):
        with patch_open() as (_open, _file):
            _file.read.return_value = 'anothermod\n'
            kernel.modprobe('mymod')
            _open.assert_called_with('/etc/modules', 'r+')
            _file.read.assert_called_with()
            _file.write.assert_called_with('mymod')
        self.check_call.assert_called_with(['modprobe', 'mymod'])

    def test_modprobe_not_persistent(self):
        with patch_open() as (_open, _file):
            _file.read.return_value = 'anothermod\n'
            kernel.modprobe('mymod', persist=False)
            assert not _open.called
        self.check_call.assert_called_with(['modprobe', 'mymod'])

    def test_rmmod_not_forced(self):
        kernel.rmmod('mymod')
        self.check_call.assert_called_with(['rmmod', 'mymod'])

    def test_rmmod_forced(self):
        kernel.rmmod('mymod', force=True)
        self.check_call.assert_called_with(['rmmod', '-f', 'mymod'])

    def test_lsmod(self):
        kernel.lsmod()
        self.check_output.assert_called_with(['lsmod'],
                                             universal_newlines=True)

    @patch('charmhelpers.core.kernel.lsmod')
    def test_is_module_loaded(self, lsmod):
        lsmod.return_value = "ip6_tables 28672  1 ip6table_filter"
        self.assertTrue(kernel.is_module_loaded(
            "ip6_tables"))

    def test_update_initramfs(self):
        kernel.update_initramfs()
        self.check_call.assert_called_with([
            "update-initramfs", "-k", "all", "-u"])
