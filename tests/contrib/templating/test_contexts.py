# Copyright 2013 Canonical Ltd.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
import mock
import os
import shutil
import tempfile
import unittest
import yaml

import six

import charmhelpers.contrib.templating.contexts


class JujuState2YamlTestCase(unittest.TestCase):
    maxDiff = None

    unit_data = {
        'private-address': '10.0.3.2',
        'public-address': '123.123.123.123',
    }

    def setUp(self):
        super(JujuState2YamlTestCase, self).setUp()

        # Hookenv patches (a single patch to hookenv doesn't work):
        patcher = mock.patch('charmhelpers.core.hookenv.config')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.relation_get')
        self.mock_relation_get = patcher.start()
        self.mock_relation_get.return_value = {}
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.relations')
        self.mock_relations = patcher.start()
        self.mock_relations.return_value = {
            'wsgi-file': {},
            'website': {},
            'nrpe-external-master': {},
        }
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.relation_type')
        self.mock_relation_type = patcher.start()
        self.mock_relation_type.return_value = None
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.local_unit')
        self.mock_local_unit = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.relations_of_type')
        self.mock_relations_of_type = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_relations_of_type.return_value = []

        def unit_get_data(argument):
            "dummy unit_get that accesses dummy unit data"
            return self.unit_data[argument]

        patcher = mock.patch(
            'charmhelpers.core.hookenv.unit_get', unit_get_data)
        self.mock_unit_get = patcher.start()
        self.addCleanup(patcher.stop)

        # patches specific to this test class.
        etc_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, etc_dir)
        self.context_path = os.path.join(etc_dir, 'some', 'context')

        patcher = mock.patch.object(charmhelpers.contrib.templating.contexts,
                                    'charm_dir', '/tmp/charm_dir')
        patcher.start()
        self.addCleanup(patcher.stop)

    def default_context(self):
        return {
            "charm_dir": "/tmp/charm_dir",
            "group_code_owner": "webops_deploy",
            "user_code_runner": "ubunet",
            "current_relation": {},
            "relations_full": {
                'wsgi-file': {},
                'website': {},
                'nrpe-external-master': {},
            },
            "relations": {
                'wsgi-file': [],
                'website': [],
                'nrpe-external-master': [],
            },
            "local_unit": "click-index/3",
            "unit_private_address": "10.0.3.2",
            "unit_public_address": "123.123.123.123",
        }

    def test_output_with_empty_relation(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
            self.context_path)

        with open(self.context_path, 'r') as context_file:
            result = yaml.safe_load(context_file.read())
            expected = self.default_context()
            self.assertEqual(expected, result)

    def test_output_with_no_relation(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_local_unit.return_value = "click-index/3"
        self.mock_relation_get.return_value = None

        charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
            self.context_path)

        with open(self.context_path, 'r') as context_file:
            result = yaml.safe_load(context_file.read())
            expected = self.default_context()
            self.assertEqual(expected, result)

    def test_output_with_relation(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_relation_type.return_value = 'wsgi-file'
        self.mock_relation_get.return_value = {
            'relation_key1': 'relation_value1',
            'relation_key2': 'relation_value2',
        }
        self.mock_relations.return_value = {
            'wsgi-file': {
                six.u('wsgi-file:0'): {
                    six.u('gunicorn/1'): {
                        six.u('private-address'): six.u('10.0.3.99'),
                    },
                    'click-index/3': {
                        six.u('wsgi_group'): six.u('ubunet'),
                    },
                },
            },
            'website': {},
            'nrpe-external-master': {},
        }
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
            self.context_path)

        with open(self.context_path, 'r') as context_file:
            result = yaml.safe_load(context_file.read())
            expected = self.default_context()
            expected['current_relation'] = {
                "relation_key1": "relation_value1",
                "relation_key2": "relation_value2",
            }
            expected["wsgi_file:relation_key1"] = "relation_value1"
            expected["wsgi_file:relation_key2"] = "relation_value2"
            expected["relations_full"]['wsgi-file'] = {
                'wsgi-file:0': {
                    'gunicorn/1': {
                        six.u('private-address'): six.u('10.0.3.99')},
                    'click-index/3': {six.u('wsgi_group'): six.u('ubunet')},
                },
            }
            expected["relations"]["wsgi-file"] = [
                {
                    '__relid__': 'wsgi-file:0',
                    '__unit__': 'gunicorn/1',
                    'private-address': '10.0.3.99',
                }
            ]
            self.assertEqual(expected, result)

    def test_relation_with_separator(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_relation_type.return_value = 'wsgi-file'
        self.mock_relation_get.return_value = {
            'relation_key1': 'relation_value1',
            'relation_key2': 'relation_value2',
        }
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
            self.context_path, namespace_separator='__')

        with open(self.context_path, 'r') as context_file:
            result = yaml.safe_load(context_file.read())
            expected = self.default_context()
            expected['current_relation'] = {
                "relation_key1": "relation_value1",
                "relation_key2": "relation_value2",
            }
            expected["wsgi_file__relation_key1"] = "relation_value1"
            expected["wsgi_file__relation_key2"] = "relation_value2"
            self.assertEqual(expected, result)

    def test_keys_with_hyphens(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
            'private-address': '10.1.1.10',
        }
        self.mock_local_unit.return_value = "click-index/3"
        self.mock_relation_get.return_value = None

        charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
            self.context_path)

        with open(self.context_path, 'r') as context_file:
            result = yaml.safe_load(context_file.read())
            expected = self.default_context()
            expected["private-address"] = "10.1.1.10"
            self.assertEqual(expected, result)

    def test_keys_with_hypens_not_allowed_in_keys(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
            'private-address': '10.1.1.10',
        }
        self.mock_local_unit.return_value = "click-index/3"
        self.mock_relation_type.return_value = 'wsgi-file'
        self.mock_relation_get.return_value = {
            'relation-key1': 'relation_value1',
            'relation-key2': 'relation_value2',
        }

        charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
            self.context_path, allow_hyphens_in_keys=False,
            namespace_separator='__')

        with open(self.context_path, 'r') as context_file:
            result = yaml.safe_load(context_file.read())
            expected = self.default_context()
            expected["private_address"] = "10.1.1.10"
            expected["wsgi_file__relation_key1"] = "relation_value1"
            expected["wsgi_file__relation_key2"] = "relation_value2"
            expected['current_relation'] = {
                "relation-key1": "relation_value1",
                "relation-key2": "relation_value2",
            }
            self.assertEqual(expected, result)
