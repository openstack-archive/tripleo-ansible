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

from concurrent import futures
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
module: tripleo_overcloud_network_vip_provision

short_description: Provision overcloud Virtual IPs

version_added: "2.8"

description:
    - Provision network Virtual IP resources for an overcloud

options:
  stack_name:
    description:
      - Name of the overcloud heat stack
    type: str
  vip_data:
    description:
      - Dictionary of network Virtual IP definitions
    type: list
    default: []
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
          - Dns Name
        type: str
        required: True
        default: overcloud
  concurrency:
    description:
      -  Maximum number of ports to provision at once. Set to 0 to have no
         concurrency limit
    type: int
    default: 0
author:
    - Harald Jensås <hjensas@redhat.com>
'''

EXAMPLES = '''
- name: Provision Overcloud Virtual IPs
  tripleo_overcloud_vip_provision:
    stack_name: overcloud
    vip_data:
    - dns_name: overcloud
      ip_address: 172.19.0.5
      name: storage_mgmt_virtual_ip
      network: storage_mgmt
      subnet: storage_mgmt_subnet
    - dns_name: overcloud
      ip_address: 172.17.0.5
      name: internal_api_virtual_ip
      network: internal_api
      subnet: internal_api_subnet
    - dns_name: overcloud
      ip_address: 172.18.0.5
      name: storage_virtual_ip
      network: storage
      subnet: storage_subnet
    - dns_name: overcloud
      ip_address: 10.0.0.5
      name: external_virtual_ip
      network: external
      subnet: external_subnet
    - dns_name: overcloud
      ip_address: 192.168.25.5
      name: control_virtual_ip
      network: ctlplane
      subnet: ctlplane-subnet
'''


def create_port_def(vip_spec, net_maps):
    vip_spec.setdefault('dns_name', 'overcloud')
    net_info = net_maps['by_name'][vip_spec['network']]
    port_def = dict(network_id=net_info['id'], dns_name=vip_spec['dns_name'])

    if vip_spec['network'] == 'ctlplane' and not vip_spec.get('name'):
        port_def['name'] = 'control' + n_utils.NET_VIP_SUFFIX
    else:
        port_def['name'] = (vip_spec['name'] if vip_spec.get('name')
                            else vip_spec['network'] + n_utils.NET_VIP_SUFFIX)

    if vip_spec.get('ip_address'):
        port_def['fixed_ips'] = [{'ip_address': vip_spec['ip_address']}]
    elif vip_spec.get('subnet'):
        port_def['fixed_ips'] = [
            {'subnet_id': net_info['subnets'][vip_spec['subnet']]}]
    elif len(net_info['subnets']) == 1:
        port_def['fixed_ips'] = [
            {'subnet_id': list(net_info['subnets'].values())[0]}]
    else:
        raise Exception(
            'Network {} has multiple subnets, please add a subnet or an '
            'ip_address for the vip on this network.'.format(
                vip_spec['network']))

    return port_def


def provision_vip_port(conn, stack, net_maps, vip_spec, managed_ports):
    port_def = create_port_def(vip_spec, net_maps)

    tags = ['tripleo_stack_name={}'.format(stack),
            'tripleo_vip_net={}'.format(vip_spec['network'])]

    ports = conn.network.ports(
        network_id=net_maps['by_name'][vip_spec['network']]['id'],
        tags=tags)

    try:
        port = next(ports)
        managed_ports.append(port.id)
        del port_def['network_id']
        for k, v in port_def.items():
            if port.get(k) != v:
                conn.network.update_port(port.id, **port_def)
                break
    except StopIteration:
        port = conn.network.create_port(**port_def)
        conn.network.set_tags(port, tags)
        managed_ports.append(port.id)


def validate_vip_nets_in_net_map(vip_data, net_maps):
    for vip in vip_data:
        if not vip['network'] in net_maps['by_name']:
            raise Exception('Network {} for Virtual IP not found.'.format(
                vip['network']))
        if (vip.get('subnet')
                and not vip.get('subnet') in net_maps['by_name'][
                    vip['network']]['subnets']):
            raise Exception(
                'Subnet {} for Virtual IP not found on network {}.'.format(
                    vip['subnet'], vip['network']))


def remove_obsolete_ports(conn, stack, managed_ports):
    ports = conn.network.ports(tags=['tripleo_stack_name={}'.format(stack)])
    ports = [p for p in ports if any("tripleo_vip_net" in t for t in p.tags)]

    for port in ports:
        if port.id not in managed_ports:
            conn.network.delete_port(port.id)


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

    concurrency = module.params['concurrency']
    stack = module.params.get('stack_name')
    vip_data = module.params.get('vip_data')

    try:
        _, conn = openstack_cloud_from_module(module)
        net_maps = n_utils.create_name_id_maps(conn)
        validate_vip_nets_in_net_map(vip_data, net_maps)

        # no limit on concurrency, create a worker for every vip
        if concurrency < 1:
            concurrency = len(vip_data) if len(vip_data) > 0 else 1

        exceptions = list()
        provision_jobs = list()
        managed_ports = list()
        with futures.ThreadPoolExecutor(max_workers=concurrency) as p:
            for vip_spec in vip_data:
                provision_jobs.append(p.submit(
                    provision_vip_port, conn, stack, net_maps, vip_spec,
                    managed_ports))

        for job in futures.as_completed(provision_jobs):
            e = job.exception()
            if e:
                exceptions.append(e)

        if exceptions:
            raise exceptions[0]

        remove_obsolete_ports(conn, stack, managed_ports)

        result['success'] = True
        module.exit_json(**result)
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error provisioning Virtual IPs for overcloud stack "
                         "{stack_name}: {error}".format(stack_name=stack,
                                                        error=err))
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
