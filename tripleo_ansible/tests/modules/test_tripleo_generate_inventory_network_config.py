# Copyright (c) 2021 OpenStack Foundation
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

from tripleo_ansible.ansible_plugins.modules import (
    tripleo_generate_inventory_network_config as plugin)
from tripleo_ansible.tests import base as tests_base


NETWORK_CONFIG = {
    'template': '/foo/template.j2',
    'net_config_data_lookup': {},
}

INSTANCE_WITH_NETWORK_CONFIG = {
    'hostname': 'instance01',
    'network_config': NETWORK_CONFIG,
}

INSTANCE_WITHOUT_NETWORK_CONFIG = {
    'hostname': 'instance02',
}

UNPROVISIONED_INSTANCE = {
    'hostname': 'instance03',
    'provisioned': False,
    'network_config': NETWORK_CONFIG,
}

FAKE_INSTANCES = [INSTANCE_WITH_NETWORK_CONFIG,
                  INSTANCE_WITHOUT_NETWORK_CONFIG,
                  UNPROVISIONED_INSTANCE]

FAKE_HOSTNAME_ROLE_MAP = {
    'instance01': 'RoleA',
    'instance02': 'RoleB',
    'instance03': 'RoleC',
}


class TestTripleoGenerateInventoryNetworkConfig(tests_base.TestCase):

    def test_generate_ansible_inventory_network_config(self):
        result = {'changed': False, 'config': {}}
        module_opts = yaml.safe_load(plugin.DOCUMENTATION)['options']
        expected_inventory_network_config = {
            'RoleA': {
                'hosts': {
                    'instance01': {
                        'default_route_network': ['ctlplane'],
                        'dns_search_domains': [],
                        'networks_skip_config': [],
                        'neutron_physical_bridge_name': 'br-ex',
                        'neutron_public_interface_name': 'nic1',
                        'num_dpdk_interface_rx_queues': 1,
                        'tripleo_network_config_update': False,
                        'tripleo_network_config_os_net_config_mappings': {},
                        'tripleo_network_config_template': '/foo/template.j2'}
                },
                'vars': {
                    'tripleo_network_config_hide_sensitive_logs': False,
                }
            },
            'RoleB': {
                'hosts': {
                    'instance02': {
                        'default_route_network': ['ctlplane'],
                        'dns_search_domains': [],
                        'networks_skip_config': [],
                        'neutron_physical_bridge_name': 'br-ex',
                        'neutron_public_interface_name': 'nic1',
                        'num_dpdk_interface_rx_queues': 1,
                        'tripleo_network_config_update': False,
                        'tripleo_network_config_template':
                            'templates/net_config_bridge.j2'}},
                'vars': {
                    'tripleo_network_config_hide_sensitive_logs': False,
                }
            }
        }
        plugin.generate_ansible_inventory_network_config(
            result, module_opts, FAKE_INSTANCES, FAKE_HOSTNAME_ROLE_MAP)
        self.assertEqual(expected_inventory_network_config, result['config'])
