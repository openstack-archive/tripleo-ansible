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
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs

import keystoneauth1
import metalsmith

import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: tripleo_baremetal_check_existing
short_description: Given a list of instances, build a list of found and
                   not found instances
version_added: "2.9"
author: "Steve Baker (@stevebaker)"
description:
  - Takes a baremetal deployment description of roles and node instances
    and transforms that into an instance list and a heat environment file
    for deployed-server.
options:
  instances:
    description:
      - List of instances to be filtered into found and not found.
        Only the name and hostname are used for finding.
    required: true
    type: list
    elements: dict
'''

RETURN = '''
instances:
    description: List of instances which actually exist
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
            }
        ]
not_found:
    description: List of instances which were not found
    returned: changed
    type: list
    sample: [
            {
                "hostname": "overcloud-controller-2",
                "image": {
                    "href": "overcloud-full"
                }
            }
        ]
'''

EXAMPLES = '''
- name: Find existing instances
  tripleo_baremetal_check_existing:
    instances:
      - name: node-1
        hostname: overcloud-controller-0
      - name: node-2
        hostname: overcloud-novacompute-0
  register: tripleo_baremetal_existing
'''


def main():
    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False,
        **module_kwargs
    )

    sdk, cloud = openstack_cloud_from_module(module)
    provisioner = metalsmith.Provisioner(cloud_region=cloud.config)

    try:
        msg = ''

        try:
            baremetal = cloud.baremetal
        except keystoneauth1.exceptions.catalog.EndpointNotFound as exc:
            msg += str(exc)
            baremetal = None

        found, not_found, pre_provisioned = bd.check_existing(
            instances=module.params['instances'],
            provisioner=provisioner,
            baremetal=baremetal
        )
        if found:
            msg += ('Found existing instances: %s. '
                    % ', '.join([i.uuid for i in found]))
        if not_found:
            msg += ('Instance(s) %s do not exist. '
                    % ', '.join(r['hostname'] for r in not_found))
        if pre_provisioned:
            msg += ('Instance(s) %s are pre-provisioned. '
                    % ', '.join(r['hostname'] for r in pre_provisioned))

        instances = [{
            'name': i.node.name or i.uuid,
            'hostname': i.hostname,
            'id': i.uuid,
        } for i in found]
        module.exit_json(
            changed=False,
            msg=msg,
            instances=instances,
            not_found=not_found,
            pre_provisioned=pre_provisioned
        )
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
