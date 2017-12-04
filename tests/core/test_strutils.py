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
        self.assertEqual(strutils.bytes_from_string('10'), 10)
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

    def test_basic_string_comparator_class_fails_instantiation(self):
        try:
            strutils.BasicStringComparator('hello')
            raise Exception("instantiating BasicStringComparator should fail")
        except Exception as e:
            assert (str(e) == "Must define the _list in the class definition!")

    def test_basic_string_comparator_class(self):

        class MyComparator(strutils.BasicStringComparator):

            _list = ('zomg', 'bartlet', 'over', 'and')

        x = MyComparator('zomg')
        self.assertEquals(x.index, 0)
        y = MyComparator('over')
        self.assertEquals(y.index, 2)
        self.assertTrue(x == 'zomg')
        self.assertTrue(x != 'bartlet')
        self.assertTrue(x == x)
        self.assertTrue(x != y)
        self.assertTrue(x < y)
        self.assertTrue(y > x)
        self.assertTrue(x < 'bartlet')
        self.assertTrue(y > 'bartlet')
        self.assertTrue(x >= 'zomg')
        self.assertTrue(x <= 'zomg')
        self.assertTrue(x >= x)
        self.assertTrue(x <= x)
        self.assertTrue(y >= 'zomg')
        self.assertTrue(y <= 'over')
        self.assertTrue(y >= x)
        self.assertTrue(x <= y)
        # ensure that something not in the list dies
        try:
            MyComparator('nope')
            raise Exception("MyComparator('nope') should have failed")
        except Exception as e:
            self.assertTrue(isinstance(e, KeyError))

    def test_basic_string_comparator_fails_different_comparators(self):

        class MyComparator1(strutils.BasicStringComparator):

            _list = ('the truth is out there'.split(' '))

        class MyComparator2(strutils.BasicStringComparator):

            _list = ('no one in space can hear you scream'.split(' '))

        x = MyComparator1('is')
        y = MyComparator2('you')
        try:
            x > y
            raise Exception("Comparing different comparators should fail")
        except Exception as e:
            self.assertTrue(isinstance(e, AssertionError))
