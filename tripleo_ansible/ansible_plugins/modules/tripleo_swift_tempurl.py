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

from tripleo_common.utils import swift as swift_utils

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_swift_tempurl

short_description: Get swift tempurl

version_added: "2.8"

description:
    - "Get swift tempurl for object."

options:
    container:
        description:
            - Container name
        type: str
        default: overcloud-swift-rings
    object:
        description:
            - Object name
        type: str
        defult: swift-rings.tar.gz
    method:
        description:
            - An HTTP method to allow for this tempurl
        type: str
        default: GET

author:
    - Rabi Mishra (@ramishra)
requirements: ["openstacksdk", "tripleo-common"]
'''

EXAMPLES = '''
- name: Get tempurl for swit backup
  tripleo_swift_tempurl:
      container: overcloud-swift-rings
      object: swift-rings.tar.gz
      method: GET
  register: tempurl
'''

RETURN = '''
tempurl:
    description: tempurl for object
    returned: always
    type: string
    no_log: true
'''


def run_module():
    result = dict(
        success=False,
        error="",
        changed=False,
        tempurl=""
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
        obj = module.params.get('object')
        method = module.params.get('method')
        _, conn = openstack_cloud_from_module(module)
        tripleo = tc.TripleOCommon(session=conn.session)
        swift = tripleo.get_object_client()
        tempurl = swift_utils.get_temp_url(swift, container, obj, method)
        result['success'] = True
        result['changed'] = True
        result['tempurl'] = tempurl
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error getting %s tempurl for %s/%s: %s" % (
            method, container, obj, err))
        module.fail_json(**result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
