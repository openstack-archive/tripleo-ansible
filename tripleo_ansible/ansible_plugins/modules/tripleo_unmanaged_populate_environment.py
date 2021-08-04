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

import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_unmanaged_populate_environment

short_description: Add unmanaged node to existing heat environment

version_added: "2.8"

description:
    - "Add unmanaged node to existing heat environment"

options:
  environment:
    description:
      - Existing heat environment data to add to
    type: dict
    default: {}
  instances:
    description:
      - List of unmanaged instances
    required: true
    type: list
    elements: dict
  node_port_map:
    description:
      - Structure with port data mapped by node and network, in the format
        returned by the tripleo_overcloud_network_ports module.
    type: dict
    default: {}
  ctlplane_network:
    description:
      - Name of control plane network
    default: ctlplane
    type: str
author:
    - Harald Jensås <hjensas@redhat.com>
'''

RETURN = '''
parameter_defaults:
  FooParam: foo
  DeployedServerPortMap:
    controller-0-ctlplane:
      fixed_ips:
      - ip_address': 1.1.1.1
    compute-0-ctlplane:
      fixed_ips:
      - ip_address': 1.1.1.2
    instance3-ctlplane:
      fixed_ips:
      - ip_address': 1.1.1.3
resource_registry:
  OS::Fake::Resource: /path/to/fake/resource.yaml
'''

EXAMPLES = '''
- name: Populate environment with network port data
  tripleo_unmanaged_populate_environment:
    ctlplane_network: ctlplane
    environment:
      parameter_defaults:
        FooParam: foo
        DeployedServerPortMap:
          instance3-ctlplane:
            fixed_ips:
              - ip_address': 1.1.1.3
      resource_registry:
        OS::Fake::Resource: /path/to/fake/resource.yaml
    instances:
    - hostname: controller-0
      managed: false
      networks:
      - network: ctlplane
        fixed_ip: 1.1.1.1
    - hostname': compute-0
      managed: false
      networks:
      - network: ctlplane
        fixed_ip: 1.1.1.2
    node_port_map:
      controller-0:
        ctlplane:
          ip_address: 1.1.1.1
          ip_subnet: 1.1.1.1/24
          ip_address_uri: 1.1.1.1
      compute-0:
        ctlplane:
          ip_address: 1.1.1.2
          ip_subnet: 1.1.1.2/24
          ip_address_uri: 1.1.1.2
  register: environment
'''


def update_environment(environment, ctlplane_network, node_port_map,
                       instances):
    parameter_defaults = environment.setdefault('parameter_defaults', {})
    port_map = parameter_defaults.setdefault('DeployedServerPortMap', {})
    for instance in instances:
        if instance.get('managed', True):
            continue

        hostname = instance['hostname']
        ip_address = node_port_map[hostname][ctlplane_network]['ip_address']
        ctlplane = {}
        ctlplane['fixed_ips'] = [{'ip_address': ip_address}]
        port_map['%s-%s' % (hostname, ctlplane_network)] = ctlplane


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
    instances = module.params['instances']
    node_port_map = module.params['node_port_map']
    ctlplane_network = module.params['ctlplane_network']

    try:
        update_environment(environment, ctlplane_network, node_port_map,
                           instances)
        result['success'] = True
        module.exit_json(**result)

    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error overcloud network provision failed!")
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
