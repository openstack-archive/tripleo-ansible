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

import yaml

from tripleo_ansible.ansible_plugins.modules import tripleo_get_dpdk_core_list as derive_params
from tripleo_ansible.tests import base as tests_base


class TestTripleoGetDpdkCoreList(tests_base.TestCase):
    """Test the _get_dpdk_core_list method of the OvS DPDK module"""

    def test_run(self):
        inspect_data = {
            "numa_topology": {
                "cpus": [{"cpu": 21, "numa_node": 1,
                          "thread_siblings": [38, 82]},
                         {"cpu": 27, "numa_node": 0,
                          "thread_siblings": [20, 64]},
                         {"cpu": 3, "numa_node": 1,
                          "thread_siblings": [25, 69]},
                         {"cpu": 20, "numa_node": 0,
                          "thread_siblings": [15, 59]},
                         {"cpu": 17, "numa_node": 1,
                          "thread_siblings": [34, 78]},
                         {"cpu": 16, "numa_node": 0,
                          "thread_siblings": [11, 55]}]
                }
            }

        numa_nodes_cores_count = [2, 1]

        expected_result = [20, 64, 15, 59, 38, 82]

        result = derive_params._get_dpdk_core_list(inspect_data,
                                                   numa_nodes_cores_count)
        self.assertEqual(result, expected_result)

    def test_run_invalid_inspect_data(self):
        inspect_data = {"numa_topology": {"cpus": []}}

        numa_nodes_cores_count = [2, 1]

        expected_result = 'Introspection data does not have numa_topology.cpus'

        result = derive_params._get_dpdk_core_list(inspect_data,
                                                   numa_nodes_cores_count)
        self.assertEqual(result, expected_result)

    def test_run_invalid_numa_nodes_cores_count(self):
        inspect_data = {"numa_topology": {
            "cpus": [{"cpu": 21, "numa_node": 1, "thread_siblings": [38, 82]},
                     {"cpu": 27, "numa_node": 0, "thread_siblings": [20, 64]}]
            }}

        numa_nodes_cores_count = []
        expected_result = ('CPU physical cores count for each NUMA nodes '
                           'is not available')

        result = derive_params._get_dpdk_core_list(inspect_data,
                                                   numa_nodes_cores_count)
        self.assertEqual(result, expected_result)
