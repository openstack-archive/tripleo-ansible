#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat, Inc.
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
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
module: podman_volume_info
author:
  - "Sagi Shnaidman (@sshnaidm)"
version_added: '2.10'
short_description: Gather info about podman volumes
notes: []
description:
  - Gather info about podman volumes with podman inspect command.
requirements:
  - "Podman installed on host"
options:
  name:
    description:
      - Name of the volume
    type: str
  executable:
    description:
      - Path to C(podman) executable if it is not in the C($PATH) on the
        machine running C(podman)
    default: 'podman'
    type: str
"""
EXAMPLES = """
- name: Gather info about all present volumes
  podman_volume_info:

- name: Gather info about specific volume
  podman_volume_info:
    name: specific_volume
"""
RETURN = """
volumes:
    description: Facts from all or specified volumes
    returned: always
    type: list
    sample: [
                {
                "name": "testvolume",
                "labels": {},
                "mountPoint": "/home/ansible/.local/share/testvolume/_data",
                "driver": "local",
                "options": {},
                "scope": "local"
                }
        ]
"""

import json
from ansible.module_utils.basic import AnsibleModule


def get_volume_info(module, executable, name):
    command = [executable, 'volume', 'inspect']
    if name:
        command.append(name)
    else:
        command.append("--all")
    rc, out, err = module.run_command(command)
    if rc != 0 or 'no such volume' in err:
        module.fail_json(msg="Unable to gather info for %s: %s" % (name or 'all volumes', err))
    if not out or json.loads(out) is None:
        return [], out, err
    return json.loads(out), out, err


def main():
    module = AnsibleModule(
        argument_spec=dict(
            executable=dict(type='str', default='podman'),
            name=dict(type='str')
        ),
        supports_check_mode=True,
    )

    name = module.params['name']
    executable = module.get_bin_path(module.params['executable'], required=True)

    inspect_results, out, err = get_volume_info(module, executable, name)

    results = {
        "changed": False,
        "volumes": inspect_results,
        "stderr": err
    }

    module.exit_json(**results)


if __name__ == '__main__':
    main()
