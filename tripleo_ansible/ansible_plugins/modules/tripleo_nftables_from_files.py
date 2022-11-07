#!/usr/bin/env python3
# Copyright 2021 Red Hat, Inc.
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

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: tripleo_nftables_from_files
author:
  - Cedric Jeanneret <cjeanner@redhat.com>
version_added: '2.12'
short_description: Get yaml contents and output a single list of rules
notes: []
description:
  - This action loads multiple YAML files from a specified location, and
    appends the elements into a single list. This list can then be used within
    tripleo_nftables in order to configure the firewall.
options:
  src:
    description:
      - Source directory for the different files
    required: True
    type: str
"""

EXAMPLES = """
- name: Get nftables rules
  register: tripleo_nftables_rules
  tripleo_nftables_from_files:
    src: /var/lib/tripleo-config/firewall
"""

RETURN = """
rules:
    description: List of nftables rules built upon the files content
    returned: always
    type: dict
    sample:
        success: True
        rules:
            - rule_name: 000 accept related established
              rule:
                proto: all
                state:
                  - RELATED
                  - ESTABLISHED
            - rule_name: 010 accept ssh from all
              rule:
                proto: tcp
                dport: 22
"""


class main():
    """Main method for the module
    """

    result = dict(sucess=False, error="")
    module = AnsibleModule(
            argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
            supports_check_mode=False,
            )

    dir_src = module.params.get('src', None)
    if dir_src is None:
        result['error'] = 'Missing required parameter: src'
        result['msg'] = result['error']
        module.fail_json(**result)

    if not os.path.exists(dir_src):
        result['error'] = 'Missing directory on host: {}'.format(dir_src)
        result['msg'] = result['error']
        module.fail_json(**result)

    rules = []
    for r_file in os.listdir(dir_src):
        with open(os.path.join(dir_src, r_file), 'r') as r_data:
            try:
                parsed_yaml = yaml.safe_load(r_data)
            except Exception:
                result['error'] = 'Unable to parse {}'.format(
                    os.path.join(dir_src, r_file))
                result['msg'] = result['error']
                module.fail_json(**result)
            rules.extend(parsed_yaml)
    result['rules'] = sorted(rules, key=lambda r: r['rule_name'])
    result['success'] = True
    module.exit_json(**result)

if __name__ == '__main__':
    main()
