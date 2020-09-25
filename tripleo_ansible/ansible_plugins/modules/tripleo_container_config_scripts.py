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

import os
import yaml

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: tripleo_container_config_scripts
author:
  - "TripleO team"
version_added: '2.9'
short_description: Generate container config scripts
notes: []
description:
  - It will generate the TripleO container config scripts.
requirements:
  - None
options:
  config_data:
    description:
      - Content of container_config_scripts.yaml file (must be YAML format)
    type: dict
    required: true
  config_dir:
    description:
      - Directory where config scripts will be written.
    type: str
    default: /var/lib/container-config-scripts
"""

EXAMPLES = """
- name: Write container config scripts
  tripleo_container_config_scripts:
    config_data:
      container_puppet_apply.sh:
        content: "#!/bin/bash\npuppet apply"
        mode: "0700"
    config_dir: /var/lib/container-config-scripts
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
    config_dir = args['config_dir']

    if not module.check_mode:
        for path, config in config_data.items():
            # this is specific to how the files are written in config-download
            mode = config.get('mode', '0600')
            config_path = os.path.join(config_dir, path)
            with open(config_path, "w") as config_file:
                config_file.write(config['content'])
            os.chmod(config_path, int(mode, 8))
            results['changed'] = True

    module.exit_json(**results)


if __name__ == '__main__':
    main()
