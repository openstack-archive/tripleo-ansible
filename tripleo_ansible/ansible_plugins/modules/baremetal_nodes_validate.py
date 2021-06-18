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

from ansible.module_utils.basic import AnsibleModule

from tripleo_common import exception
from tripleo_common.utils import nodes

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: baremetal_nodes_validate

short_description: Baremetal nodes

version_added: "2.8"

description:
    - "Baremetal nodes functions."

options:
    node_list:
        description:
            - List of the nodes to be validated
        required: true

author:
    - Adriano Petrich (@frac)
'''

EXAMPLES = '''
# Pass in a message
- name: Test with a message
  baremetal_nodes_validate:
    nodes_list:
      - _comment: 'This is a comment'
        pm_type: 'pxe_ipmitool'
        pm_addr: '192.168.0.1'
        pm_user: 'root'
        pm_password: 'p@$$w0rd'

      - pm_type: 'ipmi'
        pm_addr: '192.168.1.1'
        pm_user: 'root'
        pm_password: 'p@$$w0rd'
'''


def run_module():
    module_args = dict(
        nodes_list=dict(type='list', required=True),
    )

    result = dict(
        success=False,
        error=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(**result)
    try:
        nodes_json = module.params['nodes_list']
        nodes.validate_nodes(nodes_json)
        result['success'] = True
    except exception.InvalidNode as exc:
        result['error'] = str(exc)
        module.fail_json(msg='Validation Failed', **result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
