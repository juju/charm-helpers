''' General helper functions for tests '''
from contextlib import contextmanager
from mock import patch, MagicMock
import io

import six
if not six.PY3:
    builtin_open = '__builtin__.open'
else:
    builtin_open = 'builtins.open'


@contextmanager
def patch_open():
    '''Patch open() to allow mocking both open() itself and the file that is
    yielded.

    Yields the mock for "open" and "file", respectively.'''
    mock_open = MagicMock(spec=open)
    mock_file = MagicMock(spec=io.FileIO)

    @contextmanager
    def stub_open(*args, **kwargs):
        mock_open(*args, **kwargs)
        yield mock_file

    with patch(builtin_open, stub_open):
        yield mock_open, mock_file


@contextmanager
def mock_open(filename, contents=None):
    ''' Slightly simpler mock of open to return contents for filename '''
    def mock_file(name, mode='r', buffering=-1):  # Python 2 signature.
        if name == filename:
            if (not six.PY3) or 'b' in mode:
                return io.BytesIO(contents)
            return io.StringIO(contents)
        else:
            return open(name, mode, buffering)

    with patch(builtin_open, mock_file):
        yield


class FakeRelation(object):
    '''
    A fake relation class. Lets tests specify simple relation data
    for a default relation + unit (foo:0, foo/0, set in setUp()), eg:

        rel = {
            'private-address': 'foo',
            'password': 'passwd',
        }
        relation = FakeRelation(rel)
        self.relation_get.side_effect = relation.get
        passwd = self.relation_get('password')

    or more complex relations meant to be addressed by explicit relation id
    + unit id combos:

        rel = {
            'mysql:0': {
                'mysql/0': {
                    'private-address': 'foo',
                    'password': 'passwd',
                }
            }
        }
        relation = FakeRelation(rel)
        self.relation_get.side_affect = relation.get
        passwd = self.relation_get('password', rid='mysql:0', unit='mysql/0')
    '''
    def __init__(self, relation_data):
        self.relation_data = relation_data

    def get(self, attribute=None, unit=None, rid=None):
        if not rid or rid == 'foo:0':
            if attribute is None:
                return self.relation_data
            elif attribute in self.relation_data:
                return self.relation_data[attribute]
            return None
        else:
            if rid not in self.relation_data:
                return None
            try:
                relation = self.relation_data[rid][unit]
            except KeyError:
                return None
            if attribute and attribute in relation:
                    return relation[attribute]
            return relation

    def relation_ids(self, relation=None):
        return self.relation_data.keys()

    def related_units(self, relid=None):
        try:
            return self.relation_data[relid].keys()
        except KeyError:
            return []

    def relation_units(self, relation_id):
        if relation_id not in self.relation_data:
            return None
        return self.relation_data[relation_id].keys()
