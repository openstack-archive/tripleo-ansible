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

import yaml

from ansible.module_utils import tripleo_common_utils as tc
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.openstack import openstack_module_kwargs
from ansible.module_utils.openstack import openstack_cloud_from_module

from tripleo_common.utils import nodes

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: baremetal_register_or_update_nodes

short_description: Register, update or remove baremetal nodes

version_added: "2.8"

description:
    - "It registers, updates or removes baremetal nodes of Ironic"

options:
    nodes_json:
        description:
            - Description of the nodes to be added, removed, changed
        type: list
        required: true
    remove:
        required: false
        type: bool
    kernel_name:
        required: false
    ramdisk_name:
        required: false
    instance_boot_option:
        required: false

author:
    - Adriano Petrich (@frac)
requirements: ["openstacksdk", "tripleo-common"]
'''


def run_module():
    result = dict(
        success=False,
        error="",
        nodes=[]
    )

    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=True,
        **openstack_module_kwargs()
    )

    _, conn = openstack_cloud_from_module(module)
    tripleo = tc.TripleOCommon(session=conn.session)

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    nodes_json = module.params['nodes_json']

    for node in nodes_json:
        caps = node.get('capabilities', {})
        caps = nodes.capabilities_to_dict(caps)
        if module.params['instance_boot_option'] is not None:
            caps.setdefault('boot_option',
                            module.params['instance_boot_option'])
        node['capabilities'] = nodes.dict_to_capabilities(caps)

    baremetal_client = tripleo.get_baremetal_client()
    image_client = tripleo.get_image_client()

    try:
        registered_nodes = nodes.register_all_nodes(
            nodes_json,
            client=baremetal_client,
            remove=module.params['remove'],
            glance_client=image_client,
            kernel_name=module.params['kernel_name'],
            ramdisk_name=module.params['ramdisk_name'])
        result['success'] = True
        result['nodes'] = [
          dict(uuid=node.uuid, provision_state=node.provision_state)
          for node in registered_nodes
        ]
    except Exception as exc:
        # LOG.exception("Error registering nodes with ironic.")
        result['error'] = str(exc)
        module.fail_json(msg='Validation Failed', **result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
