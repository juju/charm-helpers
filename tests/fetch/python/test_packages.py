#!/usr/bin/env python
# coding: utf-8

import mock
import six

from unittest import TestCase
from charmhelpers.fetch.python import packages

__author__ = "Jorge Niedbalski <jorge.niedbalski@canonical.com>"

TO_PATCH = [
    "apt_install",
    "charm_dir",
    "log",
    "pip_execute",
]


class PipTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.patch_all()

        self.log.return_value = True
        self.apt_install.return_value = True

    def patch(self, method):
        _m = mock.patch.object(packages, method)
        _mock = _m.start()
        self.addCleanup(_m.stop)
        return _mock

    def patch_all(self):
        for method in TO_PATCH:
            setattr(self, method, self.patch(method))

    def test_pip_install_requirements(self):
        """
        Check if pip_install_requirements works correctly
        """
        packages.pip_install_requirements("test_requirements.txt")
        self.pip_execute.assert_called_with(["install",
                                             "-r test_requirements.txt"])

        packages.pip_install_requirements("test_requirements.txt",
                                          "test_constraints.txt")
        self.pip_execute.assert_called_with(["install",
                                             "-r test_requirements.txt",
                                             "-c test_constraints.txt"])

        packages.pip_install_requirements("test_requirements.txt",
                                          proxy="proxy_addr:8080")

        self.pip_execute.assert_called_with(["install",
                                             "--proxy=proxy_addr:8080",
                                             "-r test_requirements.txt"])

        packages.pip_install_requirements("test_requirements.txt",
                                          log="output.log",
                                          proxy="proxy_addr:8080")

        self.pip_execute.assert_called_with(["install",
                                             "--log=output.log",
                                             "--proxy=proxy_addr:8080",
                                             "-r test_requirements.txt"])

    def test_pip_install(self):
        """
        Check if pip_install works correctly with a single package
        """
        packages.pip_install("mock")
        self.pip_execute.assert_called_with(["install",
                                             "mock"])
        packages.pip_install("mock",
                             proxy="proxy_addr:8080")

        self.pip_execute.assert_called_with(["install",
                                             "--proxy=proxy_addr:8080",
                                             "mock"])
        packages.pip_install("mock",
                             log="output.log",
                             proxy="proxy_addr:8080")

        self.pip_execute.assert_called_with(["install",
                                             "--log=output.log",
                                             "--proxy=proxy_addr:8080",
                                             "mock"])

    def test_pip_install_upgrade(self):
        """
        Check if pip_install works correctly with a single package
        """
        packages.pip_install("mock", upgrade=True)
        self.pip_execute.assert_called_with(["install",
                                             "--upgrade",
                                             "mock"])

    def test_pip_install_multiple(self):
        """
        Check if pip_install works correctly with multiple packages
        """
        packages.pip_install(["mock", "nose"])
        self.pip_execute.assert_called_with(["install",
                                             "mock", "nose"])

    @mock.patch('subprocess.check_call')
    @mock.patch('os.path.join')
    def test_pip_install_venv(self, join, check_call):
        """
        Check if pip_install works correctly with multiple packages
        """
        join.return_value = 'joined-path'
        packages.pip_install(["mock", "nose"], venv=True)
        check_call.assert_called_with(["joined-path", "install",
                                       "mock", "nose"])

    def test_pip_uninstall(self):
        """
        Check if pip_uninstall works correctly with a single package
        """
        packages.pip_uninstall("mock")
        self.pip_execute.assert_called_with(["uninstall",
                                             "-q",
                                             "-y",
                                             "mock"])
        packages.pip_uninstall("mock",
                               proxy="proxy_addr:8080")

        self.pip_execute.assert_called_with(["uninstall",
                                             "-q",
                                             "-y",
                                             "--proxy=proxy_addr:8080",
                                             "mock"])
        packages.pip_uninstall("mock",
                               log="output.log",
                               proxy="proxy_addr:8080")

        self.pip_execute.assert_called_with(["uninstall",
                                             "-q",
                                             "-y",
                                             "--log=output.log",
                                             "--proxy=proxy_addr:8080",
                                             "mock"])

    def test_pip_uninstall_multiple(self):
        """
        Check if pip_uninstall works correctly with multiple packages
        """
        packages.pip_uninstall(["mock", "nose"])
        self.pip_execute.assert_called_with(["uninstall",
                                             "-q",
                                             "-y",
                                             "mock", "nose"])

    def test_pip_list(self):
        """
        Checks if pip_list works correctly
        """
        packages.pip_list()
        self.pip_execute.assert_called_with(["list"])

    @mock.patch('os.path.join')
    @mock.patch('subprocess.check_call')
    @mock.patch.object(packages, 'pip_install')
    def test_pip_create_virtualenv(self, pip_install, check_call, join):
        """
        Checks if pip_create_virtualenv works correctly
        """
        join.return_value = 'joined-path'
        packages.pip_create_virtualenv()
        if six.PY2:
            self.apt_install.assert_called_with('python-virtualenv')
            expect_flags = []
        else:
            self.apt_install.assert_called_with(['python3-virtualenv', 'virtualenv'])
            expect_flags = ['--python=python3']
        check_call.assert_called_with(['virtualenv', 'joined-path'] + expect_flags)
