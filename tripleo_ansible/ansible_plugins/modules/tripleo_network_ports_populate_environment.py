#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 OpenStack Foundation
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
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_network_ports_populate_environment

short_description: Create TripleO network port environment

version_added: "2.8"

description:
    - "Create TripleO network port environment by extending the beremetal environment"

options:
  environment:
    description:
      - Existing heat environment data to add to
    type: dict
    default: {}
  role_net_map:
    description:
      - Structure with role network association
    type: dict
    default: {}
  node_port_map:
    description:
      - Structure with port data mapped by node and network
    type: dict
    default: {}
  templates:
    description:
      - The path to tripleo-heat-templates root directory
    type: path
    default: /usr/share/openstack-tripleo-heat-templates

author:
    - Harald Jensås <hjensas@redhat.com>
'''

RETURN = '''
'''

EXAMPLES = '''
- name: Populate environment with network port data
  tripleo_network_ports_populate_environment:
    environment: {}
    role_net_map:
      Controller:
        - external
        - internal_api
        - storage
        - tenant
      Compute:
        - internal_api
        - storage
        - tenant
    node_port_map:
      controller-0:
        internal_api:
          ip_address: 172.18.0.9
          ip_subnet: 172.18.0.9/24
          ip_address_uri: 172.18.0.9
        tenant:
          ip_address: 172.19.0.9
          ip_subnet: 172.19.0.9/24
          ip_address_uri: 172.19.0.9
      compute-0:
        internal_api:
          ip_address: 172.18.0.15
          ip_subnet: 172.18.0.15/24
          ip_address_uri: 172.18.0.15
        tenant:
          ip_address: 172.19.0.15
          ip_subnet: 172.19.0.15/24
          ip_address_uri: 172.19.0.15
  register: environment
'''


CTLPLANE_NETWORK = 'ctlplane'
REGISTRY_KEY_TPL = 'OS::TripleO::{role}::Ports::{net_name}Port'
PORT_PATH_TPL = 'network/ports/deployed_{net_name_lower}.yaml'


def get_net_name_map(conn, role_net_map):
    _map = {}
    networks = set()

    for role, nets in role_net_map.items():
        networks.update(nets)

    for name_lower in networks:
        if name_lower == CTLPLANE_NETWORK:
            _map[name_lower] = name_lower
            continue

        net = conn.network.find_network(name_or_id=name_lower)
        if not net:
            raise Exception('Network {} not found'.format(name_lower))

        name_upper = [x.split('=').pop() for x in net.tags
                      if x.startswith('tripleo_network_name')]

        if not name_upper:
            raise Exception(
                'Unable to find network name for network with name_lower: {}, '
                'please make sure the network tag tripleo_network_name'
                '=$NET_NAME is set.'.format(name_lower))

        _map[name_lower] = name_upper.pop()

    return _map


def update_environment(environment, node_port_map, role_net_map, net_name_map,
                       templates):
    resource_registry = environment.setdefault('resource_registry', {})
    parameter_defaults = environment.setdefault('parameter_defaults', {})

    for role, nets in role_net_map.items():
        for net in nets:
            if net == CTLPLANE_NETWORK:
                continue

            registry_key = REGISTRY_KEY_TPL.format(role=role,
                                                   net_name=net_name_map[net])
            template_path = os.path.join(
                templates, PORT_PATH_TPL.format(net_name_lower=net))
            resource_registry.update({registry_key: template_path})

    _map = parameter_defaults.setdefault('NodePortMap', {})
    _map.update(node_port_map)


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
        environment={},
    )

    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=False,
        **openstack_module_kwargs()
    )

    environment = result['environment'] = module.params['environment']
    role_net_map = module.params['role_net_map']
    node_port_map = module.params['node_port_map']
    templates = module.params['templates']

    try:
        _, conn = openstack_cloud_from_module(module)

        net_name_map = get_net_name_map(conn, role_net_map)
        update_environment(environment, node_port_map, role_net_map,
                           net_name_map, templates)

        result['success'] = True

        module.exit_json(**result)

    except Exception as err:
        result['error'] = str(err)
        result['msg'] = "Error overcloud network provision failed!"
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
