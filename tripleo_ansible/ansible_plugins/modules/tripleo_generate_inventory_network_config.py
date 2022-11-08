#!/usr/bin/python
# -*- coding: utf-8 -*-
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

import copy
import traceback
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_generate_inventory_network_config

short_description: Generate network config for ansible inventory

version_added: "2.8"

description:
    - Generates network config that cannot be stored on neutron port resources
      for the ansible inventory.

options:
  instances:
    description:
      - Data describing instances, node instances including networks and
        network_config
    type: list
    elements: dict
    suboptions:
      hostname:
        description:
          - Node hostname
        type: str
      network_config:
        description:
          - Network configuration object
        type: dict
        suboptions:
          default_route_network:
            description:
              - The network to use for the default route
            type: list
            default:
              - ctlplane
          template:
            description:
              - The nic config template
            type: string
            default: templates/net_config_bridge.j2
          dns_search_domains:
            description:
              - A list of DNS search domains to be added (in order) to
                resolv.conf.
            type: list
            default: []
          physical_bridge_name:
            description:
              - An OVS bridge to create for accessing external networks.
            type: string
            default: br-ex
          public_interface_name:
            description:
              - Which interface to add to the public bridge
            type: string
            default: nic1
          network_config_update:
            description:
              - When to apply network configuration changes, allowed values
                are True or False.
            type: boolean
            default: False
          networks_skip_config:
            description:
              - List of networks that should be skipped when configuring node
                networking
            type: list
            default: []
          net_config_data_lookup:
            description:
              - Per node and/or per node group os-net-config nic mapping config
            type: dict
          bond_interface_ovs_options:
            description:
              - The ovs_options or bonding_options string for the bond
                interface. Set things like lacp=active and/or
                bond_mode=balance-slb for OVS bonds or like mode=4 for Linux
                bonds using this option.
            type: string
          num_dpdk_interface_rx_queues:
            description:
              - Number of Rx Queues required for DPDK bond or DPDK ports
            type: int
            default: 1
  hostname_role_map:
    description:
      - Mapping of instance hostnames to role name
    type: dict
author:
    - Harald Jensås <hjensas@redhat.com>
'''

RETURN = '''
Controller:
  hosts:
     overcloud-controller-0:
       template: templates/multiple_nics/multiple_nics.j2
       physical_bridge_name: br-ex
       public_interface_name: nic1
       network_config_update: False
       net_config_data_lookup: {}
       bond_interface_ovs_options: bond_mode=balance-slb
Compute:
  hosts:
     overcloud-compute-0:
       template: templates/multiple_nics/multiple_nics.j2
       physical_bridge_name: br-ex
       public_interface_name: nic1
       network_config_update: False
       net_config_data_lookup: {}
       bond_interface_ovs_options: bond_mode=balance-slb
    overcloud-compute-1:
       template: templates/multiple_nics/multiple_nics.j2
       physical_bridge_name: br-ex
       public_interface_name: nic1
       network_config_update: False
       net_config_data_lookup: {}
       bond_interface_ovs_options: bond_mode=balance-slb
'''

EXAMPLES = '''
- name: Generate network config for ansible inventory
  tripleo_generate_inventory_network_config:
    instances:
      - hostname: overcloud-controller-0
        network_config:
          template: templates/multiple_nics/multiple_nics.j2
          physical_bridge_name: br-ex
          public_interface_name: nic1
          network_config_update: False
          net_config_data_lookup: {}
          bond_interface_ovs_options: bond_mode=balance-slb
      - hostname: overcloud-novacompute-0
        network_config:
          template: templates/multiple_nics/multiple_nics.j2
          physical_bridge_name: br-ex
          public_interface_name: nic1
          network_config_update: False
          net_config_data_lookup: {}
          bond_interface_ovs_options: bond_mode=balance-slb
      - hostname: overcloud-novacompute-1
        network_config:
          template: templates/multiple_nics/multiple_nics.j2
          physical_bridge_name: br-ex
          public_interface_name: nic1
          network_config_update: False
          net_config_data_lookup: {}
          bond_interface_ovs_options: bond_mode=balance-slb
    hostname_role_map:
      overcloud-controller-0: Controller
      overcloud-novacompute-0: Compute
      overcloud-novacompute-1: Compute
'''


def set_network_config_defaults(module_opts, network_config):
    net_config_opts = module_opts['instances']['suboptions']['network_config']
    for k, v in net_config_opts['suboptions'].items():
        default = v.get('default')
        if default is not None:
            network_config.setdefault(k, default)


def translate_opts_for_tripleo_network_config_role(network_config):
    translation_map = dict(
        template='tripleo_network_config_template',
        physical_bridge_name='neutron_physical_bridge_name',
        public_interface_name='neutron_public_interface_name',
        network_config_update=('tripleo_network_config_update'),
        net_config_data_lookup='tripleo_network_config_os_net_config_mappings',
    )

    for key, value in copy.deepcopy(network_config).items():
        if key not in translation_map:
            continue

        new_key = translation_map[key]
        network_config.setdefault(new_key, value)
        network_config.pop(key)


def generate_ansible_inventory_network_config(result, module_opts, instances,
                                              hostname_role_map):
    inventory = result['config']

    roles = set(hostname_role_map.values())

    for role in roles:
        inventory.setdefault(role, dict())
        inventory[role].setdefault('hosts', dict())
        role_vars = inventory[role].setdefault('vars', dict())
        role_vars['tripleo_network_config_hide_sensitive_logs'] = False

    for instance in instances:
        if not instance.get('provisioned', True):
            continue

        hostname = instance['hostname']
        role = hostname_role_map[hostname]
        host = inventory[role]['hosts'].setdefault(hostname.lower(), dict())
        network_config = instance.get('network_config', dict())
        set_network_config_defaults(module_opts, network_config)
        translate_opts_for_tripleo_network_config_role(network_config)
        host.update(network_config)

    # Delete empty roles, i.e no provisioned hosts.
    for role in roles:
        if not inventory[role]['hosts']:
            del inventory[role]

    result['changed'] = True


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
        config=dict(),
    )

    module_opts = yaml.safe_load(DOCUMENTATION)['options']
    argument_spec = openstack_full_argument_spec(**module_opts)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False,
    )

    instances = module.params['instances']
    hostname_role_map = module.params['hostname_role_map']

    try:
        generate_ansible_inventory_network_config(result, module_opts,
                                                  instances, hostname_role_map)

        result['success'] = True
        module.exit_json(**result)
    except Exception:
        result['error'] = traceback.format_exc()
        result['msg'] = ("Error generating ansible inventory network config: "
                         "{}".format(traceback.format_exc().split('\n')[-2]))
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
