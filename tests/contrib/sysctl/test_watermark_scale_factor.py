#!/usr/bin/env python

from charmhelpers.contrib.sysctl.watermark_scale_factor import watermark_scale_factor, calculate_watermark_scale_factor, get_memtotal, get_normal_managed_pages

from mock import patch, mock_open
import unittest

TO_PATCH = [
    "log",
    "ERROR",
    "DEBUG"
]

PROC_MEMINFO = """
MemTotal:       98881012 kB
MemFree:         5415708 kB
MemAvailable:   30993024 kB
Buffers:           12712 kB
Cached:         16951140 kB
SwapCached:       155104 kB
Active:         39450516 kB
Inactive:       16879984 kB
Active(anon):   25640412 kB
Inactive(anon): 12953116 kB
Active(file):   13810104 kB
Inactive(file):  3926868 kB
Unevictable:      156348 kB
Mlocked:          156348 kB
SwapTotal:       2097148 kB
SwapFree:         702676 kB
Dirty:              1708 kB
Writeback:            12 kB
AnonPages:      39295640 kB
Mapped:          2094992 kB
Shmem:            141668 kB
KReclaimable:    8832856 kB
Slab:           32299340 kB
SReclaimable:    8832856 kB
SUnreclaim:     23466484 kB
KernelStack:      132608 kB
PageTables:       229164 kB
NFS_Unstable:          0 kB
Bounce:                0 kB
WritebackTmp:          0 kB
CommitLimit:    51537652 kB
Committed_AS:   112598920 kB
VmallocTotal:   34359738367 kB
VmallocUsed:     2191060 kB
VmallocChunk:          0 kB
Percpu:           393984 kB
HardwareCorrupted:     0 kB
AnonHugePages:   1744896 kB
ShmemHugePages:        0 kB
ShmemPmdMapped:        0 kB
FileHugePages:         0 kB
FilePmdMapped:         0 kB
HugePages_Total:       0
HugePages_Free:        0
HugePages_Rsvd:        0
HugePages_Surp:        0
Hugepagesize:       2048 kB
Hugetlb:               0 kB
DirectMap4k:    85061760 kB
DirectMap2M:    14542848 kB
DirectMap1G:     2097152 kB
"""

PROC_ZONEINFO = """
Node 0, zone      DMA
  per-node stats
      nr_inactive_anon 3237435
      nr_active_anon 6416446
      nr_inactive_file 983657
      nr_active_file 3448041
      nr_unevictable 39087
      nr_slab_reclaimable 2203647
      nr_slab_unreclaimable 5859699
      nr_isolated_anon 0
      nr_isolated_file 0
      workingset_nodes 29735
      workingset_refault 17290656
      workingset_activate 8570406
      workingset_restore 7721485
      workingset_nodereclaim 71212
      nr_anon_pages 9829457
      nr_mapped    526142
      nr_file_pages 4277229
      nr_dirty     158
      nr_writeback 606
      nr_writeback_temp 0
      nr_shmem     35417
      nr_shmem_hugepages 0
      nr_shmem_pmdmapped 0
      nr_file_hugepages 0
      nr_file_pmdmapped 0
      nr_anon_transparent_hugepages 853
      nr_vmscan_write 767342
      nr_vmscan_immediate_reclaim 1554724
      nr_dirtied   317982015
      nr_written   314994640
      nr_kernel_misc_reclaimable 0
      nr_foll_pin_acquired 0
      nr_foll_pin_released 0
  pages free     2948
        min      2
        low      5
        high     8
        spanned  4095
        present  3998
        managed  3976
        protection: (0, 1737, 96447, 96447, 96447)
      nr_free_pages 2948
      nr_zone_inactive_anon 0
      nr_zone_active_anon 0
      nr_zone_inactive_file 0
      nr_zone_active_file 0
      nr_zone_unevictable 0
      nr_zone_write_pending 0
      nr_mlock     0
      nr_page_table_pages 0
      nr_kernel_stack 0
      nr_bounce    0
      nr_zspages   0
      nr_free_cma  0
      numa_hit     2
      numa_miss    0
      numa_foreign 0
      numa_interleave 1
      numa_local   2
      numa_other   0
  pagesets
    cpu: 0
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 1
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 2
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 3
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 4
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 5
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 6
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 7
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 8
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 9
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 10
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 11
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 12
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 13
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 14
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 15
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 16
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 17
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 18
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 19
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 20
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 21
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 22
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
    cpu: 23
              count: 0
              high:  0
              batch: 1
  vm stats threshold: 10
  node_unreclaimable:  0
  start_pfn:           1
Node 0, zone    DMA32
  pages free     95767
        min      304
        low      748
        high     1192
        spanned  1044480
        present  484896
        managed  468467
        protection: (0, 0, 94710, 94710, 94710)
      nr_free_pages 95767
      nr_zone_inactive_anon 103547
      nr_zone_active_anon 239700
      nr_zone_inactive_file 158
      nr_zone_active_file 2968
      nr_zone_unevictable 0
      nr_zone_write_pending 0
      nr_mlock     0
      nr_page_table_pages 0
      nr_kernel_stack 0
      nr_bounce    0
      nr_zspages   0
      nr_free_cma  0
      numa_hit     25027968
      numa_miss    0
      numa_foreign 0
      numa_interleave 1
      numa_local   25027968
      numa_other   0
  pagesets
    cpu: 0
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 1
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 2
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 3
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 4
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 5
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 6
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 7
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 8
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 9
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 10
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 11
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 12
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 13
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 14
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 15
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 16
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 17
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 18
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 19
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 20
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 21
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 22
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
    cpu: 23
              count: 0
              high:  378
              batch: 63
  vm stats threshold: 50
  node_unreclaimable:  0
  start_pfn:           4096
Node 0, zone   Normal
  pages free     1253032
        min      16588
        low      40833
        high     65078
        spanned  24674304
        present  24674304
        managed  24247810
        protection: (0, 0, 0, 0, 0)
      nr_free_pages 1253032
      nr_zone_inactive_anon 3133888
      nr_zone_active_anon 6176746
      nr_zone_inactive_file 983499
      nr_zone_active_file 3445073
      nr_zone_unevictable 39087
      nr_zone_write_pending 764
      nr_mlock     39087
      nr_page_table_pages 57517
      nr_kernel_stack 131632
      nr_bounce    0
      nr_zspages   0
      nr_free_cma  0
      numa_hit     17116673798
      numa_miss    0
      numa_foreign 0
      numa_interleave 72294
      numa_local   17116673798
      numa_other   0
  pagesets
    cpu: 0
              count: 323
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 1
              count: 90
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 2
              count: 51
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 3
              count: 363
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 4
              count: 92
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 5
              count: 349
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 6
              count: 318
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 7
              count: 234
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 8
              count: 334
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 9
              count: 342
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 10
              count: 153
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 11
              count: 315
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 12
              count: 74
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 13
              count: 211
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 14
              count: 330
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 15
              count: 330
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 16
              count: 111
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 17
              count: 338
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 18
              count: 76
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 19
              count: 60
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 20
              count: 217
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 21
              count: 341
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 22
              count: 363
              high:  378
              batch: 63
  vm stats threshold: 110
    cpu: 23
              count: 338
              high:  378
              batch: 63
  vm stats threshold: 110
  node_unreclaimable:  0
  start_pfn:           1048576
Node 0, zone  Movable
  pages free     0
        min      0
        low      0
        high     0
        spanned  0
        present  0
        managed  0
        protection: (0, 0, 0, 0, 0)
Node 0, zone   Device
  pages free     0
        min      0
        low      0
        high     0
        spanned  0
        present  0
        managed  0
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
    @patch('charmhelpers.contrib.sysctl.watermark_scale_factor.get_memtotal')
    def test_calculate_watermark_scale_factor(self, memtotal, normal_managed_pages):
        memtotal.return_value = 98881012
        normal_managed_pages.return_value = [24247810]
        wmark = calculate_watermark_scale_factor()
        self.assertTrue(wmark >= 10, "ret {}".format(wmark))
        self.assertTrue(wmark <= 1000, "ret {}".format(wmark))

    def test_get_memtotal(self):
        print(PROC_MEMINFO)
        with patch("builtins.open", mock_open(read_data=PROC_MEMINFO)) as mock_file:
            result = get_memtotal()
            mock_file.assert_called_with('/proc/meminfo','r')

        self.assertTrue(result == 98881012)

    @patch("builtins.open", new_callable=mock_open, read_data=PROC_ZONEINFO)
    def test_get_normal_managed_pages(self, mock_file):
        self.assertCountEqual(get_normal_managed_pages(), [24247810])
        mock_file.assert_called_with('/proc/zoneinfo', 'r')

    def test_watermark_scale_factor(self):
        mem_totals = [16777152, 33554304, 536868864]
        managed_pages = [4194288, 24247815, 8388576, 134217216]
        arglists = [[mem, managed] for mem in mem_totals for managed in managed_pages]

        for arglist in arglists:
            wmark = watermark_scale_factor(*arglist)
            self.assertTrue(wmark >= 10, "assert failed for args: {}, ret {}".format(arglist, wmark))
            self.assertTrue(wmark <= 1000, "assert failed for args: {}, ret {}".format(arglist, wmark))
