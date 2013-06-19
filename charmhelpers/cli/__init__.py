import inspect
import itertools
import argparse


class CommandLine(object):
    argument_parser = None
    subparsers = None

    def __init__(self):
        if not self.argument_parser:
            self.argument_parser = argparse.ArgumentParser(description='Perform common charm tasks')
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

    def make_subparser(self, subcmd_name, function, description=None):
        "An argparse subparser for the named subcommand."
        subparser = self.subparsers.add_parser(subcmd_name, description)
        subparser.set_defaults(func=function)
        return subparser

    def run(self):
        "Run cli, processing arguments and executing subcommands."
        arguments = self.argument_parser.parse_args()
        argspec = inspect.getargspec(arguments.func)
        vargs = []
        kwargs = {}
        if argspec.varargs:
            vargs = getattr(arguments, argspec.vargs)
        for arg in argspec.args:
            kwargs[arg] = getattr(arguments, arg)
        arguments.func(*vargs, **kwargs)


cmdline = CommandLine()


def describe_arguments(func):
    """
    Analyze a function's signature and return a data structure suitable for
    passing in as arguments to an argparse parser's add_argument() method."""

    argspec = inspect.getargspec(func)
    # we should probably raise an exception somewhere if func includes **kwargs
    if argspec.defaults:
        positional_args = argspec.args[:len(argspec.defaults)]
        keyword_names = argspec.args[-len(argspec.defaults):]
        for arg, default in itertools.izip(keyword_names, argspec.defaults):
            yield (arg,), {'default': default}
    else:
        positional_args = argspec.args

    for arg in positional_args:
        yield (arg,), {}
    if argspec.varargs:
        yield (argspec.varargs,), {'nargs': '*'}
