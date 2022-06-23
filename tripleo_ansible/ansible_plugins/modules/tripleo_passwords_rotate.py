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

import os
import yaml

from ansible.module_utils import tripleo_common_utils as tc
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module

from tripleo_common.utils import plan as plan_utils
from tripleo_common import constants

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_passwords_rotate

short_description: Rotate Passwords

version_added: "2.8"

description:
    - "Rotate Passwords."

options:
    container:
        description:
            - Overcloud plan container name
        default: overcloud
    rotate_passwords:
        description: flag for rotate passwords or not
        default: true
        type: bool
    password_list:
        description:
            - Password list to be rotated
        type: list
        default: []
        no_log: true
    password_file:
        description:
            - file containing the current passwords for the stack
        type: str
        default: ""
        no_log: true
author:
    - Rabi Mishra (@ramishra)
requirements: ["openstacksdk", "tripleo-common"]
'''

EXAMPLES = '''
- name: Rotate passwords and update plan
  tripleo_password_rotate:
      container: overcloud
      rotate_passwords: true
      password_list: []
'''

RETURN = '''
passwords:
    description: Rotated passwords
    returned: always
    type: dict
    no_log: true
'''


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
        passwords={}
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
        rotate_passwords = module.params.get('rotate_passwords')
        password_list = module.params.get('password_list')
        password_file = module.params.get('password_file')
        _, conn = openstack_cloud_from_module(module)
        tripleo = tc.TripleOCommon(session=conn.session)
        heat = tripleo.get_orchestration_client()

        # Which file to look for passwords
        if not password_file:
            password_file = os.path.join(
                constants.DEFAULT_WORKING_DIR_FORMAT.format(container),
                constants.PASSWORDS_ENV_FORMAT.format(container))
        # Check whether the password file exists
        if os.path.exists(password_file):
            with open(password_file, 'r') as f:
                passwords_env = yaml.safe_load(f.read())
        else:
            passwords_env = None

        rotated_passwords = plan_utils.generate_passwords(
            heat=heat, container=container,
            rotate_passwords=rotate_passwords,
            rotate_pw_list=password_list,
            passwords_env=passwords_env
        )
        result['success'] = True
        result['passwords'] = rotated_passwords
        result['changed'] = True
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error rotating passwords for plan %s: %s" % (
            container, err))
        module.fail_json(**result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
