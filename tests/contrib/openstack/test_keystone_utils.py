#!/usr/bin/env python

import unittest

from mock import patch, PropertyMock

import charmhelpers.contrib.openstack.keystone as keystone

TO_PATCH = [
    'apt_install',
    'apt_update',
]


class KeystoneTests(unittest.TestCase):
    def setUp(self):
        for m in TO_PATCH:
            setattr(self, m, self._patch(m))

    def _patch(self, method):
        _m = patch('charmhelpers.contrib.openstack.keystone.' + method)
        mock = _m.start()
        self.addCleanup(_m.stop)
        return mock

    def test_get_keystone_manager(self):
        manager = keystone.get_keystone_manager(
            'test-endpoint', 2, token="12345"
        )
        self.assertTrue(isinstance(manager, keystone.KeystoneManager2))

        manager = keystone.get_keystone_manager(
            'test-endpoint', 3, token="12345")

        self.assertTrue(isinstance(manager, keystone.KeystoneManager3))
        self.assertRaises(ValueError, keystone.get_keystone_manager,
                          'test-endpoint', 4, token="12345")

    def test_resolve_sevice_id_v2(self):
        class ServiceList(list):
            def __iter__(self):
                class Service(object):
                    _info = {
                        'type': 'openstack',
                        'name': "ceilometer",
                        'id': "uuid-uuid",
                    }
                yield Service()

        manager = keystone.get_keystone_manager('test-endpoint', 2,
                                                token="1234")
        manager.api.services.list = PropertyMock(return_value=ServiceList())
        self.assertTrue(manager.service_exists("ceilometer"))
        self.assertFalse(manager.service_exists("barbican"))
        self.assertFalse(manager.service_exists("barbican",
                                                service_type="openstack"))
        self.assertTrue(manager.service_exists("ceilometer",
                                               service_type="openstack"))

    def test_resolve_sevice_id_v3(self):
        class ServiceList(list):
            def __iter__(self):
                class Service(object):
                    _info = {
                        'type': 'openstack',
                        'name': "ceilometer",
                        'id': "uuid-uuid",
                    }
                yield Service()

        manager = keystone.get_keystone_manager('test-endpoint', 3,
                                                token="12345")
        manager.api.services.list = PropertyMock(return_value=ServiceList())
        self.assertTrue(manager.service_exists("ceilometer"))
        self.assertFalse(manager.service_exists("barbican"))
        self.assertFalse(manager.service_exists("barbican",
                                                service_type="openstack"))
        self.assertTrue(manager.service_exists("ceilometer",
                                               service_type="openstack"))

    def test_get_api_suffix(self):
        self.assertEquals(keystone.get_api_suffix(2), "v2.0")
        self.assertEquals(keystone.get_api_suffix(3), "v3")

    def test_format_endpoint(self):
        self.assertEquals(keystone.format_endpoint(
            "http", "10.0.0.5", "5000", 2), "http://10.0.0.5:5000/v2.0/")
