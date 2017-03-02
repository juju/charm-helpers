#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import imp

from charmhelpers import osplatform
from mock import patch
from tests.helpers import patch_open
from charmhelpers.core import kernel


class TestKernel(unittest.TestCase):

    @patch('subprocess.check_call')
    @patch.object(osplatform, 'get_platform')
    def test_modprobe_persistent_ubuntu(self, platform, check_call):
        platform.return_value = 'ubuntu'
        imp.reload(kernel)

        with patch_open() as (_open, _file):
            _file.read.return_value = 'anothermod\n'
            with patch("charmhelpers.core.kernel.log"):
                kernel.modprobe('mymod')
            _open.assert_called_with('/etc/modules', 'r+')
            _file.read.assert_called_with()
            _file.write.assert_called_with('mymod\n')
        check_call.assert_called_with(['modprobe', 'mymod'])

    @patch('os.chmod')
    @patch('subprocess.check_call')
    @patch.object(osplatform, 'get_platform')
    def test_modprobe_persistent_centos(self, platform, check_call, os):
        platform.return_value = 'centos'
        imp.reload(kernel)

        with patch_open() as (_open, _file):
            _file.read.return_value = 'anothermod\n'
            with patch("charmhelpers.core.kernel.log"):
                kernel.modprobe('mymod')
            _open.assert_called_with('/etc/rc.modules', 'r+')
            os.assert_called_with('/etc/rc.modules', 111)
            _file.read.assert_called_with()
            _file.write.assert_called_with('modprobe mymod\n')
        check_call.assert_called_with(['modprobe', 'mymod'])

    @patch('subprocess.check_call')
    @patch.object(osplatform, 'get_platform')
    def test_modprobe_not_persistent_ubuntu(self, platform, check_call):
        platform.return_value = 'ubuntu'
        imp.reload(kernel)

        with patch_open() as (_open, _file):
            _file.read.return_value = 'anothermod\n'
            with patch("charmhelpers.core.kernel.log"):
                kernel.modprobe('mymod', persist=False)
            assert not _open.called
        check_call.assert_called_with(['modprobe', 'mymod'])

    @patch('subprocess.check_call')
    @patch.object(osplatform, 'get_platform')
    def test_modprobe_not_persistent_centos(self, platform, check_call):
        platform.return_value = 'centos'
        imp.reload(kernel)

        with patch_open() as (_open, _file):
            _file.read.return_value = 'anothermod\n'
            with patch("charmhelpers.core.kernel.log"):
                kernel.modprobe('mymod', persist=False)
            assert not _open.called
        check_call.assert_called_with(['modprobe', 'mymod'])

    @patch.object(kernel, 'log')
    @patch('subprocess.check_call')
    def test_rmmod_not_forced(self, check_call, log):
        kernel.rmmod('mymod')
        check_call.assert_called_with(['rmmod', 'mymod'])

    @patch.object(kernel, 'log')
    @patch('subprocess.check_call')
    def test_rmmod_forced(self, check_call, log):
        kernel.rmmod('mymod', force=True)
        check_call.assert_called_with(['rmmod', '-f', 'mymod'])

    @patch.object(kernel, 'log')
    @patch('subprocess.check_output')
    def test_lsmod(self, check_output, log):
        kernel.lsmod()
        check_output.assert_called_with(['lsmod'],
                                        universal_newlines=True)

    @patch('charmhelpers.core.kernel.lsmod')
    def test_is_module_loaded(self, lsmod):
        lsmod.return_value = "ip6_tables 28672  1 ip6table_filter"
        self.assertTrue(kernel.is_module_loaded("ip6_tables"))

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_update_initramfs_ubuntu(self, check_call, platform):
        platform.return_value = 'ubuntu'
        imp.reload(kernel)

        kernel.update_initramfs()
        check_call.assert_called_with(["update-initramfs", "-k", "all", "-u"])

    @patch.object(osplatform, 'get_platform')
    @patch('subprocess.check_call')
    def test_update_initramfs_centos(self, check_call, platform):
        platform.return_value = 'centos'
        imp.reload(kernel)

        kernel.update_initramfs()
        check_call.assert_called_with(['dracut', '-f', 'all'])
