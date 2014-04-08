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

import charmhelpers.contrib.templating.contexts


class JujuState2YamlTestCase(unittest.TestCase):

    def setUp(self):
        super(JujuState2YamlTestCase, self).setUp()

        # Hookenv patches (a single patch to hookenv doesn't work):
        patcher = mock.patch('charmhelpers.core.hookenv.config')
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch('charmhelpers.core.hookenv.relation_get')
        # XXX delete
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

        # patches specific to this test class.
        etc_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, etc_dir)
        self.context_path = os.path.join(etc_dir, 'some', 'context')

        patcher = mock.patch.object(charmhelpers.contrib.templating.contexts,
                                    'charm_dir', '/tmp/charm_dir')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_output_with_empty_relation(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_local_unit.return_value = "click-index/3"

        charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
            self.context_path)

        with open(self.context_path, 'r') as context_file:
            result = yaml.load(context_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "relations_deprecated": {},
                "current_relation": {},
                "relations": {
                    'wsgi-file': {},
                    'website': {},
                    'nrpe-external-master': {},
                },
                "local_unit": "click-index/3",
            }, result)

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
            result = yaml.load(context_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "local_unit": "click-index/3",
                "relations_deprecated": {},
                "current_relation": {},
                "relations": {
                    'wsgi-file': {},
                    'website': {},
                    'nrpe-external-master': {},
                }
            }, result)

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
                u'wsgi-file:0': {
                    u'gunicorn/1': {
                        u'private-address': u'10.0.3.99',
                    },
                    'your-wsgi-service/0': {
                        u'wsgi_group': u'ubunet',
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
            result = yaml.load(context_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "wsgi_file:relation_key1": "relation_value1",
                "wsgi_file:relation_key2": "relation_value2",
                "local_unit": "click-index/3",
                "relations_deprecated": {"wsgi_file": []},
                "current_relation": {
                    'wsgi-file': {
                        "relation_key1": "relation_value1",
                        "relation_key2": "relation_value2",
                    }
                },
                "relations": {
                    'wsgi-file': {
                        u'wsgi-file:0': {
                            u'gunicorn/1': {
                                u'private-address': u'10.0.3.99',
                            },
                            'your-wsgi-service/0': {
                                u'wsgi_group': u'ubunet',
                            },
                        },
                    },
                    'website': {},
                    'nrpe-external-master': {},
                },
            }, result)

    def test_output_with_multiple_relations(self):
        self.mock_config.return_value = {
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'ubunet',
        }
        self.mock_relation_type.return_value = 'cluster'
        self.mock_relation_get.return_value = {
            'private-address': '10.0.3.105',
        }
        self.mock_local_unit.return_value = "click-index/3"
        self.mock_relations_of_type.return_value = [{
            u'private-address': u'10.0.3.105',
            '__unit__': u'elasticsearch/1',
            '__relid__': u'cluster:0',
        }, {
            u'private-address': u'10.0.3.107',
            '__unit__': u'elasticsearch/2',
            '__relid__': u'cluster:0',
        }]

        charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
            self.context_path)

        with open(self.context_path, 'r') as context_file:
            result = yaml.load(context_file.read())
            self.assertIn('relations_deprecated', result)
            self.assertIn('cluster', result['relations_deprecated'])
            self.assertEqual([{
                u'private_address': u'10.0.3.105',
                '__unit__': u'elasticsearch/1',
                '__relid__': u'cluster:0',
            }, {
                u'private_address': u'10.0.3.107',
                '__unit__': u'elasticsearch/2',
                '__relid__': u'cluster:0',
            }], result['relations_deprecated']['cluster'])

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
            result = yaml.load(context_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "wsgi_file__relation_key1": "relation_value1",
                "wsgi_file__relation_key2": "relation_value2",
                "local_unit": "click-index/3",
                "relations_deprecated": {"wsgi_file": []},
                "current_relation": {
                    "wsgi-file": {
                        "relation_key1": "relation_value1",
                        "relation_key2": "relation_value2",
                    },
                },
                "relations": {
                    'wsgi-file': {},
                    'website': {},
                    'nrpe-external-master': {},
                }
            }, result)

    def test_updates_existing_values(self):
        """Data stored in the context file is retained.

        This may be helpful so that templates can access information
        from relations outside the current execution environment.
        XXX Remove. As all relation data is avaliable in any hook,
        we're now creating the relations entry whenever a hook is
        run (to avoid having to do any book-keeping for relations
        departing etc.) For the moment, we'll leave the functionality
        on the relations_deprecated property.
        """
        os.makedirs(os.path.dirname(self.context_path))
        with open(self.context_path, 'w+') as context_file:
            context_file.write(yaml.dump({
                'solr:hostname': 'example.com',
                'user_code_runner': 'oldvalue',
                'relations_deprecated': {
                    'website': [{u'private_address': u'10.0.3.107'}],
                }
            }))

        self.mock_config.return_value = charmhelpers.core.hookenv.Serializable({
            'group_code_owner': 'webops_deploy',
            'user_code_runner': 'newvalue',
        })
        self.mock_local_unit.return_value = "click-index/3"
        self.mock_relation_type.return_value = 'cluster'
        self.mock_relations_of_type.return_value = [{
            u'private-address': u'10.0.3.105',
        }]
        self.mock_relation_get.return_value = {
            u'private-address': u'10.0.3.105',
        }

        charmhelpers.contrib.templating.contexts.juju_state_to_yaml(
            self.context_path)

        with open(self.context_path, 'r') as context_file:
            result = yaml.load(context_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "newvalue",
                "local_unit": "click-index/3",
                "solr:hostname": "example.com",
                "cluster:private_address": "10.0.3.105",
                "relations_deprecated": {
                    'website': [{u'private_address': u'10.0.3.107'}],
                    'cluster': [{u'private_address': u'10.0.3.105'}],
                },
                "current_relation": {
                    'cluster': {
                        'private-address': '10.0.3.105',
                    },
                },
                "relations": {
                    'wsgi-file': {},
                    'website': {},
                    'nrpe-external-master': {},
                }
            }, result)

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
            result = yaml.load(context_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "relations_deprecated": {},
                'current_relation': {},
                "relations": {
                    'wsgi-file': {},
                    'website': {},
                    'nrpe-external-master': {},
                },
                "local_unit": "click-index/3",
                "private-address": "10.1.1.10",
            }, result)

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
            result = yaml.load(context_file.read())
            self.assertEqual({
                "charm_dir": "/tmp/charm_dir",
                "group_code_owner": "webops_deploy",
                "user_code_runner": "ubunet",
                "local_unit": "click-index/3",
                "relations_deprecated": {"wsgi_file": []},
                'current_relation': {
                    'wsgi-file': {
                        'relation-key1': 'relation_value1',
                        'relation-key2': 'relation_value2',
                    },
                },
                "relations": {
                    'wsgi-file': {},
                    'website': {},
                    'nrpe-external-master': {},
                },
                "private_address": "10.1.1.10",
                "wsgi_file__relation_key1": "relation_value1",
                "wsgi_file__relation_key2": "relation_value2",
            }, result)
