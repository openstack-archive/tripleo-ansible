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
module: os_baremetal_provide_node
short_description: Provide baremetal nodes of Ironic
extends_documentation_fragment: openstack
author:
  - "Sagi Shnaidman (@sshnaidm)"
version_added: "2.10"
description:
    - Provide Ironic nodes.
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
    failfast:
      description:
        - Don't wait for other nodes to provide if at least one failed
      type: bool
      default: True
    wait_for_bridge_mappings:
      description:
        - Whether to poll neutron agents for an agent with populated mappings
          before doing the provide
      type: bool
      default: False
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
- os_baremetal_provide_node:
    cloud: undercloud
    node_uuid:
      - 0593c323-ad62-4ce9-b431-3c322827a428

- os_baremetal_provide_node:
    cloud: undercloud
    failfast: False
    node_name:
      - baremetal-85-3

'''
import yaml
from openstack.exceptions import ResourceNotFound, ResourceFailure, ResourceTimeout
from openstack.utils import iterate_timeout

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module


def get_info_nodes(nodes_wait, msg, result, client):
    for node in nodes_wait:
        node_info = client.get_node(
            node,
            fields=['provision_state', 'last_error']
        ).to_dict()
        state = node_info['provision_state']
        if state == 'available':
            result.update({node: {
                'msg': 'Successful providing for node %s' % node,
                'failed': False,
                'error': '',
                'info': node_info,
            }})
        else:
            result.update({node: {
                'msg': 'Failed providing for node %s: %s' % (
                    node,
                    node_info['last_error'] or 'state %s' % state),
                'failed': True,
                'info': node_info,
            }})

    return result, msg


def wait_for_unlocked(client, node, timeout):
    timeout_msg = 'Timeout waiting for node %s to be unlocked' % node
    for count in iterate_timeout(timeout, timeout_msg):
        node_info = client.get_node(
            node,
            fields=['reservation']
        ).to_dict()
        if node_info['reservation'] is None:
            return


def wait_for_bridge_mapping(conn, node):
    client = conn.network

    # (bshephar) We need to use the node UUID rather than the name when we
    # check for the Neutron agents:
    # https://bugs.launchpad.net/tripleo/+bug/1966155
    node_id = conn.baremetal.find_node(node, ignore_missing=False).id

    timeout_msg = ('Timeout waiting for node %s to have bridge_mappings '
                   'set in the ironic-neutron-agent entry' % node)
    # default agent polling period is 30s, so wait 60s
    timeout = 60
    for count in iterate_timeout(timeout, timeout_msg):
        agents = list(client.agents(host=node_id, binary='ironic-neutron-agent'))
        if agents:
            if agents[0].configuration.get('bridge_mappings'):
                return


def parallel_nodes_providing(conn, module):
    client = conn.baremetal
    node_timeout = module.params['timeout']
    wait_for_bridge_mappings = module.params['wait_for_bridge_mappings']
    nodes = list(set(module.params['node_uuid'] + module.params['node_name']))
    result = {}
    nodes_wait = nodes[:]
    for node in nodes:
        try:
            wait_for_unlocked(client, node, node_timeout)

            if wait_for_bridge_mappings:
                wait_for_bridge_mapping(conn, node)

            client.set_node_provision_state(
                node,
                "provide",
                wait=False)
        except Exception as e:
            nodes_wait.remove(node)
            result.update({node: {
                'msg': 'Can not start providing for node %s: %s' % (
                    node, str(e)),
                'failed': True,
                'info': {}
            }})
            if module.params['failfast']:
                return get_info_nodes(
                    nodes_wait,
                    msg="Failed providing nodes because of: %s" % str(e),
                    result=result, client=client)

    try:
        client.wait_for_nodes_provision_state(
            nodes=nodes_wait,
            expected_state='available',
            timeout=node_timeout,
            abort_on_failed_state=module.params['failfast'],
            # fail=False  # use it when new openstacksdk is available
        )
    except ResourceFailure as e:
        return get_info_nodes(nodes_wait,
                              msg="Failed providing nodes because of failure: "
                                  "%s" % str(e),
                              result=result, client=client)
    except ResourceTimeout as e:
        return get_info_nodes(nodes_wait,
                              msg="Failed providing nodes because of timeout: "
                                  "%s" % str(e),
                              result=result, client=client)
    else:
        return get_info_nodes(nodes_wait, msg="", result=result, client=client)


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
        result, msg = parallel_nodes_providing(cloud, module)
        module_results = {"changed": True}
        failed_nodes = [k for k, v in result.items() if v['failed']]
        passed_nodes = [k for k, v in result.items() if not v['failed']]
        infos = [{k: v['info']} for k, v in result.items()]
        all_errors = "\n".join(
            [msg] + [v['msg'] for k, v in result.items() if v['failed']])
        failed = len(failed_nodes)
        if failed > 0:
            message = ("Providing completed with failures. %s node(s) failed."
                       "Errors: %s"
                       % (failed, all_errors))
            module_results.update({'failed': True})
        else:
            message = "Providing completed successfully: %s nodes" % len(
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
