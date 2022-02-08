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
module: tripleo_service_vip

short_description: Create a Virtual IP address for a service

version_added: "2.8"

description:
    - "Create a Virtual IP address for a service"

options:
  playbook_dir:
    description:
      - The path to the directory of the playbook that was passed to the
        ansible-playbook command line.
    type: str
  render_path:
    description:
      - The output path to the file that will be produced by executing this
        module.
    type: str
  stack_name:
    description:
      - Name of the overcloud stack which will be deployed on these instances
    type: str
    default: overcloud
  service_name:
    description:
      - Name of the service the Virtual IP is intended for
    type: str
  state:
    description:
      - The desired provision state, "present" to provision, "absent" to
        unprovision
    default: present
    choices:
    - present
    - absent
  network:
    description:
      - Neutron network where the Virtual IP port will be created
    type: str
  fixed_ips:
    description:
      - A list of ip allocation definitions
    type: list
    elements: dict
    suboptions:
      ip_address:
        description:
          - IP address
        type: str
      subnet:
        description:
          - Neutron subnet name or id
        type: str
      use_neutron:
        description:
          - Boolean option to allow not to create a neutron port.
        type: bool

author:
    - Harald Jensås <hjensas@redhat.com>
'''

RETURN = '''
'''

EXAMPLES = '''
- name: Create redis Virtual IP
  tripleo_service_vip:
    stack_name: overcloud
    service_name: redis
    network: internal_api
    fixed_ip:
      - subnet: internal_api_subnet
  register: redis_vip
- name: Create foo Virtual IP (Not creating a neutron port)
  tripleo_service_vip:
    stack_name: overcloud
    service_name: foo
    network: foo
    fixed_ip:
      - ip_address: 192.0.2.5
        use_neutron: false
  register: redis_vip
'''

VIRTUAL_IP_NAME_SUFFIX = '_virtual_ip'


class FakePort:
    def __init__(self, fixed_ips):
        self.fixed_ips = fixed_ips


def create_or_update_port(conn, net, stack=None, service=None,
                          fixed_ips=None):
    if not fixed_ips:
        raise Exception('ERROR: No IP allocation definition provided. '
                        'Please provide at least one IP allocation '
                        'definition using the fixed_ips argument.')

    tags = {'tripleo_stack_name={}'.format(stack),
            'tripleo_service_vip={}'.format(service)}
    port_def = dict(name=service + VIRTUAL_IP_NAME_SUFFIX, network_id=net.id)

    try:
        port = next(conn.network.ports(tags=list(tags), network_id=net.id))
    except StopIteration:
        port = None

    fixed_ips_def = port_def['fixed_ips'] = []

    for fixed_ip in fixed_ips:
        ip_address = fixed_ip.get('ip_address')
        subnet_name = fixed_ip.get('subnet')
        ip_def = {}
        if ip_address:
            ip_def['ip_address'] = ip_address
        if subnet_name:
            subnet = conn.network.find_subnet(subnet_name, network_id=net.id)
            if subnet is None:
                raise Exception('ERROR: Subnet {} does not exist for network '
                                '{}. Service {} is mapped to a subnet that '
                                'does not exist. Verify that the VipSubnetMap '
                                'parameter has the correct values.'.format(
                                    subnet_name, net.name, service))
            ip_def['subnet_id'] = subnet.id

        fixed_ips_def.append(ip_def)

    if not port:
        port = conn.network.create_port(**port_def)
    else:
        # TODO: Check if port needs update
        port = conn.network.update_port(port, **port_def)

    p_tags = set(port.tags)
    if not tags.issubset(p_tags):
        p_tags.update(tags)
        conn.network.set_tags(port, list(p_tags))

    return port


def find_ctlplane_vip(conn, stack=None, service=None):
    tags = ['tripleo_stack_name={}'.format(stack),
            'tripleo_vip_net=ctlplane']
    try:
        port = next(conn.network.ports(tags=tags))
    except StopIteration:
        raise Exception('Virtual IP address on the ctlplane network for stack '
                        '{} not found. Service {} is mapped to the ctlplane '
                        'network and thus require a virtual IP address to be '
                        'present on the ctlplane network.'.format(stack,
                                                                  service))

    return port


def validate_service_vip_vars_file(service_vip_var_file):
    if not os.path.isfile(service_vip_var_file):
        raise Exception(
            'ERROR: Service VIP var file {} is not a file'.format(
                service_vip_var_file))


def write_vars_file(port, service, playbook_dir, out=None):
    ips = [x['ip_address'] for x in port.fixed_ips]
    if len(ips) == 1:
        ips = ips[0]

    if out is not None:
        service_vip_var_file = os.path.abspath(out)
    else:
        playbook_dir_path = os.path.abspath(playbook_dir)
        network_data_v2.validate_playbook_dir(playbook_dir)
        service_vip_var_file = os.path.join(playbook_dir_path,
                                            'service_vip_vars.yaml')

    if not os.path.exists(service_vip_var_file):
        data = dict()
    else:
        validate_service_vip_vars_file(service_vip_var_file)
        with open(service_vip_var_file, 'r') as f:
            data = yaml.safe_load(f.read())

    data.update({service: ips})
    with open(service_vip_var_file, 'w') as f:
        f.write(yaml.safe_dump(data, default_flow_style=False))

    return data


def use_neutron(conn, stack, service, network, fixed_ips):

    net = conn.network.find_network(network)

    # NOTE: If the network does'nt exist fall back to use the ctlplane VIP
    if net is None or net.name == 'ctlplane':
        port = find_ctlplane_vip(conn, stack=stack, service=service)
    else:
        port = create_or_update_port(conn, net, stack=stack, service=service,
                                     fixed_ips=fixed_ips)

    return port


def use_fake(service, fixed_ips):
    if [fixed_ip for fixed_ip in fixed_ips if 'ip_address' in fixed_ip]:
        port = FakePort(fixed_ips)
    else:
        raise Exception('Neutron service is not available and no fixed IP '
                        'address provided for {} service virtual IP. When '
                        'neutron service is not available a fixed IP '
                        'address must be provided'.format(service))

    return port


# This method is here so that openstack_cloud_from_module
# can be mocked in tests.
def _openstack_cloud_from_module(module):
    _, conn = openstack_cloud_from_module(module)

    return _, conn


def delete_service_vip(module, stack, service='all'):
    try:
        _, conn = _openstack_cloud_from_module(module)
        if service == 'all':
            tags = {'tripleo_stack_name={}'.format(stack)}
            ports = conn.network.ports(tags=list(tags))
            matching = [p for p in ports
                        if any("tripleo_service_vip" in tag for tag in p.tags)]
        else:
            tags = {'tripleo_stack_name={}'.format(stack),
                    'tripleo_service_vip={}'.format(service)}
            matching = conn.network.ports(tags=list(tags))
        for p in matching:
            conn.network.delete_port(p.id)
    except Exception:
        pass


def create_service_vip(module, stack, service, network, fixed_ips,
                       playbook_dir, out=None):
    _use_neutron = True
    for fixed_ip in fixed_ips:
        if ('use_neutron', False) in fixed_ip.items():
            _use_neutron = False
            break

    if _use_neutron:
        _, conn = _openstack_cloud_from_module(module)
        port = use_neutron(conn, stack, service, network, fixed_ips)
    else:
        port = use_fake(service, fixed_ips)

    return write_vars_file(port, service, playbook_dir, out)


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

    stack = module.params.get('stack_name')
    state = module.params.get('state')
    service = module.params.get('service_name') or 'all'

    out = module.params.get('render_path', None)
    playbook_dir = module.params.get('playbook_dir', None)
    data = dict()

    try:

        if out is None and playbook_dir is None and state != 'absent':
            raise Exception("Provide a playbook_dir or an output path file.")

        if state == 'present' and service == 'all':
            raise Exception("Provide service_name for service_vip creation.")

        if state == 'absent':
            delete_service_vip(module, stack, service)
        else:
            network = module.params['network']
            fixed_ips = module.params.get('fixed_ips', [])
            data = create_service_vip(module, stack, service, network, fixed_ips,
                                      playbook_dir, out)
        result['changed'] = True
        result['success'] = True
        result['data'] = data
        module.exit_json(**result)
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ('ERROR: Failed creating/deleting service virtual IP!'
                         ' {}'.format(err))
        result['data'] = {}
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
