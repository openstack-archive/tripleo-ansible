#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2022 OpenStack Foundation
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

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs

from tripleo_common.utils import roles as rolesutils

ROLES_PATH_DEFAULT = "/usr/share/openstack-tripleo-heat-templates/roles"

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = f'''
---
module: tripleo_overcloud_role_list

short_description: Retrieve list of overcloud roles

version_added: "4.2"

description:
  - "Retrieve list of overcloud roles"

options:
  roles_path:
    description:
      - Path to the tripleo heat templates roles directory
    default: {ROLES_PATH_DEFAULT}

author:
  - Jiri Podivin <jpodivin@redhat.com>
'''

RETURN = '''
role_list:
    description: Overcloud roles list
    returned: always
    type: list
    elements: string
    sample:
      [
        "BlockStorage",
        "CellController",
        "CephAll",
        "NetworkerSriov",
        "NovaManager",
        "Novacontrol",
        "ObjectStorage",
        "Standalone",
        "Telemetry",
        "Undercloud"
        ]
'''

EXAMPLES = '''
- name: Get Overcloud roles list
  tripleo_overcloud_role_list:
  register: overcloud_role_list
- name: Write data to output file
  copy:
    content: "{{ overcloud_role_list.role_list | to_yaml }}"
    dest: /path/exported-overcloud_role_list.yaml
'''


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
        role_list=list()
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
        roles_path = module.params['roles_path']

        result['role_list'] = rolesutils.get_roles_list_from_directory(roles_path)

        result['changed'] = bool(result['role_list'])

        module.exit_json(**result)

    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error getting role list: {error}".format(error=err))
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
