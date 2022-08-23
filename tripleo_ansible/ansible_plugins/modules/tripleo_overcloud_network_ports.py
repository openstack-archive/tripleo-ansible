#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2018 OpenStack Foundation
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
import metalsmith
import re
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
module: tripleo_overcloud_network_ports

short_description: Manage composable networks ports for overcloud nodes

version_added: "2.8"
author: Harald Jensås <hjensas@redhat.com>

description:
    - "Manage composable networks ports for overcloud nodes."

options:
  stack_name:
    description:
      - Name of the overcloud stack which will be deployed on these instances
    default: overcloud
  concurrency:
    description:
      -  Maximum number of instances to provision ports for at once. Set to 0
         to have no concurrency limit
    type: int
    default: 0
  state:
    description:
      - The desired provision state, "present" to provision, "absent" to
        unprovision
    default: present
    choices:
    - present
    - absent
  instances:
    description:
      - Data describing instances, node instances and networks to provision
        ports in
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Mandatory role name
        type: str
        required: True
      hostname:
        description:
          - Node hostname
        type: str
      networks:
        description:
          - List of networks for the role
        type: list
        elements: dict
        suboptions:
          network:
            description:
              - Name of the network
            type: str
          subnet:
            description:
              - Name of the subnet on the network
            type: str
          port:
            description:
              - Name or ID of a pre-created port
            type: str
  provisioned_instances:
    description:
      - List of provisioned instances
    required: false
    type: list
    elements: dict
    suboptions:
      id:
        description:
          - Ironic Node UUID
        type: str
      hostname:
        description:
          - Node hostname
        type: str
    default: []
  hostname_role_map:
    description:
      - Mapping of instance hostnames to role name
    type: dict
'''

RETURN = '''
node_port_map:
  controller-0:
    External:
      ip_address: 10.0.0.9
      ip_subnet: 10.0.0.9/24
      ip_address_uri: 10.0.0.9
    InternalApi:
      ip_address: 172.18.0.9
      ip_subnet: 172.18.0.9/24
      ip_address_uri: 172.18.0.9
    Tenant:
      ip_address: 172.19.0.9
      ip_subnet: 172.19.0.9/24
      ip_address_uri: 172.19.0.9
  compute-0:
    InternalApi:
      ip_address: 172.18.0.15
      ip_subnet: 172.18.0.15/24
      ip_address_uri: 172.18.0.15
    Tenant:
      ip_address: 172.19.0.15
      ip_subnet: 172.19.0.15/24
      ip_address_uri: 172.19.0.15
'''

EXAMPLES = '''
- name: Manage composable networks instance ports
  tripleo_overcloud_network_ports:
    stack_name: overcloud
    concurrency: 20
    instances:
      - hostname: overcloud-controller-0
        networks:
          - network: internal_api
            subnet: internal_api_subnet
          - network: tenant
            subnet: tenant_subnet
      - hostname: overcloud-novacompute-0
        networks:
          - network: internal_api
            subnet: internal_api_subnet
          - network: tenant
            subnet:  tenant_subnet
      - hostname: overcloud-novacompute-1
        networks:
          - network: internal_api
            subnet: internal_api_subnet02
          - network: tenant
            subnet:  tenant_subnet02
        provisioned: false
    provisioned_instances:
      - hostname: overcloud-novacompute-0
        id: 1e3685bd-ffbc-4028-8a1c-4e87e45062d0
      - hostname: overcloud-controller-0
        id: 59cf045a-ef7f-4f2e-be66-accd05dcd1e6
    register: overcloud_network_ports
'''


def delete_ports(conn, ports):
    for port in ports:
        conn.network.delete_port(port.id)


def pre_provisioned_ports(result, conn, net_maps, instance, inst_ports, tags):
    for net in instance['networks']:
        if net.get('port'):
            network_id = net_maps['by_name'][net['network']]['id']
            p_obj = conn.network.find_port(net['port'], network_id=network_id)

            if p_obj is None:
                msg = ("Network port {port} for instance {instance} could not "
                       "be found.".format(port=net['port'],
                                          instance=instance['hostname']))
                raise Exception(msg)
            result['changed'] = _reset_tags(conn, p_obj, tags)
            inst_ports.append(p_obj)


def fixed_ips_need_update(port_def, port):
    number_of_fixed_ips_in_def = len(port_def['fixed_ips'])
    number_of_fixed_ips_on_port = len(port.fixed_ips)

    if number_of_fixed_ips_in_def != number_of_fixed_ips_on_port:
        return True

    match_count = 0
    for def_fixed_ip in port_def['fixed_ips']:
        def_values = set(def_fixed_ip.values())
        for port_fixed_ip in port.fixed_ips:
            port_values = set(port_fixed_ip.values())
            if def_values.issubset(port_values):
                match_count += 1

    return number_of_fixed_ips_in_def != match_count


def port_need_update(port_def, port):
    update_fields = dict()

    if fixed_ips_need_update(port_def, port):
        update_fields['fixed_ips'] = port_def['fixed_ips']

    return update_fields


def _reset_tags(conn, port, tags, default_route_network=None,
                net_name=None):
    changed = False
    p_tags = set(port.tags)
    # This would allow us to move nodes from one role to other
    r = re.compile('tripleo_role=.*')
    matched_tags = filter(r.match, p_tags.copy())
    for role_tag in matched_tags:
        if role_tag and role_tag not in tags:
            p_tags.remove(role_tag)

    if default_route_network and net_name in default_route_network:
        tags.update({'tripleo_default_route=true'})
    elif 'tripleo_default_route=true' in p_tags:
        p_tags.remove('tripleo_default_route=true')
        conn.network.set_tags(port, list(p_tags))
        changed = True

    if not tags.issubset(p_tags):
        p_tags.update(tags)
        conn.network.set_tags(port, list(p_tags))
        changed = True
    return changed


def update_ports(result, conn, port_defs, inst_ports, tags, net_maps,
                 network_config):
    default_route_network = network_config.get('default_route_network', [])
    for port_def in port_defs:
        for p in inst_ports:
            if (p.name == port_def['name']
                    and p.network_id == port_def['network_id']):
                port = p
                break
        else:  # Executed because no break in for
            raise Exception(
                'Port {name} on network {network} not found.'.format(
                    name=port_def['name'], network=port_def['network_id']))

        update_fields = port_need_update(port_def, port)

        if update_fields:
            conn.network.update_port(port.id, update_fields)
            result['changed'] = True

        net_name = net_maps['by_id'][port.network_id]
        result['changed'] = _reset_tags(conn, port, tags,
                                        default_route_network,
                                        net_name)
        # Remove the 'tripleo_default_route' tag before processing next port
        try:
            tags.remove('tripleo_default_route=true')
        except KeyError:
            pass


def create_ports(result, conn, port_defs, inst_ports, tags, net_maps,
                 network_config):
    default_route_network = network_config.get('default_route_network',
                                               ['ctlplane'])
    ports = conn.network.create_ports(port_defs)

    for port in ports:
        net_name = net_maps['by_id'][port.network_id]
        if net_name in default_route_network:
            tags.update({'tripleo_default_route=true'})
        conn.network.set_tags(port, list(tags))
        inst_ports.append(port)
        # Remove the 'tripleo_default_route' tag before processing next port
        try:
            tags.remove('tripleo_default_route=true')
        except KeyError:
            pass

    result['changed'] = True


def generate_port_defs(net_maps, instance, inst_ports):
    hostname = instance['hostname']
    create_port_defs = []
    update_port_defs = []
    existing_port_names = [port.name for port in inst_ports]

    for net in instance['networks']:
        net_name = net['network']
        net_name_upper = net_maps['by_name'][net_name]['name_upper']

        if net.get('vif', False):
            # VIF port's are managed by metalsmith.
            continue

        net_id = net_maps['by_name'][net_name]['id']
        subnet_name_map = net_maps['by_name'][net_name]['subnets']

        if net.get('fixed_ip'):
            fixed_ips = [{'ip_address': net['fixed_ip']}]
        else:
            if net.get('subnet'):
                try:
                    subnet_id = subnet_name_map[net['subnet']]
                except KeyError:
                    raise Exception(
                        'Subnet {subnet} not found on network {net_name}'
                        .format(subnet=net['subnet'], net_name=net_name))
            elif len(net_maps['by_name'][net_name]['subnets']) == 1:
                subnet_id = next(iter(subnet_name_map.values()))
            else:
                raise Exception(
                    'The "subnet" or "fixed_ip" must be set for the '
                    '{instance_name} port on the {network_name} network since '
                    'there are multiple subnets'.format(
                        instance_name=hostname, network_name=net_name))

            fixed_ips = [{'subnet_id': subnet_id}]

        port_name = '_'.join([hostname, net_name_upper])

        port_def = dict(name=port_name, dns_name=hostname, network_id=net_id,
                        fixed_ips=fixed_ips)

        if port_name not in existing_port_names:
            create_port_defs.append(port_def)
        else:
            update_port_defs.append(port_def)

    return create_port_defs, update_port_defs


def delete_removed_nets(result, conn, instance, net_maps, inst_ports):
    instance_nets = [net['network'] for net in instance['networks']]
    ports_by_net = {net_maps['by_id'][port.network_id]: port
                    for port in inst_ports
                    # Filter ports managed by metalsmith (vifs)
                    if 'tripleo_ironic_vif_port=true' not in port.tags}

    to_delete = []
    for net_name in ports_by_net:
        if net_name not in instance_nets:
            to_delete.append(ports_by_net[net_name])

    if to_delete:
        delete_ports(conn, to_delete)
        inst_ports[:] = [port for port in inst_ports if port not in to_delete]
        result['changed'] = True


def _provision_ports(result, conn, stack, instance, net_maps, ports_by_node,
                     ironic_uuid, role):
    hostname = instance['hostname']
    network_config = instance.get('network_config', {})
    tags = ['tripleo_stack_name={}'.format(stack)]
    # TODO(hjensas): This can be moved below the ironic_uuid condition in
    # later release when all upgraded deployments has had the
    # tripleo_ironic_uuid tag added
    inst_ports = conn.network.ports(tags=tags)
    # NOTE(hjensas): 'dns_name' is not a valid attribute for filtering, so we
    # have to do it manually.
    inst_ports = [port for port in inst_ports
                  if port.dns_name == hostname.lower()]

    tags.append('tripleo_role={}'.format(role))
    if ironic_uuid:
        tags.append('tripleo_ironic_uuid={}'.format(ironic_uuid))

    tags = set(tags)

    delete_removed_nets(result, conn, instance, net_maps, inst_ports)
    pre_provisioned_ports(result, conn, net_maps, instance, inst_ports, tags)

    create_port_defs, update_port_defs = generate_port_defs(net_maps, instance,
                                                            inst_ports)

    if create_port_defs:
        create_ports(result, conn, create_port_defs, inst_ports, tags,
                     net_maps, network_config)
    if update_port_defs:
        update_ports(result, conn, update_port_defs, inst_ports, tags,
                     net_maps, network_config)

    ports_by_node[hostname] = inst_ports


def _unprovision_ports(result, conn, stack, instance, ironic_uuid):
    hostname = instance['hostname']
    tags = ['tripleo_stack_name={}'.format(stack)]
    if ironic_uuid:
        tags.append('tripleo_ironic_uuid={}'.format(ironic_uuid))
    inst_ports = conn.network.ports(tags=tags)
    # NOTE(hjensas): 'dns_name' is not a valid attribute for filtering, so we
    # have to do it manually.
    inst_ports = [port for port in inst_ports
                  if port.dns_name == hostname.lower()]

    # TODO(hjensas): This can be removed in later release when all upgraded
    # deployments has had the tripleo_ironic_uuid tag added.
    if not inst_ports:
        tags = ['tripleo_stack_name={}'.format(stack)]
        inst_ports = conn.network.ports(tags=tags)
        inst_ports = [port for port in inst_ports
                      if port.dns_name == hostname.lower()]

    if inst_ports:
        delete_ports(conn, inst_ports)
        result['changed'] = True


def generate_node_port_map(result, net_maps, ports_by_node):
    node_port_map = result['node_port_map']
    for hostname, ports in ports_by_node.items():
        node = node_port_map[hostname.lower()] = dict()
        for port in ports:
            if not port.fixed_ips:
                continue

            net_name = net_maps['by_id'][port.network_id]
            ip_address = port.fixed_ips[0]['ip_address']
            subnet_id = port.fixed_ips[0]['subnet_id']
            cidr_prefix = net_maps['cidr_prefix_map'][subnet_id]

            node_net = node[net_name] = dict()
            node_net['ip_address'] = ip_address
            node_net['ip_subnet'] = '/'.join([ip_address, cidr_prefix])
            node_net['ip_address_uri'] = n_utils.wrap_ipv6(ip_address)


def validate_instance_nets_in_net_map(instances, net_maps):
    for instance in instances:
        for net in instance['networks']:
            if not net['network'] in net_maps['by_name']:
                raise Exception(
                    'Network {network_name} for instance {instance_name} not '
                    'found.'.format(network_name=net['network'],
                                    instance_name=instance['hostname']))


def manage_instances_ports(result, conn, stack, instances, concurrency, state,
                           uuid_by_hostname, hostname_role_map, net_maps):
    if not instances:
        return

    # no limit on concurrency, create a worker for every instance
    if concurrency < 1:
        concurrency = len(instances)

    validate_instance_nets_in_net_map(instances, net_maps)
    ports_by_node = dict()

    provision_jobs = []
    exceptions = []
    with futures.ThreadPoolExecutor(max_workers=concurrency) as p:
        for instance in instances:
            ironic_uuid = uuid_by_hostname.get(instance['hostname'])
            if state == 'present':
                role = hostname_role_map[instance['hostname']]
                provision_jobs.append(
                    p.submit(_provision_ports,
                             result,
                             conn,
                             stack,
                             instance,
                             net_maps,
                             ports_by_node,
                             ironic_uuid,
                             role)
                )
            elif state == 'absent':
                provision_jobs.append(
                    p.submit(_unprovision_ports,
                             result,
                             conn,
                             stack,
                             instance,
                             ironic_uuid)
                )

    for job in futures.as_completed(provision_jobs):
        e = job.exception()
        if e:
            exceptions.append(e)

    if exceptions:
        raise exceptions[0]

    generate_node_port_map(result, net_maps, ports_by_node)


def _tag_metalsmith_instance_ports(result, conn, provisioner, uuid, hostname,
                                   tags, default_route_network, net_maps):
    instance = provisioner.show_instance(uuid)

    for nic in instance.nics():
        net_name = net_maps['by_id'][nic.network_id]
        result['changed'] = _reset_tags(conn, nic, tags,
                                        default_route_network,
                                        net_name)
        if not nic.dns_name == hostname:
            conn.network.update_port(nic, dns_name=hostname)
            result['changed'] = True

        # Remove the 'tripleo_default_route' tag before processing next port
        try:
            tags.remove('tripleo_default_route=true')
        except KeyError:
            pass


def tag_metalsmith_managed_ports(result, conn, concurrency, stack,
                                 uuid_by_hostname, hostname_role_map,
                                 instances_by_hostname, net_maps):
    # no limit on concurrency, create a worker for every instance
    if concurrency < 1:
        concurrency = len(uuid_by_hostname)

    provisioner = metalsmith.Provisioner(cloud_region=conn.config)
    provisioner.connection = conn
    provision_jobs = []
    exceptions = []
    with futures.ThreadPoolExecutor(max_workers=concurrency) as p:
        for hostname, uuid in uuid_by_hostname.items():
            role = hostname_role_map[hostname]
            default_route_network = instances_by_hostname[hostname].get(
                'network_config', {}).get(
                'default_route_network', ['ctlplane'])

            tags = {'tripleo_stack_name={}'.format(stack),
                    'tripleo_ironic_uuid={}'.format(uuid),
                    'tripleo_role={}'.format(role),
                    'tripleo_ironic_vif_port=true'}
            provision_jobs.append(
                p.submit(_tag_metalsmith_instance_ports,
                         result, conn, provisioner, uuid, hostname, tags,
                         default_route_network, net_maps)
            )

    for job in futures.as_completed(provision_jobs):
        e = job.exception()
        if e:
            exceptions.append(e)

    if exceptions:
        raise exceptions[0]


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
        node_port_map=dict(),
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
    concurrency = module.params['concurrency']
    instances = module.params['instances']
    state = module.params['state']
    provisioned_instances = module.params['provisioned_instances']
    hostname_role_map = module.params['hostname_role_map']
    uuid_by_hostname = {i['hostname']: i['id'] for i in provisioned_instances}
    instances_by_hostname = {i['hostname']: i for i in instances}

    try:
        _, conn = openstack_cloud_from_module(module)

        net_maps = n_utils.create_name_id_maps(conn)

        if state == 'present' and uuid_by_hostname:
            tag_metalsmith_managed_ports(result, conn, concurrency, stack,
                                         uuid_by_hostname, hostname_role_map,
                                         instances_by_hostname, net_maps)

        manage_instances_ports(result, conn, stack, instances, concurrency,
                               state, uuid_by_hostname, hostname_role_map,
                               net_maps)
        result['success'] = True
        module.exit_json(**result)
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error managing network ports {}".format(err))
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
