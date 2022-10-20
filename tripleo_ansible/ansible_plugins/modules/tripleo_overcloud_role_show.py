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

import os

import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import (
    openstack_full_argument_spec, openstack_module_kwargs)
from tripleo_common.utils import roles as rolesutils

ROLES_PATH_DEFAULT = "/usr/share/openstack-tripleo-heat-templates/roles"
ENVIRONMENT_PATH_DEFAULT = os.path.expanduser(
   "~/overcloud-deploy/overcloud/environment/tripleo-overcloud-environment.yaml")

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = f'''
---
module: tripleo_overcloud_role_show

short_description: Retrieve detailed information about overcloud role

version_added: "4.2"

description:
  - "Retrieve detailed information about an overcloud role"
  - "Module should only be executed under users with access to the role info."
  - "If {ENVIRONMENT_PATH_DEFAULT} is not accessible, or doesn't exist, a suitable alternative has to be provided."

options:
  roles_path:
    description:
      - Path to the tripleo heat templates roles directory
    default: {ROLES_PATH_DEFAULT}
    required: false
    type: str
  role_name:
    description:
      - Name of the overcloud role
    required: true
    type: str
  environment_path:
    description:
      - Path to the tripleo environment file
    default: {ENVIRONMENT_PATH_DEFAULT}
    required: false
    type: str
  default_values:
    description:
      - Dictionary containing default key->value pairs from the requested role
      - Used only when the keys aren't already defined within the role.
    required: false
    type: dict
author:
  - Jiri Podivin <jpodivin@redhat.com>
'''

RETURN = '''
role_detail:
    description: Overcloud role info
    returned: always
    type: dict
    sample:
      {
        "CountDefault": 1,
        "RoleParametersDefault": {
            "FsAioMaxNumber": 1048576,
            "TunedProfileName": "virtual-host"
        },
        "ServicesDefault": [
            "OS::TripleO::Services::Aide",
            "OS::TripleO::Services::AuditD",
            "OS::TripleO::Services::BootParams",
            "OS::TripleO::Services::CACerts",
            "OS::TripleO::Services::CephClient",
        ],
        "deprecated_nic_config_name": "compute.yaml",
        "deprecated_param_extraconfig": "NovaComputeExtraConfig",
        "deprecated_param_image": "NovaImage",
        "deprecated_param_ips": "NovaComputeIPs",
        "deprecated_param_metadata": "NovaComputeServerMetadata",
        "deprecated_param_scheduler_hints": "NovaComputeSchedulerHints",
        "deprecated_server_resource_name": "NovaCompute",
        "description": "Basic Compute Node role\n",
        "name": "Compute"
    },
'''

EXAMPLES = '''
- name: Get Overcloud role info
  tripleo_overcloud_role_show:
    role_name: Compute
  register: overcloud_role
- name: Write data to output file
  copy:
    content: "{{ overcloud_role.role_detail | to_yaml }}"
    dest: /path/exported-overcloud_role.yaml
'''


def _set_role_defaults(role, overcloud_environment, default_values):
    """Only apply defaults if there aren't any values present
    under the keys already. First element of the item
    element from the iterator corresponds to (key, value)
    tuple. Comparing the `key` with the set of all keys in
    `role` dictionary we determine if the value needs updating.
    """

    role.update(
      [
        item for item in default_values.items()
        if item[0] not in role.keys()
      ])

    role['CountDefault'] = overcloud_environment.get(
      f"{role['name']}Count", role.get('CountDefault', None))
    role['FlavorDefault'] = overcloud_environment.get(
      f"Overcloud{role['name']}Flavor", role.get('FlavorDefault', None))

    return role


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
        role_details=dict()
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
        environment_path = module.params['environment_path']
        default_values = module.params.get('default_values', {})
        role_name = module.params['role_name']

        roles_path = os.path.join(roles_path, '{}.yaml'.format(role_name))

        with open(roles_path, 'r') as file:
            role = rolesutils.validate_role_yaml(file)
        try:
            with open(environment_path, 'r') as file:
                overcloud_environment = yaml.safe_load(file)['parameter_defaults']
        except FileNotFoundError as exception:
            raise FileNotFoundError(
              f"Given role information path {environment_path} is not accessible.\n"
              "Please verify user and host combination.") from exception

        role = _set_role_defaults(role, overcloud_environment, default_values)
        result['role_detail'] = role

        result['changed'] = bool(result['role_detail'])

        module.exit_json(**result)
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error getting role information: %{error}".format(
                                                         error=err))
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
