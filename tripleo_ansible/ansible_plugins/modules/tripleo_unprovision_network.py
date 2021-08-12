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
module: tripleo_unprovision_network

short_description: Unprovision TripleO networks

version_added: "2.9"

description:
    - "Delete TripleO Composable networks"

options:
  net_data:
    description:
      - Structure describing a TripleO composable network
    type: dict
author:
    - Sandeep Yadav <sandyada@redhat.com>
'''

EXAMPLES = '''
- name: Unprovision TripleO composable networks
  tripleo_unprovision_network:
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
'''

RETURN = '''
'''


def unprovision_subnet_and_network(conn, net_data):
    changed = False

    for subnet_name in net_data['subnets']:
        subnet = conn.network.find_subnet(subnet_name)
        if subnet:
            conn.network.delete_subnet(subnet.id)
            changed = True

    network = conn.network.find_network(net_data['name_lower'])
    if network:
        if not network.subnet_ids:
            conn.network.delete_network(network.id)
            changed = True
        else:
            raise Exception(
                'Cannot delete Network {} because it have following subnets '
                'attached {}'.format(network.id, network.subnet_ids))

    return changed


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

    net_data = module.params['net_data']
    error_messages = network_data_v2.validate_json_schema(net_data)
    if error_messages:
        module.fail_json(msg='\n\n'.join(error_messages))

    try:
        _, conn = openstack_cloud_from_module(module)
        changed = unprovision_subnet_and_network(conn, net_data)
        result['changed'] = changed if changed else result['changed']
        result['success'] = True
        module.exit_json(**result)

    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error overcloud network unprovisioning failed!")
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
