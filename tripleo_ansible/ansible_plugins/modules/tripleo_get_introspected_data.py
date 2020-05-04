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
module: tripleo_get_introspected_data
short_description: Retrieve introspection data
extends_documentation_fragment: openstack
author:
  - "Kevin Carter (@cloudnull)"
version_added: "2.10"
description:
    - Pull introspection data from a baremetal node.
options:
    node_id:
        description:
            - ID of the baremetal node
        type: str
        required: true

requirements: ["openstacksdk", "tripleo-common"]
"""

EXAMPLES = """
- name: Get introspected data
  tripleo_get_introspected_data:
    node_id: xxx
  register: introspected_data
"""


import os

import yaml

from tripleo_common import exception


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
        result['data'] = tripleo.return_introspected_node_data(
            node_id=module.params["node_id"]
        )
    except Exception as exp:
        result['error'] = str(exp)
        result['msg'] = 'Error pulling introspection data for {}: {}'.format(
            module.params["node_id"],
            exp
        )
        module.fail_json(**result)
    else:
        result['success'] = True
        module.exit_json(**result)


if __name__ == "__main__":
    main()
