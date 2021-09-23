#!/usr/bin/env python

from charmhelpers.contrib.sysctl.watermark_scale_factor import (
    watermark_scale_factor,
    calculate_watermark_scale_factor,
    get_normal_managed_pages,
)

from mock import patch
import unittest

from tests.helpers import patch_open

TO_PATCH = [
    "log",
    "ERROR",
    "DEBUG"
]

PROC_ZONEINFO = """
Node 0, zone   Normal
  pages free     1253032
        min      16588
        low      40833
        high     65078
        spanned  24674304
        present  24674304
        managed  24247810
        protection: (0, 0, 0, 0, 0)
"""


class TestWatermarkScaleFactor(unittest.TestCase):

    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.sysctl.watermark_scale_factor.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    @patch('charmhelpers.contrib.sysctl.watermark_scale_factor.get_normal_managed_pages')
    @patch('charmhelpers.core.host.get_total_ram')
    def test_calculate_watermark_scale_factor(self, get_total_ram, get_normal_managed_pages):
        get_total_ram.return_value = 101254156288
        get_normal_managed_pages.return_value = [24247810]
        wmark = calculate_watermark_scale_factor()
        self.assertTrue(wmark >= 10, "ret {}".format(wmark))
        self.assertTrue(wmark <= 1000, "ret {}".format(wmark))

    def test_get_normal_managed_pages(self):
        with patch_open() as (mock_open, mock_file):
            mock_file.readlines.return_value = PROC_ZONEINFO.splitlines()
            self.assertEqual(get_normal_managed_pages(), [24247810])
            mock_open.assert_called_with('/proc/zoneinfo', 'r')

    def test_watermark_scale_factor(self):
        mem_totals = [17179803648, 34359607296, 549753716736]
        managed_pages = [4194288, 24247815, 8388576, 134217216]
        arglists = [[mem, managed] for mem in mem_totals for managed in managed_pages]

        for arglist in arglists:
            wmark = watermark_scale_factor(*arglist)
            self.assertTrue(wmark >= 10, "assert failed for args: {}, ret {}".format(arglist, wmark))
            self.assertTrue(wmark <= 1000, "assert failed for args: {}, ret {}".format(arglist, wmark))
