from tests.helpers import FakeRelation
from testtools import TestCase
from mock import MagicMock, patch, call


class TestPeerStorage(TestCase):
    def setUp(self):
        self.relation_get = path