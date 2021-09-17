#!/usr/bin/env python
# -*- coding: utf-8 -*-

from charmhelpers.core.fstab import Fstab
from nose.tools import (assert_is,
                        assert_is_not,
                        assert_equal)
import unittest
import tempfile
import os

__author__ = 'Jorge Niedbalski R. <jorge.niedbalski@canonical.com>'

DEFAULT_FSTAB_FILE = """/dev/sda /mnt/sda ext3 defaults 0 0
 # This is an indented comment, and the next line is entirely blank.

/dev/sdb /mnt/sdb ext3 defaults 0 0
/dev/sdc	/mnt/sdc	ext3	defaults	0	0
UUID=3af44368-c50b-4768-8e58-aff003cef8be / ext4 errors=remount-ro 0 1
"""

GENERATED_FSTAB_FILE = '\n'.join(
    # Helper will writeback with spaces instead of tabs
    line.replace('\t', ' ') for line in DEFAULT_FSTAB_FILE.splitlines()
    if line.strip() and not line.strip().startswith('#'))


class FstabTest(unittest.TestCase):

    def setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile('w+', delete=False)
        self.tempfile.write(DEFAULT_FSTAB_FILE)
        self.tempfile.close()
        self.fstab = Fstab(path=self.tempfile.name)

    def tearDown(self):
        os.unlink(self.tempfile.name)

    def test_entries(self):
        """Test if entries are correctly read from fstab file"""
        assert_equal(sorted(GENERATED_FSTAB_FILE.splitlines()),
                     sorted(str(entry) for entry in self.fstab.entries))

    def test_get_entry_by_device_attr(self):
        """Test if the get_entry_by_attr method works for device attr"""
        for device in ('sda', 'sdb', 'sdc', ):
            assert_is_not(self.fstab.get_entry_by_attr('device',
                                                       '/dev/%s' % device),
                          None)

    def test_get_entry_by_mountpoint_attr(self):
        """Test if the get_entry_by_attr method works for mountpoint attr"""
        for mnt in ('sda', 'sdb', 'sdc', ):
            assert_is_not(self.fstab.get_entry_by_attr('mountpoint',
                                                       '/mnt/%s' % mnt), None)

    def test_add_entry(self):
        """Test if add_entry works for a new entry"""
        for device in ('sdf', 'sdg', 'sdh'):
            entry = Fstab.Entry('/dev/%s' % device, '/mnt/%s' % device, 'ext3',
                                None)
            assert_is_not(self.fstab.add_entry(entry), None)
            assert_is_not(self.fstab.get_entry_by_attr(
                'device', '/dev/%s' % device), None)

        assert_is(self.fstab.add_entry(entry), False,
                  "Check if adding an existing entry returns false")

    def test_remove_entry(self):
        """Test if remove entry works for already existing entries"""
        for entry in self.fstab.entries:
            assert_is(self.fstab.remove_entry(entry), True)

        assert_equal(len([entry for entry in self.fstab.entries]), 0)
        assert_equal(self.fstab.add_entry(entry), entry)
        assert_equal(len([entry for entry in self.fstab.entries]), 1)

    def test_assert_remove_add_all(self):
        """Test if removing/adding all the entries works"""
        for entry in self.fstab.entries:
            assert_is(self.fstab.remove_entry(entry), True)

        for device in ('sda', 'sdb', 'sdc', ):
            self.fstab.add_entry(
                Fstab.Entry('/dev/%s' % device, '/mnt/%s' % device, 'ext3',
                            None))

        self.fstab.add_entry(Fstab.Entry(
            'UUID=3af44368-c50b-4768-8e58-aff003cef8be',
            '/', 'ext4', 'errors=remount-ro', 0, 1))

        assert_equal(sorted(GENERATED_FSTAB_FILE.splitlines()),
                     sorted(str(entry) for entry in self.fstab.entries))
