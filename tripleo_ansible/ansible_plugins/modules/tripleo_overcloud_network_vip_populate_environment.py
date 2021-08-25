#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2021 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2021 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

import os
import yaml

try:
    from ansible.module_utils import network_data_v2 as n_utils
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import network_data_v2 as n_utils  # noqa
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
module: tripleo_overcloud_network_vip_populate_environment

short_description: Extract information on provisioned overcloud Virtual IPs

version_added: "2.8"

description:
    - Extract information about provisioned network Virtual IP resources in
      overcloud heat stack.

options:
  stack_name:
    description:
      - Name of the overcloud heat stack
    type: str
  vip_data:
    description:
      - Dictionary of network Virtual IP definitions
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Virtual IP name (optional)
        type: str
      network:
        description:
          - Neutron Network name
        type: str
        required: True
      ip_address:
        description:
          - IP address (Optional)
        type: str
      subnet:
        description:
          - Neutron Subnet name (Optional)
        type: str
      dns_name:
        description:
          - Dns Name (Optional)
        type: str
        required: True
  templates:
    description:
      - The path to tripleo-heat-templates root directory
    type: path
    default: /usr/share/openstack-tripleo-heat-templates

author:
    - Harald Jensås <hjensas@redhat.com>
'''

RETURN = '''
env:

'''

EXAMPLES = '''
- name: Get Overcloud Virtual IPs data
  tripleo_overcloud_network_vip_populate_environment:
    stack_name: overcloud
  register: overcloud_vip_env
- name: Write Virtual IPs environment to output file
  copy:
    content: "{{ overcloud_vip_env.vip_env | to_yaml }}"
    dest: /path/overcloud_vip_env.yaml
'''

REGISTRY_KEY_TPL = 'OS::TripleO::Network::Ports::{net_name}VipPort'
PORT_PATH_TPL = 'network/ports/deployed_vip_{net_name_lower}.yaml'


def get_net_name_map(conn):
    _map = {}

    networks = list(conn.network.networks())
    if not networks:
        raise Exception('Unable to create vip environment. No networks found')

    for network in networks:
        tags = n_utils.tags_to_dict(network.tags)
        try:
            _map[network.name] = tags['tripleo_network_name']
        except KeyError:
            # Hard code the ControlPlane resource which is static in
            # THT/overcloud-resource-registry-puppet.j2.yaml
            if network.name == 'ctlplane':
                _map[network.name] = 'ControlPlane'

    return _map


def add_ctlplane_vip_to_env(conn, ctlplane_vip_data, port):
    network = conn.network.get_network(port.network_id)
    subnet = conn.network.get_subnet(port.fixed_ips[0]['subnet_id'])
    ctlplane_vip_data['network'] = dict()
    ctlplane_vip_data['network']['tags'] = network.tags
    ctlplane_vip_data['subnets'] = list()
    ctlplane_vip_data['subnets'].append({'ip_version': subnet.ip_version})
    ctlplane_vip_data['fixed_ips'] = [{'ip_address': x['ip_address']}
                                      for x in port.fixed_ips]
    ctlplane_vip_data['name'] = port.name


def add_vip_to_env(conn, vip_port_map, port, net_name_lower):
    subnet = conn.network.get_subnet(port.fixed_ips[0]['subnet_id'])

    vip_port = vip_port_map[net_name_lower] = {}
    vip_port['ip_address'] = port.fixed_ips[0]['ip_address']
    vip_port['ip_address_uri'] = n_utils.wrap_ipv6(
        port.fixed_ips[0]['ip_address'])
    vip_port['ip_subnet'] = '/'.join([port.fixed_ips[0]['ip_address'],
                                      subnet.cidr.split('/')[1]])


def populate_net_vip_env(conn, stack, net_maps, vip_data, env, templates):
    low_up_map = get_net_name_map(conn)

    resource_reg = env['resource_registry'] = {}
    param_defaults = env['parameter_defaults'] = {}
    vip_port_map = param_defaults['VipPortMap'] = {}
    ctlplane_vip_data = param_defaults['ControlPlaneVipData'] = {}
    for vip_spec in vip_data:
        net_name_lower = vip_spec['network']
        try:
            port = next(conn.network.ports(
                network_id=net_maps['by_name'][net_name_lower]['id'],
                tags=['tripleo_stack_name={}'.format(stack),
                      'tripleo_vip_net={}'.format(net_name_lower)]))
        except StopIteration:
            raise Exception('Neutron port for Virtual IP spec {} not '
                            'found'.format(vip_spec))

        resource_reg[REGISTRY_KEY_TPL.format(
            net_name=low_up_map[net_name_lower])] = os.path.join(
            templates, PORT_PATH_TPL.format(net_name_lower=net_name_lower))

        if net_name_lower == 'ctlplane':
            add_ctlplane_vip_to_env(conn, ctlplane_vip_data, port)
        else:
            add_vip_to_env(conn, vip_port_map, port, net_name_lower)


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
        env=dict()
    )

    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=False,
        **openstack_module_kwargs()
    )

    stack = module.params['stack_name']
    vip_data = module.params['vip_data']
    templates = module.params['templates']

    try:
        _, conn = openstack_cloud_from_module(module)
        net_maps = n_utils.create_name_id_maps(conn)
        populate_net_vip_env(conn, stack, net_maps, vip_data, result['env'],
                             templates)

        result['changed'] = True if result['env'] else False
        result['success'] = True if result['env'] else False
        module.exit_json(**result)
    except Exception as err:
        result['error'] = err
        result['msg'] = ("Error getting Virtual IPs data from overcloud stack "
                         "{stack_name}: %{error}".format(stack_name=stack,
                                                         error=err))
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
