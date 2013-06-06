"""Tools to inspect function signatures and build argparse parsers from
them."""

import inspect
import itertools

def describe_arguments(func):
    """Analyze a function's signature and return a data structure suitable for
    passing in as arguments to an argparse parser's add_argument() method."""

    argspec = inspect.getargspec(func)
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



