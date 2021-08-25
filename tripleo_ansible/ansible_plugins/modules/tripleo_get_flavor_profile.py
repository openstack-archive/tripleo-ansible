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
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module


DOCUMENTATION = """
---
module: tripleo_get_flavor_profile
short_description: Get the flavor profile data
extends_documentation_fragment: openstack
author:
  - "Kevin Carter (@cloudnull)"
version_added: "2.10"
description:
    - Pull profile from a given flavor
options:
    flavor_name:
        description:
            - Name of flavor
        type: str
        required: true

requirements: ["openstacksdk", "tripleo-common"]
"""

EXAMPLES = """
- name: Get flavor profile
  tripleo_get_flavor_profile:
    flavor_name: m1.tiny
  register: flavor_profile
"""


import os

import yaml

from tripleo_common import exception
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
    try:
        result['profile'] = tripleo.return_flavor_profile(
            module.params["flavor_name"]
        )
    except exception.DeriveParamsError:
        result['profile'] = None
        result['success'] = True
        module.exit_json(**result)
    except Exception as exp:
        result['error'] = str(exp)
        result['msg'] = 'Error pulling flavor properties for {}: {}'.format(
            module.params["flavor_name"],
            exp
        )
        module.fail_json(**result)
    else:
        result['success'] = True
        module.exit_json(**result)


if __name__ == "__main__":
    main()
