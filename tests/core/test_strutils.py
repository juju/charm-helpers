import unittest

import charmhelpers.core.strutils as strutils


class TestStrUtils(unittest.TestCase):
    def setUp(self):
        super(TestStrUtils, self).setUp()

    def tearDown(self):
        super(TestStrUtils, self).tearDown()

    def test_bool_from_string(self):
        self.assertTrue(strutils.bool_from_string('true'))
        self.assertTrue(strutils.bool_from_string('True'))
        self.assertTrue(strutils.bool_from_string('yes'))
        self.assertTrue(strutils.bool_from_string('Yes'))
        self.assertTrue(strutils.bool_from_string('y'))
        self.assertTrue(strutils.bool_from_string('Y'))
        self.assertTrue(strutils.bool_from_string('on'))

        # unicode should also work
        self.assertTrue(strutils.bool_from_string(u'true'))

        self.assertFalse(strutils.bool_from_string('False'))
        self.assertFalse(strutils.bool_from_string('false'))
        self.assertFalse(strutils.bool_from_string('no'))
        self.assertFalse(strutils.bool_from_string('No'))
        self.assertFalse(strutils.bool_from_string('n'))
        self.assertFalse(strutils.bool_from_string('N'))
        self.assertFalse(strutils.bool_from_string('off'))

        self.assertRaises(ValueError, strutils.bool_from_string, None)
        self.assertRaises(ValueError, strutils.bool_from_string, 'foo')

    def test_bytes_from_string(self):
        self.assertEqual(strutils.bytes_from_string('3K'), 3072)
        self.assertEqual(strutils.bytes_from_string('3KB'), 3072)
        self.assertEqual(strutils.bytes_from_string('3M'), 3145728)
        self.assertEqual(strutils.bytes_from_string('3MB'), 3145728)
        self.assertEqual(strutils.bytes_from_string('3G'), 3221225472)
        self.assertEqual(strutils.bytes_from_string('3GB'), 3221225472)
        self.assertEqual(strutils.bytes_from_string('3T'), 3298534883328)
        self.assertEqual(strutils.bytes_from_string('3TB'), 3298534883328)
        self.assertEqual(strutils.bytes_from_string('3P'), 3377699720527872)
        self.assertEqual(strutils.bytes_from_string('3PB'), 3377699720527872)

        self.assertRaises(ValueError, strutils.bytes_from_string, None)
        self.assertRaises(ValueError, strutils.bytes_from_string, 'foo')
