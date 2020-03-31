# Copyright 2020 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os

from tripleo_ansible.ansible_plugins.filter import tripleo_inventory
from tripleo_ansible.tests import base as tests_base

static_inventory = """
overcloud:
  children:
    allovercloud: {}
allovercloud:
  children:
    Compute: {}
    Controller: {}
  vars: {}
Controller:
  hosts:
    overcloud-controller-0: {foo_bar: baz}
  vars:
    tripleo_role_name: Controller
Compute:
  hosts:
    overcloud-novacompute-0: {foo_bar: baz}
  vars:
    tripleo_role_name: Compute
"""

dynamic_inventory = """
{
  "overcloud": {
    "children": [ "allovercloud" ]
  },
  "allovercloud": {
    "children": [ "Compute", "Controller" ],
    "vars" : {}
  },
  "Controller" : {
    "hosts": [ "overcloud-controller-0" ],
    "vars": { "tripleo_role_name": "Controller" }
  },
  "Compute" : {
    "hosts": ["overcloud-novacompute-0" ],
    "vars": { "tripleo_role_name": "Compute" }
  }
}
"""


class TestInventoryFilters(tests_base.TestCase):

    def setUp(self):
        super(TestInventoryFilters, self).setUp()

    def _test_hostmap(self, inventory):
        expected = {
          "Compute": ["overcloud-novacompute-0"],
          "Controller": ["overcloud-controller-0"],
          "overcloud": ["overcloud-controller-0", "overcloud-novacompute-0"],
          "allovercloud": ["overcloud-controller-0", "overcloud-novacompute-0"],
        }
        result = tripleo_inventory.to_inventory_hostmap(inventory)
        self.assertEqual(expected, result)

    def test_hostmap_static(self):
        self._test_hostmap(static_inventory)

    def test_hostmap_dynamic(self):
        self._test_hostmap(dynamic_inventory)

    def _test_roles(self, inventory):
        expected = ["Compute", "Controller"]
        result = tripleo_inventory.to_inventory_roles(inventory)
        self.assertEqual(expected, result)

    def test_roles_static(self):
        self._test_roles(static_inventory)

    def test_roles_dynamic(self):
        self._test_roles(dynamic_inventory)
