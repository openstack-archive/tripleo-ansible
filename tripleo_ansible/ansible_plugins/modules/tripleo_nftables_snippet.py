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

import hashlib
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
module: tripleo_nftables_snippet
author:
  - Cedric Jeanneret <cjeanner@redhat.com>
version_added: '2.12'
short_description: Create rule snippets in selected configuration directory
notes: []
description:
  - This module validate and write the YAML in specified location/file, while
    ensuring the filename is unique in the location.
options:
  dest:
    description:
      - Destination absolute path, with filename
    required: True
    type: str
  content:
    description:
      - List of rule dicts in valid YAML
    required: False
    type: str
  state:
    description:
      - State of the snippet, either present or absent
    type: str
    default: present
"""

EXAMPLES = """
- name: Inject snippet for CI
  tripleo_nftables_snippet:
    dest: /var/lib/tripleo-config/firewall/ci-rules.yaml
    content: |
      - rule_name: 010 Allow SSH from everywhere
        rule:
          proto: tcp
          dport: 22
      - rule_name: Allow console stream from everywhere
        rule:
          proto: tcp
          dport: 19885
          state: []
"""

RETURN = """
"""


class main():
    """Main method for the module
    """

    result = dict(sucess=False, error="", changed=False)
    module = AnsibleModule(
            argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
            supports_check_mode=False,
            )

    dest = module.params.get('dest', None)
    content = module.params.get('content', None)
    state = module.params.get('state', 'present')
    if dest is None:
        result['error'] = 'Missing required parameter: dest'
        result['msg'] = result['error']
        module.fail_json(**result)
    if not os.path.isabs(dest):
        result['error'] = '"dest" parameter must be an absolute path'
        result['msg'] = result['error']
        module.fail_json(**result)
    if state == 'present' and content is None:
        result['error'] = 'Missing required parameter: content'
        result['msg'] = result['error']
        module.fail_json(**result)
    if not os.path.exists(os.path.dirname(dest)):
        result['error'] = 'Destination directory does not exist'
        result['msg'] = ("Directory {} doesn't exist, please create it "
                         "before trying to push files in there").format(
                                 os.path.dirname(dest))
        module.fail_json(**result)

    if state == 'present':
        try:
            parsed_yaml = yaml.safe_load(content)
        except Exception:
            result['error'] = "Content doesn't look like a valid YAML."
            result['msg'] = result['error']
            module.fail_json(**result)

        with open(dest, 'w') as f_output:
            yaml.dump(parsed_yaml, f_output)
            result['changed'] = True
    else:
        if os.path.exists(dest):
            try:
                os.remove(dest)
                result['changed'] = True
            except Exception:
                result['error'] = "Unable to remove {}".format(dest)
                result['msg'] = result['error']
                module.fail_json(**result)

    result['success'] = True
    module.exit_json(**result)

if __name__ == '__main__':
    main()
