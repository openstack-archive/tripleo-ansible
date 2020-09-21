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

from tripleo_ansible.ansible_plugins.filter import number_list
from tripleo_ansible.tests import base as tests_base


class TestNumberListFilters(tests_base.TestCase):

    def setUp(self):
        super(TestNumberListFilters, self).setUp()
        self.filters = number_list.FilterModule()

    def test_run_with_ranges_in_comma_delimited_str(self):
        range_list = "24-27,60,65-67"
        expected_result = "24,25,26,27,60,65,66,67"
        result = self.filters.number_list(range_list)
        self.assertEqual(result, expected_result)

    def test_run_with_ranges_in_comma_delimited_list(self):
        range_list = ['24-27', '60', '65-67']
        expected_result = "24,25,26,27,60,65,66,67"
        result = self.filters.number_list(range_list)
        self.assertEqual(result, expected_result)

    def test_run_with_ranges_exclude_num(self):
        range_list = "24-27,^25,60,65-67"
        expected_result = "24,26,27,60,65,66,67"
        result = self.filters.number_list(range_list)
        self.assertEqual(result, expected_result)

    def test_run_with_no_ranges(self):
        range_list = "24,25,26,27,60,65,66,67"
        expected_result = "24,25,26,27,60,65,66,67"
        result = self.filters.number_list(range_list)
        self.assertEqual(result, expected_result)

    def test_run_with_empty_input(self):
        range_list = ""
        self.assertRaises(Exception,
                          self.filters.number_list,
                          range_list)

    def test_run_with_invalid_input(self):
        range_list = ",d"
        self.assertRaises(Exception,
                          self.filters.number_list,
                          range_list)

    def test_run_with_invalid_exclude_number(self):
        range_list = "12-15,^17"
        expected_result = "12,13,14,15"
        result = self.filters.number_list(range_list)
        self.assertEqual(result, expected_result)
