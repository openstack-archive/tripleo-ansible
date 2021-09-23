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
    from ansible.module_utils import network_data_v2
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import network_data_v2
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
module: tripleo_composable_network

short_description: Create a TripleO Composable network

version_added: "2.8"

description:
    - Create a TripleO Composable network, a network,
      one or more segments and one or more subnets

options:
  net_data:
    description:
      - Structure describing a TripleO composable network
    type: dict
  idx:
    description:
      - TripleO network index number
    type: int
author:
    - Harald Jensås <hjensas@redhat.com>
'''

RETURN = '''
'''

EXAMPLES = '''
- name: Create composable networks
  default_network:
    description:
      - Default control plane network
    type: string
    default: ctlplane
  tripleo_composable_network:
    net_data:
      name: Storage
      name_lower: storage
      dns_domain: storage.localdomain.
      mtu: 1442
      subnets:
        storage_subnet:
          ip_subnet: 172.18.0.0/24
          gateway_ip: 172.18.0.254
          allocation_pools:
            - start: 172.18.0.10
              end: 172.18.0.250
          routes:
            - destination: 172.18.1.0/24
              nexthop: 172.18.0.254
          vip: true
          vlan: 20
        storage_leaf1:
          ip_subnet: 172.18.1.0/24
          gateway_ip: 172.18.1.254
          allocation_pools:
            - start: 172.18.1.10
              end: 172.18.1.250
          routes:
            - destination: 172.18.0.0/24
              nexthop: 172.18.1.254
          vip: false
          vlan: 21
    idx: 1
'''

DEFAULT_NETWORK = 'ctlplane'
DEFAULT_ADMIN_STATE = False
DEFAULT_SHARED = False
DEFAULT_DOMAIN = 'localdomain.'
DEFAULT_NETWORK_TYPE = 'flat'
DEFAULT_MTU = 1500
DEFAULT_VLAN_ID = 1


def get_overcloud_domain_name(conn, default_network):
    network = conn.network.find_network(default_network)
    if network is not None and network.dns_domain:
        return network.dns_domain.partition('.')[-1]
    else:
        return DEFAULT_DOMAIN


def build_network_tag_field(net_data, idx):
    tags = ['='.join(['tripleo_network_name', net_data['name']]),
            '='.join(['tripleo_net_idx', str(idx)])]
    service_net_map_replace = net_data.get('service_net_map_replace')
    vip = net_data.get('vip')
    if service_net_map_replace:
        tags.append('='.join(['tripleo_service_net_map_replace',
                              service_net_map_replace]))
    if vip:
        tags.append('='.join(['tripleo_vip', 'true']))

    return tags


def build_subnet_tag_field(subnet_data):
    tags = []
    vlan_id = subnet_data.get('vlan')
    vlan_id = str(vlan_id) if vlan_id is not None else str(DEFAULT_VLAN_ID)
    tags.append('='.join(['tripleo_vlan_id', vlan_id]))

    return tags


def create_net_spec(net_data, overcloud_domain_name, idx):
    name_lower = net_data.get('name_lower', net_data['name'].lower())
    net_spec = {
        'admin_state_up': net_data.get('admin_state_up', DEFAULT_ADMIN_STATE),
        'dns_domain': net_data.get(
            'dns_domain', '.'.join([net_data['name'].lower(),
                                    overcloud_domain_name])
        ),
        'mtu': net_data.get('mtu', DEFAULT_MTU),
        'name': name_lower,
        'shared': net_data.get('shared', DEFAULT_SHARED),
        'provider:physical_network': name_lower,
        'provider:network_type': DEFAULT_NETWORK_TYPE,
    }

    net_spec.update({'tags': build_network_tag_field(net_data, idx)})

    return net_spec


def validate_network_update(module, network, net_spec):
    # Fail if updating read-only attributes
    if (network.provider_network_type != net_spec.pop(
            'provider:network_type')
            and network.provider_network_type is not None):
        module.fail_json(
            msg='Cannot update provider:network_type in existing network')
    # NOTE(hjensas): When a network have multiple segments,
    # attributes provider:network_type, provider:physical_network is None
    # for the network.
    if (net_spec.pop('provider:physical_network')
            not in [network.provider_physical_network, net_spec['name']]
            and network.provider_physical_network is not None):
        module.fail_json(
            msg='Cannot update provider:physical_network in existing network')

    # Remove fields that don't need update from spec
    if network.is_admin_state_up == net_spec['admin_state_up']:
        net_spec.pop('admin_state_up')
    if network.dns_domain == net_spec['dns_domain']:
        net_spec.pop('dns_domain')
    if network.mtu == net_spec['mtu']:
        net_spec.pop('mtu')
    if network.name == net_spec['name']:
        net_spec.pop('name')
    if network.is_shared == net_spec['shared']:
        net_spec.pop('shared')

    return net_spec


def create_or_update_network(conn, module, net_spec):
    changed = False

    # Need to use set_tags for the tags ...
    tags = net_spec.pop('tags')

    network = conn.network.find_network(net_spec['name'])
    if not network:
        network = conn.network.create_network(**net_spec)
        changed = True
    else:
        net_spec = validate_network_update(module, network, net_spec)
        if net_spec:
            network = conn.network.update_network(network.id, **net_spec)
            changed = True

    if network.tags != tags:
        conn.network.set_tags(network, tags)
        changed = True

    return changed, network


def create_segment_spec(net_id, net_name, subnet_name, physical_network=None):
    name = '_'.join([net_name, subnet_name])
    if physical_network is None:
        physical_network = name
    else:
        physical_network = physical_network

    return {'network_id': net_id,
            'physical_network': physical_network,
            'name': name,
            'network_type': DEFAULT_NETWORK_TYPE}


def validate_segment_update(module, segment, segment_spec):
    # Fail if updating read-only attributes
    if segment.network_id != segment_spec.pop('network_id'):
        module.fail_json(
            msg='Cannot update network_id in existing segment')
    if segment.network_type != segment_spec.pop('network_type'):
        module.fail_json(
            msg='Cannot update network_type in existing segment')
    if segment.physical_network != segment_spec.pop('physical_network'):
        module.fail_json(
            msg='Cannot update physical_network in existing segment')

    # Remove fields that don't need update from spec
    if segment.name == segment_spec['name']:
        segment_spec.pop('name')

    return segment_spec


def create_or_update_segment(conn, module, segment_spec, segment_id=None):
    changed = False

    if segment_id:
        segment = conn.network.find_segment(segment_id)
    else:
        segment = conn.network.find_segment(
            segment_spec['name'], network_id=segment_spec['network_id'])

    if not segment:
        segment = conn.network.create_segment(**segment_spec)
        changed = True
    else:
        segment_spec = validate_segment_update(module, segment, segment_spec)
        if segment_spec:
            segment = conn.network.update_segment(segment.id, **segment_spec)
            changed = True

    return changed, segment


def create_subnet_spec(net_id, name, subnet_data,
                       ipv6_enabled=False):
    tags = build_subnet_tag_field(subnet_data)
    subnet_v4_spec = None
    subnet_v6_spec = None
    if not ipv6_enabled and subnet_data.get('ip_subnet'):
        subnet_v4_spec = {
            'ip_version': 4,
            'name': name,
            'network_id': net_id,
            'enable_dhcp': subnet_data.get('enable_dhcp', False),
            'gateway_ip': subnet_data.get('gateway_ip', None),
            'cidr': subnet_data['ip_subnet'],
            'allocation_pools': subnet_data.get('allocation_pools', []),
            'host_routes': subnet_data.get('routes', []),
            'tags': tags,
        }
    if ipv6_enabled and subnet_data.get('ipv6_subnet'):
        subnet_v6_spec = {
            'ip_version': 6,
            'name': name,
            'network_id': net_id,
            'enable_dhcp': subnet_data.get('enable_dhcp', False),
            'gateway_ip': subnet_data.get('gateway_ipv6', None),
            'cidr': subnet_data['ipv6_subnet'],
            'allocation_pools': subnet_data.get('ipv6_allocation_pools', []),
            'host_routes': subnet_data.get('routes_ipv6', []),
            'tags': tags,
        }
        if 'ipv6_address_mode' in subnet_data:
            subnet_v6_spec[
                'ipv6_address_mode'] = subnet_data['ipv6_address_mode']
        if 'ipv6_ra_mode' in subnet_data:
            subnet_v6_spec['ipv6_ra_mode'] = subnet_data['ipv6_ra_mode']

    return subnet_v4_spec, subnet_v6_spec


def validate_subnet_update(module, subnet, subnet_spec):

    # Fail if updating read-only attributes
    if subnet.ip_version != subnet_spec.pop('ip_version'):
        module.fail_json(
            msg='Cannot update ip_version in existing subnet')
    if subnet.network_id != subnet_spec.pop('network_id'):
        module.fail_json(
            msg='Cannot update network_id in existing subnet')
    if subnet.cidr != subnet_spec.pop('cidr'):
        module.fail_json(
            msg='Cannot update cidr in existing subnet')
    segment_id = subnet_spec.pop('segment_id')
    if subnet.segment_id != segment_id:
        module.fail_json(
            msg='Cannot update segment_id in existing subnet, '
                'Current segment_id: {} Update segment_id: {}'.format(
                    subnet.segment_id, segment_id))

    # Remove fields that don't need update from spec
    if subnet.name == subnet_spec['name']:
        subnet_spec.pop('name')
    if subnet.is_dhcp_enabled == subnet_spec['enable_dhcp']:
        subnet_spec.pop('enable_dhcp')
    if subnet.ipv6_address_mode == subnet_spec.get('ipv6_address_mode'):
        try:
            subnet_spec.pop('ipv6_address_mode')
        except KeyError:
            pass
    if subnet.ipv6_ra_mode == subnet_spec.get('ipv6_ra_mode'):
        try:
            subnet_spec.pop('ipv6_ra_mode')
        except KeyError:
            pass
    if subnet.gateway_ip == subnet_spec['gateway_ip']:
        subnet_spec.pop('gateway_ip')
    if subnet.allocation_pools == subnet_spec['allocation_pools']:
        subnet_spec.pop('allocation_pools')
    if subnet.host_routes == subnet_spec['host_routes']:
        subnet_spec.pop('host_routes')

    return subnet_spec


def create_or_update_subnet(conn, module, subnet_spec):
    changed = False
    # Need to use set_tags for the tags ...
    tags = subnet_spec.pop('tags')

    subnet = conn.network.find_subnet(subnet_spec['name'],
                                      ip_version=subnet_spec['ip_version'],
                                      network_id=subnet_spec['network_id'])
    if not subnet:
        subnet = conn.network.create_subnet(**subnet_spec)
        changed = True
    else:
        subnet_spec = validate_subnet_update(module, subnet, subnet_spec)
        if subnet_spec:
            subnet = conn.network.update_subnet(subnet.id, **subnet_spec)
            changed = True

    if subnet.tags != tags:
        conn.network.set_tags(subnet, tags)
        changed = True

    return changed


def adopt_the_implicit_segment(conn, module, segments, subnets, network):
    changed = False
    # Check for implicit segment
    implicit_segment = [s for s in segments if s['name'] is None]
    if not implicit_segment:
        return changed

    if len(implicit_segment) > 1:
        module.fail_json(msg='Multiple segments with no name attribute exist '
                             'on network {}, unable to reliably adopt the '
                             'implicit segment.'.format(network.id))
    else:
        implicit_segment = implicit_segment[0]

    if implicit_segment and subnets:
        subnet_associated = [s for s in subnets
                             if s.segment_id == implicit_segment.id][0]
        segment_spec = create_segment_spec(
            network.id, network.name, subnet_associated.name,
            physical_network=implicit_segment.physical_network)
        create_or_update_segment(conn, module, segment_spec,
                                 segment_id=implicit_segment.id)
        changed = True

        return changed
    elif implicit_segment and not subnets:
        conn.network.delete_segment(implicit_segment.id)
        changed = True
        return changed

    module.fail_json(msg='ERROR: Unable to reliably adopt the implicit '
                         'segment.')


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
    )

    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=False,
        **openstack_module_kwargs()
    )

    default_network = module.params.get('default_network', DEFAULT_NETWORK)
    net_data = module.params['net_data']
    idx = module.params['idx']
    error_messages = network_data_v2.validate_json_schema(net_data)
    if error_messages:
        module.fail_json(msg='\n\n'.join(error_messages))

    try:
        _, conn = openstack_cloud_from_module(module)

        ipv6_enabled = net_data.get('ipv6', False)
        # Create or update the network
        net_spec = create_net_spec(
            net_data, get_overcloud_domain_name(conn, default_network), idx)
        changed, network = create_or_update_network(conn, module, net_spec)
        result['changed'] = changed if changed else result['changed']

        # Get current segments and subnets on the network
        segments = list(conn.network.segments(network_id=network.id))
        subnets = list(conn.network.subnets(network_id=network.id))

        changed = adopt_the_implicit_segment(conn, module, segments,
                                             subnets, network)
        result['changed'] = changed if changed else result['changed']
        for subnet_name, subnet_data in net_data.get('subnets', {}).items():
            segment_spec = create_segment_spec(
                network.id, network.name, subnet_name,
                physical_network=subnet_data.get('physical_network'))
            subnet_v4_spec, subnet_v6_spec = create_subnet_spec(
                network.id, subnet_name, subnet_data, ipv6_enabled)

            changed, segment = create_or_update_segment(
                conn, module, segment_spec)
            result['changed'] = changed if changed else result['changed']

            if subnet_v4_spec:
                subnet_v4_spec.update({'segment_id': segment.id})
                changed = create_or_update_subnet(conn, module, subnet_v4_spec)
                result['changed'] = changed if changed else result['changed']

            if subnet_v6_spec:
                subnet_v6_spec.update({'segment_id': segment.id})
                changed = create_or_update_subnet(conn, module, subnet_v6_spec)
                result['changed'] = changed if changed else result['changed']

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
