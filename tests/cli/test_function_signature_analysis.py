"""Tests for the commandant code that analyzes a function signature to
determine the parameters to argparse."""

from testtools import TestCase

from charmhelpers import cli


class FunctionSignatureTest(TestCase):
    """Test a variety of function signatures."""

    def test_positional_arguments(self):
        """Finite number of order-dependent required arguments."""
        argparams = tuple(cli.describe_arguments(lambda x, y, z: False))
        self.assertEqual(3, len(argparams))
        for argspec in ((('x',), {}), (('y',), {}), (('z',), {})):
            self.assertIn(argspec, argparams)

    def test_keyword_arguments(self):
        """Function has optional parameters with default values."""
        argparams = tuple(cli.describe_arguments(lambda x, y=3, z="bar": False))
        self.assertEqual(3, len(argparams))
        for argspec in ((('x',), {}),
                        (('--y',), {"default": 3}),
                        (('--z',), {"default": "bar"})):
            self.assertIn(argspec, argparams)

    def test_varargs(self):
        """Function has a splat-operator parameter to catch an arbitrary number
        of positional parameters."""
        argparams = tuple(cli.describe_arguments(
            lambda x, y=3, *z: False))
        self.assertEqual(3, len(argparams))
        for argspec in ((('x',), {}),
                        (('--y',), {"default": 3}),
                        (('z',), {"nargs": "*"})):
            self.assertIn(argspec, argparams)

    def test_keyword_splat_missing(self):
        """Double-splat arguments can't be represented in the current version
        of commandant."""
        args = cli.describe_arguments(lambda x, y=3, *z, **missing: False)
        for opts, _ in args:
            # opts should be ('varname',) at this point
            self.assertTrue(len(opts) == 1)
            self.assertNotIn('missing', opts)
