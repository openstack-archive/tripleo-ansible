#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat, Inc.
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

import json
import os
import yaml

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: tripleo_container_configs
author:
  - "TripleO team"
version_added: '2.9'
short_description: Generate Container configs in JSON
notes: []
description:
  - It will generate the Container JSON configs from config-download data in
    YAML.
requirements:
  - None
options:
  config_data:
    description:
      - Content of kolla_config.yaml file (must be YAML format)
    type: dict
    required: true
"""

EXAMPLES = """
- name: Write container config json files
  tripleo_container_configs:
    config_data:
      /var/lib/kolla/config_files/ceilometer_agent_compute.json:
        command: /usr/bin/ceilometer-polling compute
        config_files:
        - dest: /
          merge: true
          preserve_properties: true
          source: /var/lib/kolla/config_files/src/*
      /var/lib/kolla/config_files/ceilometer_agent_notification.json:
        command: /usr/bin/ceilometer-agent-notification
        config_files:
        - dest: /
          merge: true
          preserve_properties: true
          source: /var/lib/kolla/config_files/src/*
"""


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
    )
    results = dict(
        changed=False
    )

    # parse args
    args = module.params

    # Set parameters
    config_data = args['config_data']

    if not module.check_mode:
        for path, config in config_data.items():
            with open(path, "wb") as config_file:
                config_file.write(json.dumps(config, indent=2).encode('utf-8'))
            os.chmod(path, 0o600)
            results['changed'] = True

    module.exit_json(**results)


if __name__ == '__main__':
    main()
