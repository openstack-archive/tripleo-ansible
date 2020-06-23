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

try:
    from ansible.module_utils import tripleo_common_utils as tc
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import tripleo_common_utils as tc
from tripleo_ansible.ansible_plugins.filter import range_list
from tripleo_ansible.tests import base as tests_base


class TestRangeListFilters(tests_base.TestCase):

    def setUp(self):
        super(TestRangeListFilters, self).setUp()
        self.filters = range_list.FilterModule()

    def test_run_with_ranges(self):
        num_list = "0,22,23,24,25,60,65,66,67"
        expected_result = "0,22-25,60,65-67"
        result = self.filters.range_list(num_list)
        self.assertEqual(result, expected_result)

    def test_run_with_no_range(self):
        num_list = "0,22,24,60,65,67"
        expected_result = "0,22,24,60,65,67"
        result = self.filters.range_list(num_list)
        self.assertEqual(result, expected_result)

    def test_run_with_empty_input(self):
        num_list = ""
        self.assertRaises(tc.DeriveParamsError,
                          self.filters.range_list, num_list)

    def test_run_with_invalid_input(self):
        num_list = ",d"
        self.assertRaises(tc.DeriveParamsError,
                          self.filters.range_list, num_list)
