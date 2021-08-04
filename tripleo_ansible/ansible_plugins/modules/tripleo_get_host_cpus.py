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
module: tripleo_get_host_cpus
author:
  - Jaganathan Palanisamy <jpalanis@redhat.com>
version_added: '2.8'
short_description: Generates a dictionary which contains all container configs
notes: []
description:
  - This module reads container configs in JSON files and generate a dictionary
    which later will be used to manage the containers.
options:
  inspect_data:
    description:
      - Hardware data
    required: True
    type: dict
  debug:
    description:
      - Whether or not debug is enabled.
    default: False
    required: False
    type: bool
"""

EXAMPLES = """
- name: Gets the host cpus
  tripleo_get_host_cpus:
    inspect_data: {}
"""

RETURN = """
host_cpus_list:
    description:
      - Host cpus list
    returned: always
    type: list
"""

import json
import yaml


# Gets the Host CPUs List.
# CPU threads from first physical core is allocated for host processes
# on each NUMA nodes.
def _get_host_cpus_list(inspect_data):
    host_cpus_list = []
    numa_cpus_info = inspect_data.get('numa_topology',
                                      {}).get('cpus', [])

    # Checks whether numa topology cpus information is not available
    # in introspection data.
    if not numa_cpus_info:
        msg = 'Introspection data does not have numa_topology.cpus'
        raise tc.DeriveParamsError(msg)

    numa_nodes_threads = {}
    # Creates a list for all available threads in each NUMA nodes
    for cpu in numa_cpus_info:
        if not cpu['numa_node'] in numa_nodes_threads:
            numa_nodes_threads[cpu['numa_node']] = []
        numa_nodes_threads[cpu['numa_node']].extend(
            cpu['thread_siblings'])

    for numa_node in sorted(numa_nodes_threads.keys()):
        node = int(numa_node)
        # Gets least thread in NUMA node
        numa_node_min = min(numa_nodes_threads[numa_node])
        for cpu in numa_cpus_info:
            if cpu['numa_node'] == node:
                # Adds threads from core which is having least thread
                if numa_node_min in cpu['thread_siblings']:
                    host_cpus_list.extend(cpu['thread_siblings'])
                    break

    return ','.join([str(thread) for thread in host_cpus_list])


def main():
    result = dict(
        host_cpus_list="",
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
        result['host_cpus_list'] = _get_host_cpus_list(
            module.params["inspect_data"]
        )
    except tc.DeriveParamsError as dexp:
        result['error'] = str(dexp)
        result['msg'] = 'Error unable to determine Host CPUS : {}'.format(
            dexp
        )
        module.fail_json(**result)
    except Exception as exp:
        result['error'] = str(exp)
        result['msg'] = 'Error unable to determine Host CPUS : {}'.format(
            exp
        )
        module.fail_json(**result)
    else:
        result['success'] = True
        module.exit_json(**result)


if __name__ == '__main__':
    main()
