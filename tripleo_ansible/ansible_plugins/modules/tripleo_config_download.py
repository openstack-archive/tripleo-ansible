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
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module

from tripleo_common.utils import config as ooo_config

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_config_download

short_description: Download config

version_added: "2.8"

description:
    - "Download Config."

options:
    plan:
        description:
            - Overcloud plan name
        type: str
        default: overcloud
    work_dir:
        description:
            - Work dir
        type: str
        default: /home/stack/config-download
    config_type:
        description:
            - Config type
        type: str
    download:
        description:
            - Download flag
        type: bool
        default: true
author:
    - Rabi Mishra (@ramishra)
'''

EXAMPLES = '''
- name: Download config
  tripleo_config_download:
      plan: overcloud
      work_dir: /home/stack/config-downloa
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
        argument_spec,
        supports_check_mode=False,
        **openstack_module_kwargs()
    )

    try:
        plan = module.params.get('plan')
        work_dir = module.params.get('work_dir')
        config_type = module.params.get('config_type')
        download = module.params.get('download')

        _, conn = openstack_cloud_from_module(module)
        tripleo = tc.TripleOCommon(session=conn.session)

        heat = tripleo.get_orchestration_client()
        ooo_config.get_overcloud_config(
            swift=None,
            heat=heat,
            container=plan,
            config_dir=work_dir,
            config_type=config_type,
            preserve_config=download)
        result['success'] = True
        result['changed'] = True
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error downloading config for %s: %s" % (
            plan, err))
        module.fail_json(**result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
