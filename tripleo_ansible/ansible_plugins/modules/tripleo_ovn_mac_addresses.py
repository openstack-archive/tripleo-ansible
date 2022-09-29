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

from concurrent import futures
import os
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
module: tripleo_ovn_mac_addresses

short_description: Manage OVN bridge Mac Addresses

version_added: "2.8"

description:
    - "Create a OVN Mac Address network, and allocate bridge mac address ports"

options:
  concurrency:
    description:
      -  Maximum number of server resources to provision ports for at once.
         Set to 0 to have no concurrency limit
    type: int
    default: 0
  playbook_dir:
    description:
      - The path to the directory of the playbook that was passed to the
        ansible-playbook command line.
    type: str
  stack_name:
    description:
      - Name of the overcloud stack
    type: str
    default: overcloud
  ovn_bridge_mappings:
    description:
      - OVN bridge mappings
    type: list
  server_resource_names:
    description:
      - List of server resources
    type: list
  ovn_static_bridge_mac_mappings:
    description:
      - Static OVN Bridge MAC address mappings. Unique OVN bridge mac addresses
        is dynamically allocated by creating neutron ports. When neutron isn't
        available, for instance in the standalone deployment, use this
        parameter to provide static OVN bridge mac addresses.
    type: dict
    default: {}

author:
    - Harald Jensås <hjensas@redhat.com>
'''

RETURN = '''
'''

EXAMPLES = '''
- name: Create OVN Mac address ports
  tripleo_ovn_mac_addresses:
    stack_name: overcloud
    bridge_mappings:
      - datacentre:br-ex
    server_resource_names:
      - controller-0
      - controller-1
      - controller-2
- name: Create OVN Mac address ports (static)
  tripleo_ovn_mac_addresses:
    stack_name: overcloud
    bridge_mappings:
      - datacentre:br-ex
    server_resource_names:
      - controller-0
      - compute-0
    ovn_static_bridge_mac_mappings:
      controller-0:
        datacenter: 00:00:5E:00:53:00
        provider: 00:00:5E:00:53:01
      compute-0:
        datacenter: 00:00:5E:00:54:00
        provider: 00:00:5E:00:54:01
'''

NET_NAME = 'ovn_mac_addr_net'
NET_DESCRIPTION = 'Network used to allocate MAC addresses for OVN chassis.'


def create_ovn_mac_address_network(result, conn):
    network = conn.network.find_network(NET_NAME)
    if network is None:
        network = conn.network.create_network(name=NET_NAME,
                                              description=NET_DESCRIPTION)

        result['changed'] = True

    return network.id


def port_exists(conn, net_id, tags, name):
    try:
        next(conn.network.ports(network_id=net_id, name=name, tags=tags))
    except StopIteration:
        return False

    return True


def create_ovn_mac_address_ports(result, conn, net_id, tags, physnets,
                                 server):
    for physnet in physnets:
        name = '_'.join([server, 'ovn_physnet', physnet])
        if port_exists(conn, net_id, tags, name):
            continue

        port = conn.network.create_port(network_id=net_id, name=name,
                                        dns_name=server)
        conn.network.set_tags(
            port, tags + ['tripleo_ovn_physnet={}'.format(physnet)])

        result['changed'] = True


def remove_obsolete_ports(result, conn, net_id, tags, servers, physnets):
    ports = conn.network.ports(network_id=net_id, tags=tags)
    for port in ports:
        tags = network_data_v2.tags_to_dict(port.tags)
        if (port.dns_name not in servers
                or tags['tripleo_ovn_physnet'] not in physnets):
            conn.network.delete_port(port)
            result['changed'] = True


def validate_ovn_bridge_mac_addr_var_file(ovn_bridge_mac_addr_var_file):
    if not os.path.isfile(ovn_bridge_mac_addr_var_file):
        raise Exception(
            'ERROR: OVN bridge MAC address var file {} is not a file'.format(
                ovn_bridge_mac_addr_var_file))


def write_vars_file(conn, playbook_dir, net_id, tags, static_mappings):

    playbook_dir_path = os.path.abspath(playbook_dir)
    network_data_v2.validate_playbook_dir(playbook_dir)

    ovn_bridge_mac_addr_var_file = os.path.join(
        playbook_dir_path, 'ovn_bridge_mac_address_vars.yaml')

    if not os.path.exists(ovn_bridge_mac_addr_var_file):
        data = dict()
    else:
        validate_ovn_bridge_mac_addr_var_file(ovn_bridge_mac_addr_var_file)
        with open(ovn_bridge_mac_addr_var_file, 'r') as f:
            data = yaml.safe_load(f.read())

    if not static_mappings:
        ports = conn.network.ports(network_id=net_id, tags=tags)

        for port in ports:
            tag_dict = network_data_v2.tags_to_dict(port.tags)
            hostname = port.dns_name
            physnet = tag_dict.get('tripleo_ovn_physnet')
            if hostname and physnet:
                host = data.setdefault(hostname, dict())
                host[physnet] = port.mac_address
    else:
        data = static_mappings

    with open(ovn_bridge_mac_addr_var_file, 'w') as f:
        f.write(yaml.safe_dump(data, default_flow_style=False))


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

    stack = module.params.get('stack_name', 'overcloud')
    bridge_mappings = module.params['ovn_bridge_mappings'] or []
    servers = module.params.get('server_resource_names') or []
    playbook_dir = module.params['playbook_dir']
    concurrency = module.params.get('concurrency', 0)
    static_mappings = module.params.get(
        'ovn_static_bridge_mac_mappings', {})
    physnets = [x.split(':')[0] for x in bridge_mappings]
    conn = tags = net_id = None

    try:
        if not static_mappings:
            _, conn = openstack_cloud_from_module(module)
            net_id = create_ovn_mac_address_network(result, conn)
            tags = ['tripleo_stack_name={}'.format(stack)]

            # no limit on concurrency, create a worker for every server
            if concurrency < 1:
                concurrency = len(servers)

            if servers:
                jobs = []
                exceptions = []
                with futures.ThreadPoolExecutor(max_workers=concurrency) as p:
                    for server in servers:
                        jobs.append(p.submit(create_ovn_mac_address_ports,
                                             result, conn, net_id, tags,
                                             physnets, server))

                for job in futures.as_completed(jobs):
                    e = job.exception()
                    if e:
                        exceptions.append(e)

                if exceptions:
                    raise exceptions[0]

            try:
                remove_obsolete_ports(result, conn, net_id, tags, servers,
                                      physnets)
            except Exception:
                pass
        if static_mappings or servers:
            write_vars_file(conn, playbook_dir, net_id, tags, static_mappings)

        result['success'] = True
        module.exit_json(**result)

    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ('ERROR: Failed creating OVN MAC address resources!'
                         ' {}'.format(err))
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
