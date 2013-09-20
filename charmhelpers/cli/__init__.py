import inspect
import itertools
import argparse
import sys


class OutputFormatter(object):
    def __init__(self, outfile=sys.stdout):
        self.formats = (
            "raw",
            "json",
            "py",
            "yaml",
            "csv",
            "tab",
        )
        self.outfile = outfile

    def add_arguments(self, argument_parser):
        formatgroup = argument_parser.add_mutually_exclusive_group()
        choices = self.supported_formats
        formatgroup.add_argument("--format", metavar='FMT',
                                 help="Select output format for returned data, "
                                      "where FMT is one of: {}".format(choices),
                                 choices=choices, default='raw')
        for fmt in self.formats:
            fmtfunc = getattr(self, fmt)
            formatgroup.add_argument("-{}".format(fmt[0]),
                                     "--{}".format(fmt), action='store_const',
                                     const=fmt, dest='format',
                                     help=fmtfunc.__doc__)

    @property
    def supported_formats(self):
        return self.formats

    def raw(self, output):
        """Output data as raw string (default)"""
        self.outfile.write(str(output))

    def py(self, output):
        """Output data as a nicely-formatted python data structure"""
        import pprint
        pprint.pprint(output, stream=self.outfile)

    def json(self, output):
        """Output data in JSON format"""
        import json
        json.dump(output, self.outfile)

    def yaml(self, output):
        """Output data in YAML format"""
        import yaml
        yaml.safe_dump(output, self.outfile)

    def csv(self, output):
        """Output data as excel-compatible CSV"""
        import csv
        csvwriter = csv.writer(self.outfile)
        csvwriter.writerows(output)

    def tab(self, output):
        """Output data in excel-compatible tab-delimited format"""
        import csv
        csvwriter = csv.writer(self.outfile, dialect=csv.excel_tab)
        csvwriter.writerows(output)

    def format_output(self, output, fmt='raw'):
        fmtfunc = getattr(self, fmt)
        fmtfunc(output)


class CommandLine(object):
    argument_parser = None
    subparsers = None
    formatter = None

    def __init__(self):
        if not self.argument_parser:
            self.argument_parser = argparse.ArgumentParser(description='Perform common charm tasks')
        if not self.formatter:
            self.formatter = OutputFormatter()
            self.formatter.add_arguments(self.argument_parser)
        if not self.subparsers:
            self.subparsers = self.argument_parser.add_subparsers(help='Commands')

    def subcommand(self, command_name=None):
        """
        Decorate a function as a subcommand. Use its arguments as the
        command-line arguments"""
        def wrapper(decorated):
            cmd_name = command_name or decorated.__name__
            subparser = self.subparsers.add_parser(cmd_name,
                                                   description=decorated.__doc__)
            for args, kwargs in describe_arguments(decorated):
                subparser.add_argument(*args, **kwargs)
            subparser.set_defaults(func=decorated)
            return decorated
        return wrapper

    def subcommand_builder(self, command_name, description=None):
        """
        Decorate a function that builds a subcommand. Builders should accept a
        single argument (the subparser instance) and return the function to be
        run as the command."""
        def wrapper(decorated):
            subparser = self.subparsers.add_parser(command_name)
            func = decorated(subparser)
            subparser.set_defaults(func=func)
            subparser.description = description or func.__doc__
        return wrapper

    def run(self):
        "Run cli, processing arguments and executing subcommands."
        arguments = self.argument_parser.parse_args()
        argspec = inspect.getargspec(arguments.func)
        vargs = []
        kwargs = {}
        if argspec.varargs:
            vargs = getattr(arguments, argspec.varargs)
        for arg in argspec.args:
            kwargs[arg] = getattr(arguments, arg)
        self.formatter.format_output(arguments.func(*vargs, **kwargs), arguments.format)


cmdline = CommandLine()


def describe_arguments(func):
    """
    Analyze a function's signature and return a data structure suitable for
    passing in as arguments to an argparse parser's add_argument() method."""

    argspec = inspect.getargspec(func)
    # we should probably raise an exception somewhere if func includes **kwargs
    if argspec.defaults:
        positional_args = argspec.args[:-len(argspec.defaults)]
        keyword_names = argspec.args[-len(argspec.defaults):]
        for arg, default in itertools.izip(keyword_names, argspec.defaults):
            yield ('--{}'.format(arg),), {'default': default}
    else:
        positional_args = argspec.args

    for arg in positional_args:
        yield (arg,), {}
    if argspec.varargs:
        yield (argspec.varargs,), {'nargs': '*'}
