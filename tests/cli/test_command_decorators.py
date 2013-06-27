"""Tests for the commandant code that analyzes a function signature to
determine the parameters to argparse."""

from testtools import TestCase, matchers
from mock import patch

from charmhelpers import cli

@patch('sys.exit')
class SubCommandTest(TestCase):
    """Test creation of subcommands"""

    def test_subcommand_wrapper(self, mock_sys_exit):
        """Test function name detection"""
        cmdline = cli.CommandLine()
        @cmdline.subcommand()
        def payload():
            "A function that does work."
            pass
        args = cmdline.argument_parser.parse_args(['payload'])
        self.assertEqual(args.func, payload)
        self.assertEqual(mock_sys_exit.mock_calls, [])

    def test_bogus_arguments(self, mock_sys_exit):
        """Test function name detection"""
        cmdline = cli.CommandLine()
        @cmdline.subcommand()
        def payload():
            "A function that does work."
            pass
        self.assertRaises(TypeError, cmdline.argument_parser.parse_args,
                ['deliberately bad input'])
        mock_sys_exit.assert_called_once_with(2)

    def test_cmdline_options(self, mock_sys_exit):
        """Test detection of positional arguments and optional parameters."""
        cmdline = cli.CommandLine()
        @cmdline.subcommand()
        def payload(x, y=None):
            "A function that does work."
            return x
        args = cmdline.argument_parser.parse_args(['payload', 'positional', '--y=optional'])
        self.assertEqual(args.func, payload)
        self.assertEqual(args.x, 'positional')
        self.assertEqual(args.y, 'optional')
        self.assertEqual(mock_sys_exit.mock_calls, [])
