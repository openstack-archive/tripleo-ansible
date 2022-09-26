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

import copy
import yaml
import logging
import os

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs

from tripleo_common import constants
from tripleo_common.image import image_uploader
from tripleo_common.image import kolla_builder
from tripleo_common.utils.locks import processlock

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_container_image_prepare

short_description: Container Image Prepare

version_added: "2.8"

description:
    - "Container Image Prepare."

options:
    roles_data:
        description:
            - Roles data to filter images
        default: []
        type: list
    environment:
        description:
            - Stack environment containing ContainerImagePrepare parameter
        type: dict
        default: {}
    cleanup:
        description:
            - Cleanup behaviour
        type: str
        default: full
    dry_run:
        description:
            - Flag for dry run
        type: bool
        default: false
    log_file:
        description:
            - Log file
        type: str
    debug:
        description:
            - Flag to enable debug logging
        type: bool
        default: false
author:
    - Rabi Mishra (@ramishra)
'''

EXAMPLES = '''
- name: Container image prepare
  tripleo_container_image_prepare:
      roles_data: {}
      environment: {}
      cleanup: full
      dry_run: False
'''


def setup_logging(log_file, debug):
    # Implements own logging
    log_format = ('%(asctime)s %(process)d %(levelname)s '
                  '%(name)s [  ] %(message)s')
    logging.basicConfig(
        datefmt='%Y-%m-%d %H:%M:%S',
        format=log_format
    )
    log = logging.getLogger()
    if log_file:
        formatter = logging.Formatter(log_format)
        fh = logging.FileHandler(filename=log_file)
        fh.setFormatter(formatter)
        log.addHandler(fh)
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    log.setLevel(log_level)
    return log


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
        params={}
    )

    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=False,
        **openstack_module_kwargs()
    )

    log_file = module.params.get('log_file')
    debug = module.params.get('debug')
    if not module.no_log:
        log = setup_logging(log_file, debug)

    cleanup = module.params.get('cleanup')
    dry_run = module.params.get('dry_run')
    if cleanup not in image_uploader.CLEANUP:
        raise RuntimeError('--cleanup must be one of: %s' %
                           ', '.join(image_uploader.CLEANUP))

    roles_data = module.params.get('roles_data')
    env = module.params.get('environment')
    try:
        lock = processlock.ProcessLock()
        params = kolla_builder.container_images_prepare_multi(
            env, roles_data, cleanup=cleanup, dry_run=dry_run,
            lock=lock)

        for role in roles_data:
            # NOTE(tkajinam): If a role-specific container image prepare
            #                 parameter is set, run the image prepare process
            #                 with the overridden environment
            role_param = '%sContainerImagePrepare' % role['name']
            if env.get('parameter_defaults', {}).get(role_param):
                tmp_env = copy.deepcopy(env)
                tmp_env['parameter_defaults']['ContainerImagePrepare'] = (
                    env['parameter_defaults'][role_param]
                )

                # NOTE(tkajinam): Put the image parameters as role-specific
                #                 parameters
                params['%sParameters' % role['name']] = (
                    kolla_builder.container_images_prepare_multi(
                        tmp_env, [role], cleanup=cleanup, dry_run=dry_run,
                        lock=lock)
                )

        if not module.no_log:
            output = yaml.safe_dump(params, default_flow_style=False)
            log.info(output)

        result['success'] = True
        result['changed'] = True
        result['params'] = {"parameter_defaults": params}
    except Exception as err:
        result['error'] = str(err)
        result['msg'] = ("Error running container image prepare: %s" % (err))
        module.fail_json(**result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
