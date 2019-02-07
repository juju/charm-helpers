#!/usr/bin/env python
# coding: utf-8

from unittest import TestCase

from charmhelpers.fetch.python import debug

import mock

__author__ = "Jorge Niedbalski <jorge.niedbalski@canonical.com>"

TO_PATCH = [
    "log",
    "open_port",
    "close_port",
    "Rpdb",
    "_error",
]


class DebugTestCase(TestCase):
    """Test cases for charmhelpers.contrib.python.debug"""

    def setUp(self):
        TestCase.setUp(self)
        self.patch_all()
        self.log.return_value = True
        self.close_port.return_value = True

        self.wrapped_function = mock.Mock(return_value=True)
        self.set_trace = debug.set_trace

    def patch(self, method):
        _m = mock.patch.object(debug, method)
        _mock = _m.start()
        self.addCleanup(_m.stop)
        return _mock

    def patch_all(self):
        for method in TO_PATCH:
            setattr(self, method, self.patch(method))

    def test_debug_set_trace(self):
        """Check if set_trace works
        """
        self.set_trace()
        self.open_port.assert_called_with(4444)

    def test_debug_set_trace_ex(self):
        """Check if set_trace raises exception
        """
        self.set_trace()
        self.Rpdb.set_trace.side_effect = Exception()
        self.assertTrue(self._error.called)
