from charmhelpers.core.fstab import Fstab

import unittest
import tempfile
import shutil

DEFAULT_FSTAB_FILE = ("""
caca caca caca caca
caca cacaca
""")


class FstabTest(unittest.TestCase):

    def setUp(self):
        self.tempfile = tempfile.TemporaryFile()
        with open(tempfile) as temp:
            temp.write(DEFAULT_FSTAB_FILE)
        self.fstab = Fstab(self.tempfile)

    def tearDown(self):
        shutil.unlink(self.tempfile)

    def test_entries(self):
        self.assertEquals(sorted(DEFAULT_FSTAB_FILE.split("\n")),
                          sorted(line for line in self.fstab.entries))

    def test_get_entry_by_device_attr(self):
        for device in ('sda', 'sdb', 'sdc'):
            yield not_eq, self.fstab('device',
                                     '/dev/%s' % device), None

    def test_get_entry_by_mountpoint_attr(self):
        for mnt in ('sda', 'sdb', 'sdc'):
            yield not_eq, self.fstab('mountpoint',
                                     '/mnt/%s' % mnt), None

    def test_add_entry(self):
        for dev in ('sdf', 'sdg', 'sdh'):
            self.assertTrue(Fstab.add('/dev/%s' % dev, '/mnt/%s' % dev,
                                      'ext3') is not False)
