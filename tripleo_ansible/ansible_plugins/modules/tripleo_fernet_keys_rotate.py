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
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module

from tripleo_common.utils import plan as plan_utils

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_fernet_keys_rotate

short_description: Rotate Fernet Keys

version_added: "2.8"

description:
    - "Rotate fernet keys."

options:
    container:
        description:
            - Overcloud stack name
        default: overcloud
author:
    - Rabi Mishra (@ramishra)
requirements: ["openstacksdk", "tripleo-common"]
'''

EXAMPLES = '''
- name: Rotate fernet keys
  tripleo_fernet_keys_rotate:
      container: overcloud
'''

RETURN = '''
fernet_keys:
    description: Rotated fernet keys
    returned: always
    type: dict
    no_log: true
    sample: {
        "/etc/keystone/fernet-keys/0": {
            "content": "kZL9nNvdYim9AvLUfrX4bHAMgwlCIbIkgBLVEoMTi1A="
        },
        "/etc/keystone/fernet-keys/62": {
            "content": "VTwb92H8iysaU0ky7nDV2XFNOscA4Cm_TYBFeI9wuQs="
        },
        "/etc/keystone/fernet-keys/63": {
            "content": "6aiyiVzN5c2qYhuS2mgOLa0zK7Hc6q5-zq6n4tdEUAE="
        },
        "/etc/keystone/fernet-keys/64": {
            "content": "Qq0Ef-wFtxAkwfOxqHHq8zykvozPGkwym4t9ATMrujA="
        },
        "/etc/keystone/fernet-keys/65": {
            "content": "mnbPEIt0AQltAd5bzs9P8nV4cpksaOo7IHvK7eBHp8M="
        }
    }
'''


def run_module():
    result = dict(
        success=False,
        error="",
        fernet_keys={}
    )

    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=True,
        **openstack_module_kwargs()
    )

    try:
        container = module.params.get('container')
        _, conn = openstack_cloud_from_module(module)
        tripleo = tc.TripleOCommon(session=conn.session)

        heat = tripleo.get_orchestration_client()
        # if the user is working with this module in only check mode we do not
        # want to make any changes to the environment, just return the current
        # state with no modifications
        if module.check_mode:
            module.exit_json(**result)
        fernet_keys = plan_utils.rotate_fernet_keys(heat, container)
        result['success'] = True
        result['fernet_keys'] = fernet_keys
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error rotating fernet keys for plan %s: %s" % (
            container, err))
        module.fail_json(**result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
