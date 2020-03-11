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
from swiftclient import client as swift_client

from tripleo_common.utils import plan as plan_utils

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_image_params_prepare

short_description: Update plan image params

version_added: "2.8"

description:
    - "Prepare Image params and update plan"

options:
    container:
        description:
            - Overcloud plan container name
        type: str
        default: overcloud
    with_roledata:
        description:
            - With role data
        type: bool
        default: false
author:
    - Rabi Mishra (@ramishra)
'''

EXAMPLES = '''
- name: Prepare image params and update plan
  tripleo_image_params_prepare:
      container: overcloud
      with_roledata: true
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

    try:
        container = module.params.get('container')
        with_roledata = module.params.get('with_roledata')
        _, conn = openstack_cloud_from_module(module)
        session = conn.session

        swift = get_object_client(session)
        plan_utils.update_plan_environment_with_image_parameters(
        swift, container, with_roledata=with_roledata)
        result['success'] = True
        result['changed'] = True
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error updating image parms for plan %s: %s" % (
            container, err))
        module.fail_json(**result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
