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

import metalsmith

import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: tripleo_baremetal_populate_environment
short_description: Add parameters to a heat environment with instance data
version_added: "2.9"
author: "Steve Baker (@stevebaker)"
description:
  - Takes a list of existing instances and a heat environment file
    and appends to that environment with instance-specific parameters such
    as the port map.
options:
  instances:
    description:
      - List of instance uuids to use for building the environment.
    required: true
    type: list
    elements: dict
    suboptions:
      id:
        description
          - Node UUID to look up node details
      type: str
  environment:
    description:
      - Existing heat environment data to add to
    type: dict
    default: {}
  ctlplane_network:
    description:
      - Name of control plane network
    default: ctlplane
  templates:
    description:
      - The path to tripleo-heat-templates root directory
    type: path
    default: /usr/share/openstack-tripleo-heat-templates
'''

RETURN = '''
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
                "DeployedServerPortMap": {}
                "HostnameMap": {
                    "overcloud-controller-0": "overcloud-controller-0",
                    "overcloud-controller-1": "overcloud-controller-1",
                    "overcloud-controller-2": "overcloud-controller-2",
                    "overcloud-novacompute-0": "overcloud-novacompute-0",
                    "overcloud-novacompute-1": "overcloud-novacompute-1",
                    "overcloud-novacompute-2": "overcloud-novacompute-2"
                }
            },
            "resource_registry": {
                "OS::TripleO::DeployedServer::ControlPlanePort": "/usr/share/openstack-tripleo-heat-templates/deployed-server/deployed-neutron-port.yaml"
            }
        }
'''  # noqa


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

    instance_uuids = [i['id'] for i in module.params['instances']]

    try:
        env = bd.populate_environment(
            instance_uuids=instance_uuids,
            provisioner=provisioner,
            environment=module.params['environment'],
            ctlplane_network=module.params['ctlplane_network'],
            templates=module.params['templates']
        )
        module.exit_json(
            changed=False,
            environment=env
        )
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
