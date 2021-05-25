#!/usr/bin/env python

from charmhelpers.contrib.sysctl.watermark_scale_factor import watermark_scale_factor
import unittest


class TestWatermarkScaleFactor(unittest.TestCase):

    def test_calculate_watermark_scale_factor(self):
        mem_totals = [16777152, 33554304, 536868864]
        managed_pages = [4194288, 24247815, 8388576, 134217216]
        arglists = [[mem, managed] for mem in mem_totals for managed in managed_pages]

        for arglist in arglists:
            wmark = watermark_scale_factor(*arglist)
            self.assertTrue(wmark >= 10, f"assert failed for args: {arglist}, ret {wmark}")
            self.assertTrue(wmark <= 1000, f"assert failed for args: {arglist}, ret {wmark}")
