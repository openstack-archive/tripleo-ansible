#!/usr/bin/python
# Copyright 2020 Red Hat, Inc.
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
__metaclass__ = type

from ansible.module_utils import baremetal_deploy as bd
from ansible.module_utils.basic import AnsibleModule

import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: tripleo_baremetal_expand_roles
short_description: Manage baremetal nodes with metalsmith
version_added: "2.9"
author: "Steve Baker (@stevebaker)"
description:
  - Takes a baremetal deployment description of roles and node instances
    and transforms that into an instance list and a heat environment file
    for deployed-server.
options:
  stack_name:
    description:
      - Name of the overcloud stack which will be deployed on these instances
    default: overcloud
  state:
    description:
      - Build instance list for the desired provision state, "present" to
        provision, "absent" to unprovision, "all" for a combination of
        "present" and "absent".
    default: present
    choices:
    - present
    - absent
    - all
  baremetal_deployment:
    description:
      - Data describing roles and baremetal node instances to provision for
        those roles
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Mandatory role name
        type: str
        required: True
      hostname_format:
        description:
          - Overrides the default hostname format for this role.
            The default format uses the lower case role name.
            For example, the default format for the Controller role is
            %stackname%-controller-%index%. Only the Compute role does not
            follow the role name rule. The Compute default format is
            %stackname%-novacompute-%index%
        type: str
      count:
        description:
          - Number of instances to create for this role.
        type: int
        default: 1
      defaults:
        description:
          - A dictionary of default values for instances entry properties.
            An instances entry property overrides any defaults that you specify
            in the defaults parameter.
        type: dict
      instances:
        description:
          - Values that you can use to specify attributes for specific nodes.
            The length of this list must not be greater than the value of the
            count parameter.
        type: list
        elements: dict
  default_network:
    description:
      - Default nics entry when none are specified
    type: list
    suboptions: dict
    default:
      - network: ctlplane
        vif: true
  default_image:
    description:
      - Default image
    type: dict
    default:
      href: overcloud-full
  ssh_public_keys:
    description:
      - SSH public keys to load
    type: str
  user_name:
    description:
      - Name of the admin user to create
    type: str
'''

RETURN = '''
instances:
    description: Expanded list of instances to perform actions on
    returned: changed
    type: list
    sample: [
            {
                "hostname": "overcloud-controller-0",
                "image": {
                    "href": "overcloud-full"
                }
            },
            {
                "hostname": "overcloud-controller-1",
                "image": {
                    "href": "overcloud-full"
                }
            },
            {
                "hostname": "overcloud-controller-2",
                "image": {
                    "href": "overcloud-full"
                }
            },
            {
                "hostname": "overcloud-novacompute-0",
                "image": {
                    "href": "overcloud-full"
                }
            },
            {
                "hostname": "overcloud-novacompute-1",
                "image": {
                    "href": "overcloud-full"
                }
            },
            {
                "hostname": "overcloud-novacompute-2",
                "image": {
                    "href": "overcloud-full"
                }
            }
        ]
environment:
    description: Heat environment data to be used with the overcloud deploy.
                 This is only a partial environment, further changes are
                 required once instance changes have been made.
    returned: changed
    type: dict
    sample: {
            "parameter_defaults": {
                "ComputeDeployedServerCount": 3,
                "ComputeDeployedServerHostnameFormat": "%stackname%-novacompute-%index%",
                "ControllerDeployedServerCount": 3,
                "ControllerDeployedServerHostnameFormat": "%stackname%-controller-%index%",
                "HostnameMap": {
                    "overcloud-controller-0": "overcloud-controller-0",
                    "overcloud-controller-1": "overcloud-controller-1",
                    "overcloud-controller-2": "overcloud-controller-2",
                    "overcloud-novacompute-0": "overcloud-novacompute-0",
                    "overcloud-novacompute-1": "overcloud-novacompute-1",
                    "overcloud-novacompute-2": "overcloud-novacompute-2"
                }
            }
        }
'''  # noqa

EXAMPLES = '''
- name: Expand roles
  tripleo_baremetal_expand_roles:
    baremetal_deployment:
    - name: Controller
      count: 3
      defaults:
        image:
          href: overcloud-full
        networks: []
    - name: Compute
      count: 3
      defaults:
        image:
          href: overcloud-full
        networks: []
    state: present
    stack_name: overcloud
  register: tripleo_baremetal_instances
'''


def main():
    argument_spec = yaml.safe_load(DOCUMENTATION)['options']
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False,
    )

    state = module.params['state']

    try:
        if state in ('present', 'all'):
            present, env, role_net_map, hostname_role_map = bd.expand(
                roles=module.params['baremetal_deployment'],
                stack_name=module.params['stack_name'],
                expand_provisioned=True,
                default_image=module.params['default_image'],
                default_network=module.params['default_network'],
                user_name=module.params['user_name'],
                ssh_public_keys=module.params['ssh_public_keys'],
            )
        if state in ('absent', 'all'):
            absent, _, _, _ = bd.expand(
                roles=module.params['baremetal_deployment'],
                stack_name=module.params['stack_name'],
                expand_provisioned=False,
                default_image=module.params['default_image'],
            )
            env = {}
            role_net_map = {}
            hostname_role_map = {}
        if state == 'present':
            instances = present
        elif state == 'absent':
            instances = absent
        elif state == 'all':
            instances = present + absent

        module.exit_json(
            changed=True,
            msg='Expanded to %d instances' % len(instances),
            instances=instances,
            environment=env,
            role_net_map=role_net_map,
            hostname_role_map=hostname_role_map,
        )
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
