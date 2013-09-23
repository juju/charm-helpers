''' General helper functions for tests '''
from contextlib import contextmanager
from mock import patch, MagicMock
import io


@contextmanager
def patch_open():
    '''Patch open() to allow mocking both open() itself and the file that is
    yielded.

    Yields the mock for "open" and "file", respectively.'''
    mock_open = MagicMock(spec=open)
    mock_file = MagicMock(spec=file)

    @contextmanager
    def stub_open(*args, **kwargs):
        mock_open(*args, **kwargs)
        yield mock_file

    with patch('__builtin__.open', stub_open):
        yield mock_open, mock_file


@contextmanager
def mock_open(filename, contents=None):
    ''' Slightly simpler mock of open to return contents for filename '''
    def mock_file(*args):
        if args[0] == filename:
            return io.StringIO(contents)
        else:
            return open(*args)
    with patch('__builtin__.open', mock_file):
        yield
