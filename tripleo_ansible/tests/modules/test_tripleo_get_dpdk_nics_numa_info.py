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

try:
    from ansible.module_utils import tripleo_common_utils as tc
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import tripleo_common_utils as tc
from tripleo_ansible.ansible_plugins.modules import tripleo_get_dpdk_nics_numa_info as derive_params
from tripleo_ansible.tests import base as tests_base


class TestTripleoGetDpdkNicsNumaInfo(tests_base.TestCase):
    """Test the _get_dpdk_nics_numa_info method of the OvS DPDK module"""

    def test_run_dpdk_port(self):
        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge",
            "addresses": [{"ip_netmask": ""}]}]

        inspect_data = {
            "numa_topology": {
                "nics": [{"name": "ens802f1", "numa_node": 1},
                         {"name": "ens802f0", "numa_node": 1},
                         {"name": "eno1", "numa_node": 0},
                         {"name": "eno2", "numa_node": 0},
                         {"name": "enp12s0f1", "numa_node": 0},
                         {"name": "enp12s0f0", "numa_node": 0},
                         {"name": "enp13s0f0", "numa_node": 0},
                         {"name": "enp13s0f1", "numa_node": 0}]
                },
            "inventory": {
                "interfaces": [{"has_carrier": True,
                                "name": "ens802f1"},
                               {"has_carrier": True,
                                "name": "ens802f0"},
                               {"has_carrier": True,
                                "name": "eno1"},
                               {"has_carrier": True,
                                "name": "eno2"},
                               {"has_carrier": True,
                                "name": "enp12s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }

        expected_result = [{'bridge_name': 'br-link', 'name': 'ens802f1',
                            'mtu': 8192, 'numa_node': 1,
                            'addresses': [{'ip_netmask': ''}]}]

        result = derive_params._get_dpdk_nics_numa_info(network_configs,
                                                        inspect_data)
        self.assertEqual(result, expected_result)

    def test_run_dpdk_bond(self):
        network_configs = [{
            "members": [{"type": "ovs_dpdk_bond", "name": "dpdkbond0",
                         "mtu": 9000, "rx_queue": 4,
                         "members": [{"type": "ovs_dpdk_port",
                                      "name": "dpdk0",
                                      "members": [{"type": "interface",
                                                   "name": "nic4"}]},
                                     {"type": "ovs_dpdk_port",
                                      "name": "dpdk1",
                                      "members": [{"type": "interface",
                                                   "name": "nic5"}]}]}],
            "name": "br-link",
            "type": "ovs_user_bridge",
            "addresses": [{"ip_netmask": "172.16.10.0/24"}]}]
        inspect_data = {
            "numa_topology": {
                "nics": [{"name": "ens802f1", "numa_node": 1},
                         {"name": "ens802f0", "numa_node": 1},
                         {"name": "eno1", "numa_node": 0},
                         {"name": "eno2", "numa_node": 0},
                         {"name": "enp12s0f1", "numa_node": 0},
                         {"name": "enp12s0f0", "numa_node": 0},
                         {"name": "enp13s0f0", "numa_node": 0},
                         {"name": "enp13s0f1", "numa_node": 0}]
                },
            "inventory": {
                "interfaces": [{"has_carrier": True,
                                "name": "ens802f1"},
                               {"has_carrier": True,
                                "name": "ens802f0"},
                               {"has_carrier": True,
                                "name": "eno1"},
                               {"has_carrier": True,
                                "name": "eno2"},
                               {"has_carrier": True,
                                "name": "enp12s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }
        expected_result = [{'bridge_name': 'br-link', 'mtu': 9000,
                            'numa_node': 1, 'name': 'ens802f0',
                            'addresses': [{'ip_netmask': '172.16.10.0/24'}]},
                           {'bridge_name': 'br-link', 'mtu': 9000,
                            'numa_node': 1, 'name': 'ens802f1',
                            'addresses': [{'ip_netmask': '172.16.10.0/24'}]}]

        result = derive_params._get_dpdk_nics_numa_info(network_configs,
                                                        inspect_data)
        self.assertEqual(result, expected_result)

    def test_run_no_inspect_nics(self):

        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]

        inspect_data = {
            "numa_topology": {
                "nics": []
                },
            "inventory": {
                "interfaces": [{"has_carrier": True,
                                "name": "ens802f1"},
                               {"has_carrier": True,
                                "name": "ens802f0"},
                               {"has_carrier": True,
                                "name": "eno1"},
                               {"has_carrier": True,
                                "name": "eno2"},
                               {"has_carrier": True,
                                "name": "enp12s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }
        self.assertRaises(tc.DeriveParamsError,
                          derive_params._get_dpdk_nics_numa_info,
                          network_configs, inspect_data)

    def test_run_no_inspect_interfaces(self):

        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]

        inspect_data = {
            "numa_topology": {
                "nics": []
                },
            "inventory": {
                "interfaces": []
                }
            }
        self.assertRaises(tc.DeriveParamsError,
                          derive_params._get_dpdk_nics_numa_info,
                          network_configs, inspect_data)

    def test_run_no_inspect_active_interfaces(self):

        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]

        inspect_data = {
            "numa_topology": {
                "nics": [{"name": "ens802f1", "numa_node": 1},
                         {"name": "ens802f0", "numa_node": 1},
                         {"name": "eno1", "numa_node": 0},
                         {"name": "eno2", "numa_node": 0},
                         {"name": "enp12s0f1", "numa_node": 0},
                         {"name": "enp12s0f0", "numa_node": 0},
                         {"name": "enp13s0f0", "numa_node": 0},
                         {"name": "enp13s0f1", "numa_node": 0}]
                },
            "inventory": {
                "interfaces": [{"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }

        self.assertRaises(tc.DeriveParamsError,
                          derive_params._get_dpdk_nics_numa_info,
                          network_configs, inspect_data)

    def test_run_no_numa_node(self):
        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]

        inspect_data = {
            "numa_topology": {
                "nics": [{"name": "ens802f1"},
                         {"name": "ens802f0", "numa_node": 1},
                         {"name": "eno1", "numa_node": 0},
                         {"name": "eno2", "numa_node": 0},
                         {"name": "enp12s0f1", "numa_node": 0},
                         {"name": "enp12s0f0", "numa_node": 0},
                         {"name": "enp13s0f0", "numa_node": 0},
                         {"name": "enp13s0f1", "numa_node": 0}]
                },
            "inventory": {
                "interfaces": [{"has_carrier": True,
                                "name": "ens802f1"},
                               {"has_carrier": True,
                                "name": "ens802f0"},
                               {"has_carrier": True,
                                "name": "eno1"},
                               {"has_carrier": True,
                                "name": "eno2"},
                               {"has_carrier": True,
                                "name": "enp12s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }

        self.assertRaises(tc.DeriveParamsError,
                          derive_params._get_dpdk_nics_numa_info,
                          network_configs, inspect_data)
