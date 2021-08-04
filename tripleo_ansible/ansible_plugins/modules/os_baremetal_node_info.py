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
module: os_baremetal_node_info
short_description: Show info about baremetal nodes of Ironic
extends_documentation_fragment: openstack
author:
  - "Sagi Shnaidman (@sshnaidm)"
version_added: "2.10"
description:
    - Requests Ironic for nodes info.
options:
    mac:
      description:
        - unique mac address that is used to attempt to identify the host.
      type: str
      required: False
    uuid:
      description:
        - globally unique identifier (UUID) to identify the host.
      type: str
      required: False
    name:
      description:
        - unique name identifier to identify the host in Ironic.
      type: str
      required: False
    ironic_url:
      description:
        - If noauth mode is utilized, this is required to be set to the
          endpoint URL for the Ironic API.
          Use with "auth" and "auth_type" settings set to None.
      type: str
      required: False
    filters:
      description:
        - Filters to pass for Ironic client
      type: dict
      default: {}
      suboptions:
        associated:
          description:
            - Only return those which are, or are not, associated with an
              instance_id.
          type: str
          required: False
        conductor_group:
          description:
            -  Only return those in the specified conductor_group.
          type: str
          required: False
        driver:
          description:
            - Only return those with the specified driver.
          type: str
          required: False
        fault:
          description:
            - Only return those with the specified fault type.
          type: str
          required: False
        instance_id:
          description:
            - Only return the node with this specific instance UUID or an empty
              set if not found.
          type: str
          required: False
        is_maintenance:
          description:
            - Only return those with maintenance set to True or False.
          type: bool
          required: False
        limit:
          description:
            - Requests at most the specified number of nodes be returned from
              the query.
          type: int
          required: False
        marker:
          description:
            - Specifies the ID of the last-seen node. Use the limit parameter
              to make an initial limited request and use the ID of the
              last-seen node from the response as the marker value in a
              subsequent limited request.
          type: str
          required: False
        provision_state:
          description:
            - Only return those nodes with the specified provision_state.
          type: str
          required: False
        resource_class:
          description:
            - Only return those with the specified resource_class.
          type: str
          required: False
        sort_dir:
          description:
            - Sorts the response by the requested sort direction.
                A valid value is asc (ascending) or desc (descending). Default is asc.
                You can specify multiple pairs of sort key and sort direction query parameters.
                If you omit the sort direction in a pair, the API uses the natural sorting direction of
                the server attribute that is provided as the sort_key.
          type: str
          required: False
          choices:
            - asc
            - desc
        sort_key:
          description:
            - Sorts the response by the this attribute value. Default is id.
                You can specify multiple pairs of sort key and sort direction query parameters.
                If you omit the sort direction in a pair, the API uses the natural sorting direction
                of the server attribute that is provided as the sort_key.
          type: str
          required: False

requirements: ["openstacksdk"]
'''

RETURN = '''
baremetal_nodes:
    description: Dictionary of new facts representing discovered properties of
                 the node.
    returned: changed
    type: list
    sample: [
                {
                    "allocation_id": null,
                    "bios_interface": "no-bios",
                    "boot_interface": "ipxe",
                    "chassis_id": null,
                    "clean_step": {},
                    "conductor": "undercloud.localdomain",
                    "conductor_group": "",
                    "console_interface": "ipmitool-socat",
                    "created_at": "2019-11-13T09:01:36+00:00",
                    "deploy_interface": "iscsi",
                    "deploy_step": {},
                    "driver": "ipmi",
                    "driver_info": {
                        "deploy_kernel": "file:///var/lib/ironic/httpboot/agent.kernel",
                        "deploy_ramdisk": "file:///var/lib/ironic/httpboot/agent.ramdisk",
                        "ipmi_address": "192.168.100.19",
                        "ipmi_password": "******",
                        "ipmi_username": "admin",
                        "rescue_kernel": "file:///var/lib/ironic/httpboot/agent.kernel",
                        "rescue_ramdisk": "file:///var/lib/ironic/httpboot/agent.ramdisk"
                    },
                    "driver_internal_info": {
                        "agent_cached_clean_steps": {
                            "deploy": [
                                {
                                    "abortable": true,
                                    "interface": "deploy",
                                    "priority": 99,
                                    "reboot_requested": false,
                                    "step": "erase_devices_metadata"
                                },
                                {
                                    "abortable": true,
                                    "interface": "deploy",
                                    "priority": 10,
                                    "reboot_requested": false,
                                    "step": "erase_devices"
                                }
                            ],
                            "raid": [
                                {
                                    "abortable": true,
                                    "interface": "raid",
                                    "priority": 0,
                                    "reboot_requested": false,
                                    "step": "create_configuration"
                                },
                                {
                                    "abortable": true,
                                    "interface": "raid",
                                    "priority": 0,
                                    "reboot_requested": false,
                                    "step": "delete_configuration"
                                }
                            ]
                        },
                        "agent_cached_clean_steps_refreshed": "2019-11-13 09:06:10.069764",
                        "agent_continue_if_ata_erase_failed": false,
                        "agent_enable_ata_secure_erase": true,
                        "agent_erase_devices_iterations": 1,
                        "agent_erase_devices_zeroize": true,
                        "agent_last_heartbeat": "2019-11-13T09:27:45.360292",
                        "agent_url": "http://192.168.24.11:9999",
                        "agent_version": "5.1.0.dev23",
                        "clean_steps": null,
                        "deploy_boot_mode": "bios",
                        "deploy_steps": null,
                        "disk_erasure_concurrency": 1,
                        "hardware_manager_version": {
                            "generic_hardware_manager": "1.1"
                        },
                        "is_whole_disk_image": false,
                        "last_power_state_change": "2019-11-13T09:30:28.924594",
                        "root_uuid_or_disk_id": "ccd53b26-429c-494a-ae99-bd244e6c488b"
                    },
                    "extra": {},
                    "fault": null,
                    "id": "400b3cd0-d134-417b-8f0e-63e273e01e5a",
                    "inspect_interface": "inspector",
                    "instance_id": "6911e6d6-c2e0-41df-ad88-3e4ab014e24c",
                    "instance_info": {
                        "configdrive": "******",
                        "display_name": "overcloud-controller-2",
                        "image_source": "e1712507-7d7c-4ee1-8cc7-155cc2c698f5",
                        "local_gb": "79",
                        "memory_mb": "4096",
                        "nova_host_id": "undercloud.localdomain",
                        "root_gb": "40",
                        "swap_mb": "0",
                        "vcpus": "1"
                    },
                    "is_automated_clean_enabled": null,
                    "is_console_enabled": false,
                    "is_maintenance": false,
                    "is_protected": false,
                    "last_error": null,
                    "links": [
                        {
                            "href": "https://192.168.24.2:13385/v1/nodes/400b3cd0-d134-417b-8f0e-63e273e01e5a",
                            "rel": "self"
                        },
                        {
                            "href": "https://192.168.24.2:13385/nodes/400b3cd0-d134-417b-8f0e-63e273e01e5a",
                            "rel": "bookmark"
                        }
                    ],
                    "location": {
                        "cloud": "undercloud",
                        "project": {
                            "domain_id": null,
                            "domain_name": "Default",
                            "id": "5cd4120087264bb2b28f4413501e639a",
                            "name": "admin"
                        },
                        "region_name": "regionOne",
                        "zone": null
                    },
                    "maintenance_reason": null,
                    "management_interface": "ipmitool",
                    "name": "baremetal-1010-0",
                    "network_interface": "flat",
                    "port_groups": [
                        {
                            "href": "https://192.168.24.2:13385/v1/nodes/400b3cd0-d134-417b-8f0e-63e273e01e5a/portgroups",
                            "rel": "self"
                        },
                        {
                            "href": "https://192.168.24.2:13385/nodes/400b3cd0-d134-417b-8f0e-63e273e01e5a/portgroups",
                            "rel": "bookmark"
                        }
                    ],
                    "ports": [
                        {
                            "href": "https://192.168.24.2:13385/v1/nodes/400b3cd0-d134-417b-8f0e-63e273e01e5a/ports",
                            "rel": "self"
                        },
                        {
                            "href": "https://192.168.24.2:13385/nodes/400b3cd0-d134-417b-8f0e-63e273e01e5a/ports",
                            "rel": "bookmark"
                        }
                    ],
                    "power_interface": "ipmitool",
                    "power_state": "power on",
                    "properties": {
                        "capabilities": "cpu_vt:true,cpu_aes:true,cpu_hugepages_1g:true,cpu_hugepages:true,boot_option:local",
                        "cpu_arch": "x86_64",
                        "cpus": "4",
                        "local_gb": "79",
                        "memory_mb": "8192"
                    },
                    "protected_reason": null,
                    "provision_state": "active",
                    "raid_config": {},
                    "raid_interface": "no-raid",
                    "rescue_interface": "agent",
                    "reservation": null,
                    "resource_class": "baremetal",
                    "states": [
                        {
                            "href": "https://192.168.24.2:13385/v1/nodes/400b3cd0-d134-417b-8f0e-63e273e01e5a/states",
                            "rel": "self"
                        },
                        {
                            "href": "https://192.168.24.2:13385/nodes/400b3cd0-d134-417b-8f0e-63e273e01e5a/states",
                            "rel": "bookmark"
                        }
                    ],
                    "storage_interface": "noop",
                    "target_power_state": null,
                    "target_provision_state": null,
                    "target_raid_config": {},
                    "traits": [],
                    "updated_at": "2019-11-13T09:30:47+00:00",
                    "vendor_interface": "ipmitool"
                }
    ]
'''  # noqa

EXAMPLES = '''
# Invoke node inspection
- os_baremetal_node_info:
    name: "testnode1"

- os_baremetal_node_info:
    cloud: undercloud
    filters:
      is_maintenance: true
'''
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module


def _choose_id_value(module):
    if module.params['uuid']:
        return module.params['uuid']
    if module.params['name']:
        return module.params['name']
    return None


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
    sdk, cloud = openstack_cloud_from_module(module)

    try:
        if module.params['name'] or module.params['uuid']:
            result = cloud.get_machine(_choose_id_value(module))
        elif module.params['mac']:
            result = cloud.get_machine_by_mac(module.params['mac'])
        else:
            result = list(cloud.baremetal.nodes(details=True,
                                                **module.params['filters']))

        module.exit_json(changed=False,
                         baremetal_nodes=result)

    except sdk.exceptions.OpenStackCloudException as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
