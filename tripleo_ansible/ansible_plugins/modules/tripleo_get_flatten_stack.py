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
module: tripleo_get_flatten_stack
short_description: Get the heat stack tree and parameters in flattened structure
extends_documentation_fragment: openstack
author:
  - "Kevin Carter (@cloudnull)"
version_added: "2.10"
description:
    - This method validates the stack of the container and returns the
      parameters and the heat stack tree. The heat stack tree is
      flattened for easy consumption.
options:
    container:
        description:
            - Name of plan / container
        type: str
        required: true

requirements: ["openstacksdk", "tripleo-common"]
"""

EXAMPLES = """
- name: Get flattened stack
  tripleo_get_flatten_stack:
    cloud: undercloud
    container: overcloud
  register: flattened_params
"""


import yaml

from tripleo_common.utils import stack_parameters as stack_param_utils


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
    heat = tripleo.get_orchestration_client()
    try:
        result['stack_data'] = stack_param_utils.get_flattened_parameters(
            swift=object_client,
            heat=heat,
            container=module.params["container"]
        )
    except Exception as exp:
        result['error'] = str(exp)
        result['msg'] = 'Error flattening stack data for plan {}: {}'.format(
            module.params["container"],
            exp
        )
        module.fail_json(**result)
    else:
        result['success'] = True
        module.exit_json(**result)


if __name__ == "__main__":
    main()
