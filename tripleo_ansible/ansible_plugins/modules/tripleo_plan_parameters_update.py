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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.openstack import openstack_module_kwargs
from ansible.module_utils.openstack import openstack_cloud_from_module

# NOTE: This is still using the legacy clients. We've not
#       changed to using the OpenStackSDK fully because
#       tripleo-common expects the legacy clients. Once
#       we've updated tripleo-common to use the SDK we
#       should revise this.
from heatclient.v1 import client as heatclient
from swiftclient import client as swift_client

from tripleo_common.utils import stack_parameters as stack_param_utils

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_plan_parameters_update

short_description: Update plan parameters

version_added: "2.8"

description:
    - "Update plan parameters and validate stack"

options:
    container:
        description:
            - Overcloud plan container name
        type: str
        default: overcloud
    parameters:
        description:
            - Parameters to update
        type: dict
        default: {}
    parameter_key:
        description:
            - Heat parameter key
        type: str
        default: parameter_defaults
    validate:
        description:
            - Validate heat stack
        type: bool
        default: true

author:
    - Rabi Mishra (@ramishra)
'''

EXAMPLES = '''
- name: Update Plan params
  tripleo_plan_parameters_update:
      container: overcloud
      parameters:
          RootStackName: overcloud
      validate: false
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

    def get_object_client(session):
        return swift_client.Connection(
            session=session,
            retries=10,
            starting_backoff=3,
            max_backoff=120)

    def get_orchestration_client(session):
        return heatclient.Client(
            session=session)

    try:
        container = module.params.get('container')
        parameters = module.params.get('parameters')
        parameter_key = module.params.get('parameter_key')
        validate = module.params.get('validate')
        _, conn = openstack_cloud_from_module(module)
        session = conn.session

        swift = get_object_client(session)
        heat = get_orchestration_client(session)
        stack_param_utils.update_parameters(
            swift, heat,  parameters,
            container=container,
            parameter_key=parameter_key,
            validate=validate)
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
