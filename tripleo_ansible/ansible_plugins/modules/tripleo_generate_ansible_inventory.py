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
import os
import traceback
import yaml

from ansible.module_utils import tripleo_common_utils as tc
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module

from tripleo_common import inventory as inventory

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_generate_ansible_inventory

short_description: Generate Ansible Inventory

version_added: "2.8"

description:
    - "Generate Ansible Inventory"

options:
    plan:
        description:
            - Overcloud plan name
        type: str
        default: overcloud
    ansible_ssh_user:
        description:
            - Ansible ssh user
        type: str
        default: tripleo-admin
    ansible_ssh_private_key_file:
        description:
            - Private key file
        type: str
    ansible_python_interpreter:
        description:
            - Python interpreter
        type: str
    ssh_network:
        description:
            - SSH network
        type: str
        default: ctlplane
    work_dir:
        description:
            - Work dir
        type: str
        default: /home/stack/config-download/overcloud
author:
    - Rabi Mishra (@ramishra)
'''

RETURN = '''
inventory_path:
    description: Inventory file path
    returned: always
    type: string
'''


EXAMPLES = '''
- name: Generate ansible inventory for plan
  tripleo_generate_ansible_inventory:
      plan: overcloud
      ansible_ssh_user: tripleo-admin
      ansible_ssh_private_key_file: /home/stack/.ssh/tripleo-admin-rsa
      ansible_python_interpreter: /usr/bin/python3
      ssh_network: ctlplane
      work_dir: /home/stack/config-download/overcloud
'''


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
    )

    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False,
        **openstack_module_kwargs()
    )

    try:
        plan = module.params.get('plan')
        ssh_user = module.params.get('ansible_ssh_user')
        ssh_private_key_file = module.params.get(
            'ansible_ssh_private_key_file')
        python_interpretor = module.params.get('ansible_python_interpretor')
        ssh_network = module.params.get('ssh_network')
        work_dir = module.params.get('work_dir')

        _, conn = openstack_cloud_from_module(module)
        tripleo = tc.TripleOCommon(session=conn.session)
        heat = tripleo.get_orchestration_client()

        cloud_name = os.environ.get('OS_CLOUD', 'undercloud')
        inventory_path = inventory.generate_tripleo_ansible_inventory(
            cloud_name=cloud_name,
            heat=heat,
            plan=plan,
            work_dir=work_dir,
            ansible_python_interpreter=python_interpretor,
            ansible_ssh_user=ssh_user,
            undercloud_key_file=ssh_private_key_file,
            ssh_network=ssh_network)
        result['inventory_path'] = inventory_path
        result['success'] = True
        result['changed'] = True
    except Exception as err:
        result['error'] = traceback.format_exc()
        result['msg'] = ("Error generating inventory for %s: %s - %s" % (
            plan, err, str(err)))
        module.fail_json(**result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
