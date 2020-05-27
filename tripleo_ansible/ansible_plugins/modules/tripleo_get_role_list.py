# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import tripleo_common_utils as tc
from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.openstack import openstack_module_kwargs
from ansible.module_utils.openstack import openstack_cloud_from_module


DOCUMENTATION = """
---
module: tripleo_get_role_list
short_description: Lists deployment roles
extends_documentation_fragment: openstack
author:
  - "Kevin Carter (@cloudnull)"
version_added: "2.10"
description:
    - This action lists all deployment roles residing in the undercloud.  A
      deployment plan consists of a container marked with metadata
      'x-container-meta-usage-tripleo'.
options:
    container:
        description:
            - Name of plan / container
        type: str
        required: true
    role_file_name:
        description:
            - File name
        type: str
        default: roles_data.yaml
    detail:
        description:
            - If false displays role names only.
              If true, returns all roles data.
        type: bool
        default: false
    valid:
        description:
            - check if the role has count > 0 in heat environment
        type: bool
        default: true
requirements: ["openstacksdk", "tripleo-common"]
"""

EXAMPLES = """
- name: configure boot
  tripleo_get_role_list:
  register: role_list
"""


import os

import yaml

from tripleo_common.utils import roles as roles_utils


def main():
    result = dict(
        success=False,
        changed=False,
        error=None,
    )
    module = AnsibleModule(
        openstack_full_argument_spec(
            **yaml.safe_load(DOCUMENTATION)['options']
        ),
        **openstack_module_kwargs()
    )
    _, conn = openstack_cloud_from_module(module)
    tripleo = tc.TripleOCommon(session=conn.session)
    object_client = tripleo.get_object_client()
    heat = None
    if module.params['valid']:
        heat = tripleo.get_orchestration_client()
    try:
        result['roles'] = roles_utils.get_roles_from_plan(
            swift=object_client,
            heat=heat,
            container=module.params['container'],
            role_file_name=module.params['role_file_name'],
            detail=module.params['detail'],
            valid=module.params['valid']
        )
    except Exception as exp:
        result['error'] = str(exp)
        result['msg'] = 'Error listing roles: {}'.format(exp)
        module.fail_json(**result)
    else:
        result['success'] = True
        module.exit_json(**result)


if __name__ == "__main__":
    main()
