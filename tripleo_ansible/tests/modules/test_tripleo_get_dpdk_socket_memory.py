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

from tripleo_ansible.ansible_plugins.modules import tripleo_get_dpdk_socket_memory as derive_params
from tripleo_ansible.tests import base as tests_base


class TestTripleoGetDpdkSocketMemory(tests_base.TestCase):
    """Test the _get_dpdk_socket_memory method of the OvS DPDK module"""

    def test_run_valid_dpdk_nics_numa_info(self):
        dpdk_nics_numa_info = [{"name": "ens802f1", "numa_node": 1,
                                "mtu": 8192}]
        numa_nodes = [0, 1]
        overhead = 800
        packet_size_in_buffer = (4096 * 64)

        expected_result = "1024,3072"
        result = derive_params._get_dpdk_socket_memory(
            dpdk_nics_numa_info, numa_nodes, overhead,
            packet_size_in_buffer)
        self.assertEqual(result, expected_result)

    def test_run_multiple_mtu_in_same_numa_node(self):
        dpdk_nics_numa_info = [{"name": "ens802f1", "numa_node": 1,
                                "mtu": 1500},
                               {"name": "ens802f2", "numa_node": 1,
                                "mtu": 2048}]
        numa_nodes = [0, 1]
        overhead = 800
        packet_size_in_buffer = (4096 * 64)

        expected_result = "1024,2048"
        result = derive_params._get_dpdk_socket_memory(
            dpdk_nics_numa_info, numa_nodes, overhead, packet_size_in_buffer)
        self.assertEqual(result, expected_result)

    def test_run_duplicate_mtu_in_same_numa_node(self):
        dpdk_nics_numa_info = [{"name": "ens802f1", "numa_node": 1,
                                "mtu": 4096},
                               {"name": "ens802f2", "numa_node": 1,
                                "mtu": 4096}]
        numa_nodes = [0, 1]
        overhead = 800
        packet_size_in_buffer = (4096 * 64)

        expected_result = "1024,2048"
        result = derive_params._get_dpdk_socket_memory(
            dpdk_nics_numa_info, numa_nodes, overhead, packet_size_in_buffer)
        self.assertEqual(result, expected_result)

    def test_run_valid_roundup_mtu(self):
        dpdk_nics_numa_info = [{"name": "ens802f1", "numa_node": 1,
                                "mtu": 1200}]
        numa_nodes = [0, 1]
        overhead = 800
        packet_size_in_buffer = (4096 * 64)

        expected_result = "1024,2048"
        result = derive_params._get_dpdk_socket_memory(
            dpdk_nics_numa_info, numa_nodes, overhead,
            packet_size_in_buffer)
        self.assertEqual(result, expected_result)
