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
module: tripleo_overcloud_network_extract

short_description: Extract information on provisioned overcloud networks

version_added: "2.8"

description:
    - "Extract information about provisioned network resource in overcloud heat stack."

options:
  stack_name:
    description:
      - Name of the overcloud heat stack
    type: str
author:
    - Harald Jensås <hjensas@redhat.com>
'''

RETURN = '''
network_data:
    description: Overcloud networks data
    returned: always
    type: list
    sample:
      - name: Storage
        name_lower: storage
        mtu: 1440
        dns_domain: storage.localdomain.
        vip: true
        subnets:
          storage:
            ip_subnet: '172.18.0.0/24'
            allocation_pools:
            - {'end': '172.18.0.250', 'start': '172.18.0.10'}
            gateway_ip: '172.18.0.254'
            ipv6_subnet: 'fd00:fd00:fd00:2000::/64'
            ipv6_allocation_pools:
            - {'end': 'fd00:fd00:fd00:2000:ffff:ffff:ffff:fffe', 'start': 'fd00:fd00:fd00:2000::10'}
            gateway_ipv6: 'fd00:fd00:fd00:2000::1'
            routes:
              - destination: 172.18.1.0/24
                nexthop: 172.18.0.254
            routes_ipv6:
              - destination: 'fd00:fd00:fd00:2001::/64'
                nexthop: 'fd00:fd00:fd00:2000::1'
            vlan: 10
            physical_network: storage
          storage_leaf1:
            vlan: 21
            ip_subnet: '172.18.1.0/24'
            allocation_pools:
            - {'end': '172.18.1.250', 'start': '172.18.1.10'}
            gateway_ip: '172.18.1.254'
            ipv6_subnet: 'fd00:fd00:fd00:2001::/64'
            ipv6_allocation_pools:
            - {'end': 'fd00:fd00:fd00:2001:ffff:ffff:ffff:fffe', 'start': 'fd00:fd00:fd00:2001::10'}
            gateway_ipv6: 'fd00:fd00:fd00:2001::1'
            routes:
              - destination: 172.18.0.0/24
                nexthop: 172.18.1.254
            routes_ipv6:
              - destination: 'fd00:fd00:fd00:2000::/64'
                nexthop: 'fd00:fd00:fd00:2001::1'
            vlan: 20
            physical_network: storage_leaf1
'''

EXAMPLES = '''
- name: Get Overcloud networks data
  tripleo_overcloud_network_extract:
    stack_name: overcloud
  register: overcloud_network_data
- name: Write netowork data to output file
  copy:
    content: "{{ overcloud_network_data.network_data | to_yaml }}"
    dest: /path/exported-network-data.yaml
'''


DEFAULT_NETWORK_MTU = 1500
DEFAULT_NETWORK_SHARED = False
DEFAULT_NETWORK_ADMIN_STATE_UP = False
DEFAULT_NETWORK_TYPE = 'flat'
DEFAULT_NETWORK_VIP = False
DEFAULT_SUBNET_DHCP_ENABLED = False
DEFAULT_SUBNET_IPV6_ADDRESS_MODE = None
DEFAULT_SUBNET_IPV6_RA_MODE = None


def is_vip_network(conn, network_id):
    network = conn.network.get_network(network_id)
    return (network.tags is not None and 'tripleo_vip=True' in network.tags)


def get_network_info(conn, network_id):

    def pop_defaults(_dict):
        if _dict['mtu'] == DEFAULT_NETWORK_MTU:
            _dict.pop('mtu')
        if _dict['shared'] == DEFAULT_NETWORK_SHARED:
            _dict.pop('shared')
        if _dict['admin_state_up'] == DEFAULT_NETWORK_ADMIN_STATE_UP:
            _dict.pop('admin_state_up')
        if _dict['vip'] == DEFAULT_NETWORK_VIP:
            _dict.pop('vip')
        if _dict['dns_domain'] is None:
            _dict.pop('dns_domain')

    network = conn.network.get_network(network_id)
    tag_dict = n_utils.tags_to_dict(network.tags)

    net_dict = {
        'name_lower': network.name,
        'dns_domain': network.dns_domain,
        'mtu': network.mtu,
        'shared': network.is_shared,
        'admin_state_up': network.is_admin_state_up,
        'vip': is_vip_network(conn, network.id),
    }

    if 'tripleo_service_net_map_replace' in tag_dict:
        net_dict.update({
            'service_net_map_replace':
                tag_dict['tripleo_service_net_map_replace']
        })

    pop_defaults(net_dict)

    return tag_dict['tripleo_net_idx'], net_dict


def get_subnet_info(conn, subnet_id):

    def pop_defaults(_dict):
        if _dict['enable_dhcp'] == DEFAULT_SUBNET_DHCP_ENABLED:
            _dict.pop('enable_dhcp')
        if _dict['network_type'] == DEFAULT_NETWORK_TYPE:
            _dict.pop('network_type')
        if _dict['vlan'] is None:
            _dict.pop('vlan')
        if _dict['segmentation_id'] is None:
            _dict.pop('segmentation_id')

        try:
            if _dict['ipv6_address_mode'] == DEFAULT_SUBNET_IPV6_ADDRESS_MODE:
                _dict.pop('ipv6_address_mode')
        except KeyError:
            pass

        try:
            if _dict['ipv6_ra_mode'] == DEFAULT_SUBNET_IPV6_RA_MODE:
                _dict.pop('ipv6_ra_mode')
        except KeyError:
            pass

    subnet = conn.network.get_subnet(subnet_id)
    segment = conn.network.get_segment(subnet.segment_id)
    tag_dict = n_utils.tags_to_dict(subnet.tags)
    subnet_name = subnet.name

    subnet_dict = {
        'enable_dhcp': subnet.is_dhcp_enabled,
        'vlan': (int(tag_dict['tripleo_vlan_id'])
                 if tag_dict.get('tripleo_vlan_id') else None),
        'physical_network': segment.physical_network,
        'network_type': segment.network_type,
        'segmentation_id': segment.segmentation_id,
    }

    if subnet.ip_version == 4:
        subnet_dict.update({
            'ip_subnet': subnet.cidr,
            'allocation_pools': subnet.allocation_pools,
            'routes': subnet.host_routes,
        })

        if subnet.gateway_ip:
            subnet_dict.update({
                'gateway_ip': subnet.gateway_ip,
            })

    if subnet.ip_version == 6:
        subnet_dict.update({
            'ipv6_subnet': subnet.cidr,
            'ipv6_allocation_pools': subnet.allocation_pools,
            'routes_ipv6': subnet.host_routes,
            'ipv6_address_mode': subnet.ipv6_address_mode,
            'ipv6_ra_mode': subnet.ipv6_ra_mode,
        })

        if subnet.gateway_ip:
            subnet_dict.update({
                'gateway_ipv6': subnet.gateway_ip,
            })

    pop_defaults(subnet_dict)

    return subnet_name, subnet_dict


def parse_net_resource(conn, net_resource, indexed_networks, net_entry):
    for res in net_resource:
        if net_resource[res][n_utils.RES_TYPE] == n_utils.TYPE_NET:
            idx, net_dict = get_network_info(
                conn, net_resource[res][n_utils.RES_ID])
            net_entry.update(net_dict)
        if net_resource[res][n_utils.RES_TYPE] == n_utils.TYPE_SUBNET:
            subnet_name, subnet_dict = get_subnet_info(
                conn, net_resource[res][n_utils.RES_ID])
            net_entry['subnets'].update({subnet_name: subnet_dict})
    indexed_networks[idx] = net_entry


def parse_net_resources(conn, net_resources):
    indexed_networks = dict()
    for net in net_resources:
        name = net.rpartition('Network')[0]
        net_entry = {'name': name, 'subnets': dict()}
        parse_net_resource(conn, net_resources[net], indexed_networks,
                           net_entry)

    network_data = [indexed_networks[i] for i in sorted(indexed_networks)]

    return network_data


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
        network_data=list()
    )

    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=False,
        **openstack_module_kwargs()
    )

    stack_name = module.params['stack_name']

    try:
        _, conn = openstack_cloud_from_module(module)
        net_resources = n_utils.get_overcloud_network_resources(conn,
                                                                stack_name)
        result['network_data'] = parse_net_resources(conn, net_resources)

        result['changed'] = True if result['network_data'] else False
        module.exit_json(**result)
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error getting network data from overcloud stack "
                         "{stack_name}: %{error}".format(stack_name=stack_name,
                                                         error=err))
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
