#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat, Inc.
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
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import copy
import os
import subprocess
import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_os_net_config_mappings
author:
    - Harald Jensås (hjensas@redhat.com)
version_added: '2.8'
short_description: Configure os-net-config mappings for nodes or node groups
notes: []
description:
  - This module creates os-net-config mapping for nodes or node groups based on
    the input data provided. MAC addresses or DMI table strings can be used
    to identify specific nodes or node groups. See manual page for DMIDECODE(8)
    for a list of DMI table strings that can be used.
options:
  net_config_data_lookup:
    description:
      - Per node and/or per node group configuration map
    type: dict
'''

EXAMPLES = '''
- name: Map os-net-config nicX abstraction using MAC address
  tripleo_os_net_config_mappings:
    net_config_data_lookup:
      overcloud-controller-0:
        nic1: "00:c8:7c:e6:f0:2e"
      overcloud-compute-13:
        nic1: "00:18:7d:99:0c:b6"
- name: Interface name to os-net-config nicX abstraction using system-uuid
  tripleo_os_net_config_mappings:
    net_config_data_lookup:
      overcloud-controller-0:
        dmiString: 'system-uuid'
        id: 'A8C85861-1B16-4803-8689-AFC62984F8F6'
        nic1: em3
        nic2: em1
        nic3: em2
        nic4: em4
- name: Interface name to os-net-config nicX abstraction for node groups using system-product-name
  tripleo_os_net_config_mappings:
    net_config_data_lookup:
      nodegroup-dell-poweredge-r630:
        dmiString: "system-product-name"
        id: "PowerEdge R630"
        nic1: em3
        nic2: em1
        nic3: em2
      nodegroup-cisco-ucsb-b200-m4:
        dmiString: "system-product-name"
        id: "UCSB-B200-M4"
        nic1: enp7s0
        nic2: enp6s0
'''

RETURN = '''
mapping:
  description:
    - Dictionary with os-net-config mapping data that can be written to the
      os-net-config mapping file.
  returned: when mapping match present in net_config_data_lookup
  type: dict
'''


def _get_interfaces():
    eth_addr = []

    for x in os.listdir('/sys/class/net/'):
        excluded_ints = ['lo', 'vnet']
        int_subdir = '/sys/class/net/{}/'.format(x)

        if x in excluded_ints or not os.path.isdir(int_subdir):
            continue
        # cast to lower case for MAC address match
        with open('/sys/class/net/{}/address'.format(x)) as f:
            mac_addr = f.read().strip().lower()
        eth_addr.append(mac_addr)

    eth_addr = list(filter(None, eth_addr))

    return eth_addr


def _get_mappings(data):
    eth_addr = _get_interfaces()

    for node in data:
        iface_mapping = copy.deepcopy(data[node])
        if 'dmiString' in iface_mapping:
            del iface_mapping['dmiString']
        if 'id' in iface_mapping:
            del iface_mapping['id']

        # Match on mac addresses first - cast all to lower case
        lc_iface_mapping = copy.deepcopy(iface_mapping)
        for key, x in lc_iface_mapping.items():
            lc_iface_mapping[key] = x.lower()

        if any(x in eth_addr for x in
                lc_iface_mapping.values()):
            return {'interface_mapping': lc_iface_mapping}

        # If data contain dmiString and id keys, try to match node(group)
        if 'dmiString' in data[node] and 'id' in data[node]:
            ps = subprocess.Popen(
                ['dmidecode', '--string', data[node]['dmiString']],
                stdout=subprocess.PIPE, universal_newlines=True)
            out, err = ps.communicate()

            # See LP#1816652
            if data[node].get('id').lower() == out.rstrip().lower():
                return {'interface_mapping': lc_iface_mapping}


def run(module):
    results = dict(
        changed=False,
        mapping=None,
    )

    data = module.params['net_config_data_lookup']
    if isinstance(data, dict) and data:
        results['mapping'] = _get_mappings(data)

    results['changed'] = True if results['mapping'] else False

    module.exit_json(**results)


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=False,
    )
    run(module)

if __name__ == '__main__':
    main()
