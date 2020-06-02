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

import yaml

from ansible.module_utils import tripleo_common_utils as tc
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.openstack import openstack_module_kwargs
from ansible.module_utils.openstack import openstack_cloud_from_module

from tripleo_common.utils import stack as stack_utils

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_plan_deploy

short_description: Deploy Plan

version_added: "2.8"

description:
    - "Deploy Plan"

options:
    container:
        description:
            - Overcloud plan container name
        type: str
        default: overcloud
    skip_deploy_identifier:
        description:
            - Skip deploy indetifier
        type: bool
        default: false
    timeout_mins:
        description:
            - Stack deploy timeout in mins
        type: int
        default: 240

author:
    - Rabi Mishra (@ramishra)
requirements: ["openstacksdk", "tripleo-common"]
'''

EXAMPLES = '''
- name: Deploy Plan
  tripleo_plan_deploy:
    container: overcloud
    skip_deploy_identifier: false
    timeout_mins: 240
'''


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
        container = module.params.get('container')
        skip_deploy_identifier = module.params.get('skip_deploy_identifier')
        timeout_mins = module.params.get('timeout_mins')
        _, conn = openstack_cloud_from_module(module)
        tripleo = tc.TripleOCommon(session=conn.session)
        swift = tripleo.get_object_client()
        heat = tripleo.get_orchestration_client()
        stack_utils.deploy_stack(
            swift, heat,
            container=container,
            skip_deploy_identifier=skip_deploy_identifier,
            timeout_mins=timeout_mins)
        result['success'] = True
        result['changed'] = True
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error updating parameters for plan %s: %s" % (
            container, err))
        module.fail_json(**result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
