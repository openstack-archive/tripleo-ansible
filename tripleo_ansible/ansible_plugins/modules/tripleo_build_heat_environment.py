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
import yaml

from ansible.module_utils import tripleo_common_utils as tc
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module

from heatclient.common import template_utils

DOCUMENTATION = """
---
module: tripleo_build_heat_environment
short_description: Build heat stack environment
author:
  - "Rabi Mishra (@ramishra)"
version_added: "2.10"
description:
    - Builds heat stack environment from environment files.
options:
    container:
        description:
            - Name of plan / container
        type: str
    env_files:
        description:
            - List of environment files and directories
        type: list
        default: []
requirements: ["tripleo-common"]
"""

EXAMPLES = """
- name: Build heat environment
  tripleo_build_heat_environment:
    container: overcloud
    env_files: []
"""


def main():
    result = dict(
        success=False,
        changed=False,
        error=None,
        environment={}
    )
    module = AnsibleModule(
        openstack_full_argument_spec(
            **yaml.safe_load(DOCUMENTATION)['options']
        ),
        **openstack_module_kwargs()
    )
    container = module.params.get('container')
    env_files = module.params.get('env_files')
    try:
        if container:
            _, conn = openstack_cloud_from_module(module)
            tripleo = tc.TripleOCommon(session=conn.session)
            heat = tripleo.get_orchestration_client()
            env = heat.environment(container)
        else:
            _, env = template_utils.process_multiple_environments_and_files(
                env_paths=env_files)
        result['environment'] = env
        result['changed'] = True
        result['success'] = True
    except Exception as ex:
        result['error'] = str(ex)
        result['msg'] = 'Error buiding environment: {}'.format(
            ex)
        module.fail_json(**result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
