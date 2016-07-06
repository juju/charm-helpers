# Copyright 2016 Canonical Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import glob
import yaml

from unittest import TestCase

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'defaults')


class DefaultsTestCase(TestCase):

    def setUp(self):
        super(DefaultsTestCase, self).setUp()

    def get_keys(self, dicto, keys=None):
        if keys is None:
            keys = []

        if dicto:
            if type(dicto) is not dict:
                raise Exception("Unexpected entry: %s" % dicto)

            for key in dicto.keys():
                keys.append(key)
                if type(dicto[key]) is dict:
                    self.get_keys(dicto[key], keys)

        return keys

    def test_defaults(self):
        defaults_paths = glob.glob('%s/*.yaml' % TEMPLATES_DIR)
        for defaults in defaults_paths:
            schema = "%s.schema" % defaults
            self.assertTrue(os.path.exists(schema))
            a = yaml.safe_load(open(schema))
            b = yaml.safe_load(open(defaults))
            if not a and not b:
                continue

            # Test that all keys in default are present in their associated
            # schema.
            skeys = self.get_keys(a)
            dkeys = self.get_keys(b)
            self.assertEqual(set(dkeys).symmetric_difference(skeys), set([]))
