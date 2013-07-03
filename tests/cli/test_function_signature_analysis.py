"""Tests for the commandant code that analyzes a function signature to
determine the parameters to argparse."""

from testtools import TestCase, matchers

from charmhelpers import cli

class FunctionSignatureTest(TestCase):
    """Test a variety of function signatures."""

    def test_positional_arguments(self):
        """Finite number of order-dependent required arguments."""
        argparams = cli.describe_arguments(lambda x, y, z: False)
        self.assertEqual(tuple(argparams),
                ((('x',), {}), (('y',), {}), (('z',), {})))

    def test_keyword_arguments(self):
        """Function has optional parameters with default values."""
        argparams = tuple(cli.describe_arguments(
            lambda x, y=3, z="bar": False))
        self.assertIn((('--y',), {'default': 3}), argparams)
        self.assertIn((('--z',), {'default': 'bar'}), argparams)

    def test_varargs(self):
        """Function has a splat-operator parameter to catch an arbitrary number
        of positional parameters."""
        argparams = tuple(cli.describe_arguments(
            lambda x, y=3, *z: False))
        self.assertIn((('z',), {'nargs': '*'}), argparams)

    def test_keyword_splat_missing(self):
        """Double-splat arguments can't be represented in the current version
        of commandant."""
        args = cli.describe_arguments(
                lambda x, y=3, *z, **missing: False)
        for opts, _ in args:
            # opts should be ('varname',) at this point
            self.assertThat(opts, matchers.HasLength(1))
            self.assertNotIn('missing', opts)

