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
from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.openstack import openstack_module_kwargs
from ansible.module_utils.openstack import openstack_cloud_from_module


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: tripleo_get_dpdk_socket_memory
author:
  - Jaganathan Palanisamy <jpalanis@redhat.com>
version_added: '2.8'
short_description: Gets the dpdk socket memory
notes: []
description:
  - This module gets the dpdk socket memory
options:
  dpdk_nics_numa_info:
    description:
      - DPDK nics numa details
    required: True
    type: list
  numa_nodes:
    description:
      - NUMA nodes
    required: True
    type: list
  overhead:
    description:
      - Overhead value
    required: True
    type: int
  packet_size_in_buffer:
    description:
      - Packet size in buffer value
    required: True
    type: int
  minimum_socket_memory:
    description:
      - Minimum socket memory per node
    required: False
    type: int
    default: 1024
"""

EXAMPLES = """
- name: Gets the DPDK socket memory
  tripleo_get_dpdk_socket_memory:
    dpdk_nics_numa_info: {}
    numa_nodes: []
    overhead: 800
    packet_size_in_buffer: 64
    minimum_socket_memory: 1500
"""

RETURN = """
configs:
    description:
      - DPDK socket memory for each numa node.
    returned: always
    type: string
"""

import json
import math
import yaml


# Computes round off MTU value in bytes
# example: MTU value 9000 into 9216 bytes
def _roundup_mtu_bytes(mtu):
    max_div_val = int(math.ceil(float(mtu) / float(1024)))
    return (max_div_val * 1024)


# Calculates socket memory for a NUMA node
def _calculate_node_socket_memory(numa_node, dpdk_nics_numa_info,
                                  overhead, packet_size_in_buffer,
                                  minimum_socket_memory):
    distinct_mtu_per_node = []
    socket_memory = 0

    # For DPDK numa node
    for nics_info in dpdk_nics_numa_info:
        if (numa_node == nics_info['numa_node']
                and not nics_info['mtu'] in distinct_mtu_per_node):
            distinct_mtu_per_node.append(nics_info['mtu'])
            roundup_mtu = _roundup_mtu_bytes(nics_info['mtu'])
            socket_memory += (((roundup_mtu + overhead) * packet_size_in_buffer)
                              / (1024 * 1024))

    # For Non DPDK numa node
    if socket_memory == 0:
        socket_memory = minimum_socket_memory
    # For DPDK numa node
    else:
        socket_memory += 512

    socket_memory_in_gb = int(socket_memory / 1024)
    if socket_memory % 1024 > 0:
        socket_memory_in_gb += 1
    return (socket_memory_in_gb * 1024)


# Gets the DPDK Socket Memory List.
# For NUMA node with DPDK nic, socket memory is calculated
# based on MTU, Overhead and Packet size in buffer.
# For NUMA node without DPDK nic, minimum socket memory is
# assigned (recommended 1GB)
def _get_dpdk_socket_memory(dpdk_nics_numa_info, numa_nodes, overhead,
                            packet_size_in_buffer,
                            minimum_socket_memory=1024):
    dpdk_socket_memory_list = []
    for node in numa_nodes:
        socket_mem = _calculate_node_socket_memory(
            node, dpdk_nics_numa_info, overhead,
            packet_size_in_buffer, minimum_socket_memory)
        dpdk_socket_memory_list.append(socket_mem)

    return ','.join([str(sm) for sm in dpdk_socket_memory_list])


def main():
    result = dict(
        socket_memory="",
        success=False,
        error=None
    )

    module = AnsibleModule(
        openstack_full_argument_spec(
            **yaml.safe_load(DOCUMENTATION)['options']
        ),
        **openstack_module_kwargs()
    )
    try:
        result['socket_memory'] = _get_dpdk_socket_memory(
            module.params["dpdk_nics_numa_info"],
            module.params["numa_nodes"],
            module.params["overhead"],
            module.params["packet_size_in_buffer"],
            module.params["minimum_socket_memory"]
        )
    except Exception as exp:
        result['error'] = str(exp)
        result['msg'] = 'Error unable to determine DPDK socket memory : {}'.format(
            exp
        )
        module.fail_json(**result)
    else:
        result['success'] = True
        module.exit_json(**result)


if __name__ == '__main__':
    main()
