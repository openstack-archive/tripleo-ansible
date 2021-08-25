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
try:
    from ansible.module_utils import tripleo_common_utils as tc
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import tripleo_common_utils as tc
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: tripleo_get_dpdk_core_list.py
author:
  - Jaganathan Palanisamy <jpalanis@redhat.com>
version_added: '2.8'
short_description: Gets the DPDK NICs with MTU for NUMA nodes.
notes: []
description:
  - This module gets the DPDK NICs with MTU for NUMA nodes.
options:
  inspect_data:
    description:
      - hardware data
    required: True
    type: dict
  numa_nodes_cores_count:
    description:
      - cores count required for each numa node.
    required: True
    type: list
  debug:
    description:
      - Whether or not debug is enabled.
    default: False
    required: False
    type: bool
"""

EXAMPLES = """
- name: Generate containers configs data
  tripleo_get_dpdk_core_list:
    inspect_data: {}
    numa_nodes_cores_count: 2
"""

RETURN = """
dpdk_core_list:
    description:
      - DPDK core list in string format.
    returned: always
    type: dict
"""

import glob
import json
import os
import re
import yaml

from tripleo_common import exception


def _get_dpdk_core_list(inspect_data, numa_nodes_cores_count):
    dpdk_core_list = []
    numa_cpus_info = inspect_data.get('numa_topology',
                                      {}).get('cpus', [])

    # Checks whether numa topology cpus information is not available
    # in introspection data.
    if not numa_cpus_info:
        msg = 'Introspection data does not have numa_topology.cpus'
        raise tc.DeriveParamsError(msg)

    # Checks whether CPU physical cores count for each NUMA nodes is
    # not available
    if not numa_nodes_cores_count:
        msg = ('CPU physical cores count for each NUMA nodes '
               'is not available')
        raise tc.DeriveParamsError(msg)

    numa_nodes_threads = {}
    # Creates list for all available threads in each NUMA node
    for cpu in numa_cpus_info:
        if not cpu['numa_node'] in numa_nodes_threads:
            numa_nodes_threads[cpu['numa_node']] = []
        numa_nodes_threads[cpu['numa_node']].extend(cpu['thread_siblings'])

    for node, node_cores_count in enumerate(numa_nodes_cores_count):
        # Gets least thread in NUMA node
        numa_node_min = min(numa_nodes_threads[node])
        cores_count = node_cores_count
        for cpu in numa_cpus_info:
            if cpu['numa_node'] == node:
                # Adds threads from core which is not having least thread
                if numa_node_min not in cpu['thread_siblings']:
                    dpdk_core_list.extend(cpu['thread_siblings'])
                    cores_count -= 1
                    if cores_count == 0:
                        break
    return ','.join([str(thread) for thread in dpdk_core_list])


def main():
    result = dict(
        dpdk_core_list="",
        success=False,
        error=None,
    )

    module = AnsibleModule(
        openstack_full_argument_spec(
            **yaml.safe_load(DOCUMENTATION)['options']
        ),
        **openstack_module_kwargs()
    )
    try:
        result['dpdk_core_list'] = _get_dpdk_core_list(
            module.params["inspect_data"],
            module.params["numa_nodes_cores_count"]
        )
    except tc.DeriveParamsError as dexp:
        result['error'] = str(dexp)
        result['msg'] = 'Error unable to determine PMD CPUS : {}'.format(
            dexp
        )
        module.fail_json(**result)
    except Exception as exp:
        result['error'] = str(exp)
        result['msg'] = 'Error unable to determine PMD CPUS : {}'.format(
            exp
        )
        module.fail_json(**result)
    else:
        result['success'] = True
        module.exit_json(**result)


if __name__ == '__main__':
    main()
