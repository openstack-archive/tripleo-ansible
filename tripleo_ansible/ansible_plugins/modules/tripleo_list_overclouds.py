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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import yaml

try:
    from ansible.module_utils import tripleo_common_utils as tc
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import tripleo_common_utils as tc
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module

from heatclient import exc as heat_exc
from tripleo_common import inventory as inventory

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_list_overclouds

short_description: List all currently deployed overcloud stacks

version_added: "2.8"

description:
    - "List all currently deployed overcloud stacks"

options: {}
author:
    - Steve Baker (@stevebaker)
'''

RETURN = '''
stacks:
    description: List of stacks
    returned: always
    type: list
    sample:
      - id: 6ea20112-acc5-41d8-9481-78f1151bcfaa
        stack_name: overcloud
      - id: 9345a389-4345-482c-9e18-db226c011e56
        stack_name: other-overcloud
'''


EXAMPLES = '''
- name: Get overcloud stacks
  tripleo_list_overclouds:
  register: overclouds
- name: Display stack names
  debug:
    msg: "overcloud {{ item.stack_name }}
  loop: "{{ overclouds.stacks }}
'''


def get_overclouds(heat_client):
    for stack in heat_client.stacks.list():
        try:
            heat_client.stacks.output_show(stack.stack_name, 'AnsibleHostVarsMap')
            yield {
                "id": stack.id,
                "stack_name": stack.stack_name
            }
        except heat_exc.NotFound:
            pass


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

    try:
        _, conn = openstack_cloud_from_module(module)

        tripleo = tc.TripleOCommon(session=conn.session)
        heat_client = tripleo.get_orchestration_client()

        result['stacks'] = list(get_overclouds(heat_client))
        result['success'] = True
        result['changed'] = False
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error getting overclouds: %s" % err)
        module.fail_json(**result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
