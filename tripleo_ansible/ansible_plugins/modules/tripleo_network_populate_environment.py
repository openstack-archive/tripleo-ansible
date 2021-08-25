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
module: tripleo_network_populate_environment

short_description: Create TripleO Composable network deployed environemnt

version_added: "2.8"

description:
    - "Create TripleO Composable network deployed environemnt data"

options:
  net_data:
    description:
      - Structure describing a TripleO composable network
    type: list
  templates:
    description:
      - The path to tripleo-heat-templates root directory
    type: path
    default: /usr/share/openstack-tripleo-heat-templates

author:
    - Harald Jensås <hjensas@redhat.com>
'''

RETURN = '''
net_ip_version_map:
  description:
    - Dictionary mapping network's to ip_version
  returned: always
  type: dict
net_cidr_map:
  description:
    - Dictionary mapping network to cidrs
  returned: always
  type: dict
'''

EXAMPLES = '''
- name: Populate environment
  tripleo_network_populate_environment:
    net_data:
      - name: Baremetal
      - name: External
      - name: InternalApi
        name_lower: internal_api
    templates: /home/stack/tripleo-heat-templates
  register: network_environment
'''


def get_net_ip_version(subnets, net_data):
    ip_versions = {subnet.ip_version for subnet in subnets}

    if {4, 6} == ip_versions:
        # Full dual stack is currently not supported, operator must set
        # ipv6: true in network_data if services on the network should use ipv6
        return 6 if net_data.get('ipv6') is True else 4

    return ip_versions.pop()


def get_net_cidrs(subnets, ip_version):
    return [subnet.cidr for subnet in subnets
            if subnet.ip_version == ip_version]


def get_network_attrs(network):
    return {'name': network.name,
            'mtu': network.mtu,
            'dns_domain': network.dns_domain,
            'tags': network.tags}


def get_subnet_attrs(subnet):
    attrs = {
        'name': subnet.name,
        'cidr': subnet.cidr,
        'gateway_ip': subnet.gateway_ip,
        'host_routes': subnet.host_routes,
        'dns_nameservers': subnet.dns_nameservers,
        'ip_version': subnet.ip_version,
        'tags': subnet.tags,
    }

    return subnet.name, attrs


def get_subnets_attrs(subnets):
    subnets_map = dict()
    for subnet in subnets:
        name, attrs = get_subnet_attrs(subnet)
        subnets_map[name] = attrs

    return subnets_map


def set_composable_network_attrs(module, conn, name_lower, net_data,
                                 attrs=None,
                                 cidr_map=None, ip_version_map=None):
    net = conn.network.find_network(name_lower)
    if net is None:
        msg = ('Failed crating deployed network environment. Network '
               '{} not found'.format(net_data['name']))
        module.fail_json(msg=msg)

    attrs['network'] = get_network_attrs(net)

    subnets = [conn.network.get_subnet(s_id) for s_id in net.subnet_ids]

    ip_version_map[name_lower] = get_net_ip_version(subnets, net_data)
    cidr_map[name_lower] = get_net_cidrs(subnets, ip_version_map[name_lower])
    attrs['subnets'] = get_subnets_attrs(subnets)


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

    networks_data = module.params['net_data']
    templates = module.params['templates']

    try:
        _, conn = openstack_cloud_from_module(module)
        net_ip_version_map = dict()
        net_cidr_map = dict()
        net_attr_map = dict()
        for net_data in networks_data:
            name_lower = net_data.get('name_lower', net_data['name'].lower())
            net_attr_map[name_lower] = dict()

            set_composable_network_attrs(
                module, conn, name_lower, net_data,
                attrs=net_attr_map[name_lower],
                cidr_map=net_cidr_map,
                ip_version_map=net_ip_version_map)

        result['environment'] = {
            'resource_registry': {
                'OS::TripleO::Network':
                    os.path.join(templates, 'network/deployed_networks.yaml'),
            },
            'parameter_defaults': {
                'DeployedNetworkEnvironment': {
                    'net_ip_version_map': net_ip_version_map,
                    'net_cidr_map': net_cidr_map,
                    'net_attributes_map': net_attr_map,
                }
            }
        }
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
