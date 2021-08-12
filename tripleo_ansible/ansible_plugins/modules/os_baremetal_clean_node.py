#!/usr/bin/python
# Copyright (c) 2019 OpenStack Foundation
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

# flake8: noqa: E501
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: os_baremetal_clean_node
short_description: Clean baremetal nodes of Ironic
extends_documentation_fragment: openstack
author:
  - "Sagi Shnaidman (@sshnaidm)"
version_added: "2.10"
description:
    - Clean Ironic nodes.
options:
    node_uuid:
      description:
        - globally unique identifier (UUID) to identify the host.
      type: list
      required: False
      default: []
    node_name:
      description:
        - unique name identifier to identify the host in Ironic.
      type: list
      required: False
      default: []
    clean_steps:
      description:
        - The clean steps as a list of clean-step
          dictionaries; each dictionary should have keys 'interface' and
          'step', and optional key 'args'. This must be specified for node
          cleaning.
      type: list
      required: True
    timeout:
      description:
        - Timeout to wait for each node to clean in seconds.
      type: int
      required: False
      default: 1800
    quiet:
      description:
        - Don't provide cleaned nodes info in output of the module
      type: bool
      default: False
    max_retries:
      description:
        - Number of attempts before failing.
      type: int
      required: False
      default: 0
    concurrency:
      description:
        - Max level of concurrency.
      type: int
      required: False
      default: 20
    raid_config:
      description:
        - Sets the raid configuration for a given node.
      type: dict
      required: False
requirements: ["openstacksdk"]
'''

RETURN = '''
baremetal_nodes:
    description: Dictionary of new facts representing discovered properties of
                 the node.
    returned: changed
    type: dict
    sample: {
                "baremetal_data": [
                    {
                        "af7e758c-d5d0-4cd6-9f60-efbabf5a7788": {
                            "allocation_id": null,
                            "bios_interface": null,
                            "boot_interface": null,
                            "chassis_id": null,
                            "clean_step": null,
                            "conductor": null,
                            "conductor_group": null,
                            "console_interface": null,
                            "created_at": null,
                            "deploy_interface": null,
                            "deploy_step": null,
                            "driver": null,
                            "driver_info": null,
                            "driver_internal_info": null,
                            "extra": null,
                            "fault": null,
                            "id": "af7e758c-d5d0-4cd6-9f60-efbabf5a7788",
                            "inspect_interface": null,
                            "instance_id": null,
                            "instance_info": null,
                            "is_automated_clean_enabled": null,
                            "is_console_enabled": null,
                            "is_maintenance": null,
                            "is_protected": null,
                            "last_error": null,
                            "links": [
                                {
                                    "href": "https://192.168.24.2:13385/v1/nodes/af7e758c-d5d0-4cd6-9f60-efbabf5a7788",
                                    "rel": "self"
                                },
                                {
                                    "href": "https://192.168.24.2:13385/nodes/af7e758c-d5d0-4cd6-9f60-efbabf5a7788",
                                    "rel": "bookmark"
                                }
                            ],
                            "location": {
                                "cloud": "undercloud",
                                "project": {
                                    "domain_id": null,
                                    "domain_name": "Default",
                                    "id": "09c0706606d04ca5a57b3894ad6e915a",
                                    "name": "admin"
                                },
                                "region_name": "regionOne",
                                "zone": null
                            },
                            "maintenance_reason": null,
                            "management_interface": null,
                            "name": null,
                            "network_interface": null,
                            "owner": null,
                            "port_groups": null,
                            "ports": null,
                            "power_interface": null,
                            "power_state": null,
                            "properties": null,
                            "protected_reason": null,
                            "provision_state": "manageable",
                            "raid_config": null,
                            "raid_interface": null,
                            "rescue_interface": null,
                            "reservation": null,
                            "resource_class": null,
                            "states": null,
                            "storage_interface": null,
                            "target_power_state": null,
                            "target_provision_state": null,
                            "target_raid_config": null,
                            "traits": null,
                            "updated_at": null,
                            "vendor_interface": null
                        }
                    },
                    {
                        "c0a4aa96-742d-40be-b594-f940856dfae7": {
                            "allocation_id": null,
                            "bios_interface": null,
                            "boot_interface": null,
                            "chassis_id": null,
                            "clean_step": null,
                            "conductor": null,
                            "conductor_group": null,
                            "console_interface": null,
                            "created_at": null,
                            "deploy_interface": null,
                            "deploy_step": null,
                            "driver": null,
                            "driver_info": null,
                            "driver_internal_info": null,
                            "extra": null,
                            "fault": null,
                            "id": "c0a4aa96-742d-40be-b594-f940856dfae7",
                            "inspect_interface": null,
                            "instance_id": null,
                            "instance_info": null,
                            "is_automated_clean_enabled": null,
                            "is_console_enabled": null,
                            "is_maintenance": null,
                            "is_protected": null,
                            "last_error": null,
                            "links": [
                                {
                                    "href": "https://192.168.24.2:13385/v1/nodes/c0a4aa96-742d-40be-b594-f940856dfae7",
                                    "rel": "self"
                                },
                                {
                                    "href": "https://192.168.24.2:13385/nodes/c0a4aa96-742d-40be-b594-f940856dfae7",
                                    "rel": "bookmark"
                                }
                            ],
                            "location": {
                                "cloud": "undercloud",
                                "project": {
                                    "domain_id": null,
                                    "domain_name": "Default",
                                    "id": "09c0706606d04ca5a57b3894ad6e915a",
                                    "name": "admin"
                                },
                                "region_name": "regionOne",
                                "zone": null
                            },
                            "maintenance_reason": null,
                            "management_interface": null,
                            "name": null,
                            "network_interface": null,
                            "owner": null,
                            "port_groups": null,
                            "ports": null,
                            "power_interface": null,
                            "power_state": null,
                            "properties": null,
                            "protected_reason": null,
                            "provision_state": "manageable",
                            "raid_config": null,
                            "raid_interface": null,
                            "rescue_interface": null,
                            "reservation": null,
                            "resource_class": null,
                            "states": null,
                            "storage_interface": null,
                            "target_power_state": null,
                            "target_provision_state": null,
                            "target_raid_config": null,
                            "traits": null,
                            "updated_at": null,
                            "vendor_interface": null
                        }
                    },
                    {
                        "72176c3a-cfcb-4d82-927d-92b1d3f46716": {
                            "allocation_id": null,
                            "bios_interface": null,
                            "boot_interface": null,
                            "chassis_id": null,
                            "clean_step": null,
                            "conductor": null,
                            "conductor_group": null,
                            "console_interface": null,
                            "created_at": null,
                            "deploy_interface": null,
                            "deploy_step": null,
                            "driver": null,
                            "driver_info": null,
                            "driver_internal_info": null,
                            "extra": null,
                            "fault": null,
                            "id": "72176c3a-cfcb-4d82-927d-92b1d3f46716",
                            "inspect_interface": null,
                            "instance_id": null,
                            "instance_info": null,
                            "is_automated_clean_enabled": null,
                            "is_console_enabled": null,
                            "is_maintenance": null,
                            "is_protected": null,
                            "last_error": null,
                            "links": [
                                {
                                    "href": "https://192.168.24.2:13385/v1/nodes/72176c3a-cfcb-4d82-927d-92b1d3f46716",
                                    "rel": "self"
                                },
                                {
                                    "href": "https://192.168.24.2:13385/nodes/72176c3a-cfcb-4d82-927d-92b1d3f46716",
                                    "rel": "bookmark"
                                }
                            ],
                            "location": {
                                "cloud": "undercloud",
                                "project": {
                                    "domain_id": null,
                                    "domain_name": "Default",
                                    "id": "09c0706606d04ca5a57b3894ad6e915a",
                                    "name": "admin"
                                },
                                "region_name": "regionOne",
                                "zone": null
                            },
                            "maintenance_reason": null,
                            "management_interface": null,
                            "name": null,
                            "network_interface": null,
                            "owner": null,
                            "port_groups": null,
                            "ports": null,
                            "power_interface": null,
                            "power_state": null,
                            "properties": null,
                            "protected_reason": null,
                            "provision_state": "manageable",
                            "raid_config": null,
                            "raid_interface": null,
                            "rescue_interface": null,
                            "reservation": null,
                            "resource_class": null,
                            "states": null,
                            "storage_interface": null,
                            "target_power_state": null,
                            "target_provision_state": null,
                            "target_raid_config": null,
                            "traits": null,
                            "updated_at": null,
                            "vendor_interface": null
                        }
                    }
                ],
                "changed": true,
                "failed_nodes": [],
                "passed_nodes": [
                    "af7e758c-d5d0-4cd6-9f60-efbabf5a7788",
                    "c0a4aa96-742d-40be-b594-f940856dfae7",
                    "72176c3a-cfcb-4d82-927d-92b1d3f46716"
                ]
            }
'''  # noqa

EXAMPLES = '''
# Invoke node inspection
- os_baremetal_clean_node:
    node_uuid:
      - 0593c323-ad62-4ce9-b431-3c322827a428
    clean_steps:
      - interface: deploy
        step: erase_devices_metadata

- os_baremetal_clean_node:
    node_uuid:
      - 0593c323-ad62-4ce9-b431-3c322827a428
    raid_config:
      logical_disks:
        - "size_gb": 100
          "raid_level": "1"
          "controller": "software"
    clean_steps:
      - interface: raid
        step: delete_configuration
      - interface: raid
        step: create_configuration

- os_baremetal_clean_node:
    node_uuid:
      - 0593c323-ad62-4ce9-b431-3c322827a428
    clean_steps:
      - interface: bios
        step: apply_configuration
        priority: 150
        args:
          settings:
            - name: "LogicalProc"
              value: "Disabled"

- os_baremetal_clean_node:
    node_name:
      - baremetal-85-3
    clean_steps:
      - interface: management
        step: activate_license
        args:
          ilo_license_key: "ABC12-XXXXX-XXXXX-XXXXX-YZ345"
      - interface: management
        step: update_firmware
        args:
          firmware_update_mode: "ilo"
          firmware_images:
            - url: "file:///firmware_images/ilo/1.5/CP024444.scexe"
              checksum: "a94e683ea16d9ae44768f0a65942234d"
              component: "ilo"
'''

import yaml

from concurrent import futures

from openstack import exceptions

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import (openstack_full_argument_spec,
                                            openstack_module_kwargs,
                                            openstack_cloud_from_module)


def parallel_nodes_cleaning(conn, module):
    client = conn.baremetal
    node_timeout = module.params['timeout']
    nodes = module.params['node_uuid'] + module.params['node_name']
    clean_steps = module.params['clean_steps']
    result = {}

    if module.params['raid_config']:
        for node in nodes:
            try:
                node_info = client.update_node(
                    node,
                    target_raid_config=module.params['raid_config']
                )
                result.update({node: {
                    'msg': 'Setting the raid configuration'
                           ' for node {} succeeded.'.format(node),
                    'failed': False,
                    'info': node_info,
                }})
            except exceptions.BadRequestException as e:
                result.update({node: {
                    'msg': 'Setting raid configuration'
                           ' for node {} failed. Error: {}'.format(
                               node,
                               str(e)
                            ),
                    'failed': True,
                    'error': str(e),
                    'info': {},
                }})
                nodes.pop(nodes.index(node))

    workers = min(len(nodes), module.params['concurrency']) or 1
    with futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_build = {
            executor.submit(
                client.set_node_provision_state,
                node,
                "clean",
                clean_steps=clean_steps,
                wait=True
            ): node for node in nodes
        }

        done, not_done = futures.wait(
            future_to_build,
            timeout=node_timeout,
            return_when=futures.ALL_COMPLETED
        )

    nodes_wait = list()
    for job in done:
        if job._exception:
            result.update(
                {
                    future_to_build[job]: {
                        'msg': 'Cleaning failed for node {}: {}'.format(
                            future_to_build[job],
                            str(job._exception)
                        ),
                        'failed': True,
                        'info': {}
                    }
                }
            )
        else:
            nodes_wait.append(future_to_build[job])
    else:
        if not_done:
            for job in not_done:
                result.update(
                    {
                        future_to_build[job]: {
                            'msg': 'Cleaning incomplete for node {}'.format(
                                future_to_build[job],
                            ),
                            'failed': True,
                            'info': {}
                        }
                    }
                )

    nodes_to_delete = []
    for node in nodes_wait:
        node_info = client.get_node(
            node,
            fields=['provision_state', 'last_error']
        ).to_dict()
        state = node_info['provision_state']
        if state == 'manageable':
            nodes_to_delete.append(node)
            result.update({node: {
                'msg': 'Successful cleaning for node %s' % node,
                'failed': False,
                'error': '',
                'info': node_info,
            }})
        elif state not in [
                'manageable', 'cleaning', 'clean wait', 'available']:
            nodes_to_delete.append(node)
            result.update({node: {
                'msg': 'Failed cleaning for node %s: %s' % (
                    node,
                    node_info['last_error'] or 'state %s' % state),
                'failed': True,
                'info': node_info,
            }})

    for node in nodes_to_delete:
        nodes_wait.remove(node)

    if nodes_wait:
        for node in nodes_wait:
            node_info = client.get_node(
                node,
                fields=['provision_state', 'last_error']
            ).to_dict()
            state = node_info['provision_state']
            result.update({node: {
                'msg': 'Timeout exceeded for node %s: '
                       'node is in state %s' % (node, state),
                'failed': True,
                'info': node_info,
            }})

    return result


def main():

    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(
        argument_spec,
        supports_check_mode=False,
        **module_kwargs
    )
    if not module.params['node_uuid'] and not module.params['node_name']:
        module.fail_json(msg="Provide either UUID or names of nodes!")
    sdk, cloud = openstack_cloud_from_module(module)

    try:
        result = parallel_nodes_cleaning(cloud, module)
        module_results = {"changed": True}
        failed_nodes = [k for k, v in result.items() if v['failed']]
        passed_nodes = [k for k, v in result.items() if not v['failed']]
        infos = [{k: v['info']} for k, v in result.items()]
        all_errors = "\n".join(
            [v['msg'] for k, v in result.items() if v['failed']])
        failed = len(failed_nodes)
        if failed > 0:
            message = ("Cleaning completed with failures. %s node(s) failed."
                       "Errors: %s"
                       % (failed, all_errors))
            module_results.update({'failed': True})
        else:
            message = "Cleaning completed successfully: %s nodes" % len(
                module.params["node_uuid"])
        module_results.update({
            "baremetal_data": infos if not module.params['quiet'] else {},
            "failed_nodes": failed_nodes,
            "passed_nodes": passed_nodes,
            "msg": message
        })
        module.exit_json(**module_results)

    except sdk.exceptions.OpenStackCloudException as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
