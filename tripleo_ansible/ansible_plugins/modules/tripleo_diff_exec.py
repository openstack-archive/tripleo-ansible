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

from ansible.module_utils.basic import AnsibleModule

import filecmp
import os
import shutil
import subprocess
import traceback
import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: tripleo_diff_exec
short_description: Run a command if a file is different than a previous one
version_added: "2.9"
author: "Alex Schultz (@mwhahaha)"
description:
  - Takes a file path and compares it to a previous version (created by this
    module) and runs a command if the contents are different.
options:
  command:
    description:
      - Command to run if the state file has changed since the last run. If the
        previous version of the state file does not exist, the command is run.
    required: true
    type: str
  environment:
    description:
      - Environment variables to be passed to the command being run
    required: false
    type: dict
    default: {}
  return_codes:
    description:
      - List of valid return code values for the command
    required: false
    type: list
    default: [0]
  state_file:
    description:
      - File to use to compare to the previous version
    required: true
    type: str
  state_file_suffix:
    description:
      - Suffix to use to store the previous version of the file for comparisons
        between runs
    required: false
    default: -tripleo_diff_exec
    type: str
'''

RETURN = '''
'''

EXAMPLES = '''
- name: Run command if file is changed
  tripleo_diff_exec:
    command: systemctl restart foo.service
    state_file: /var/lib/my-file
    state_file_suffix: -foo
    environment:
      FOO: bar
'''


def run(module):
    results = dict(
        changed=False
    )

    args = module.params
    command = args.get('command')
    environment = args.get('environment', {})
    return_codes = args.get('return_codes', [0])
    state_file = args.get('state_file')
    state_file_bkup = args.get('state_file') + args.get('state_file_suffix',
                                                        '-tripleo_diff_exec')

    if not os.path.exists(state_file):
        results['failed'] = True
        results['error'] = "Missing state file"
        results['msg'] = "State file does not exist: %s" % state_file
    elif (not os.path.exists(state_file_bkup)
            or not filecmp.cmp(state_file, state_file_bkup, shallow=False)):
        # run command
        try:
            tmp_environment = os.environ.copy()
            tmp_environment.update(environment)
            r = subprocess.run(command, shell=True, env=tmp_environment,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
            if r.returncode in return_codes:
                results['changed'] = True
                # copy old to bkup
                shutil.copy2(state_file, state_file_bkup)
            else:
                results['failed'] = True
                results['error'] = "Failed running command"
                results['msg'] = ("Error running %s. rc: %s, stdout: %s, "
                                  "stderr: %s" % (command, r.returncode,
                                                  r.stdout, r.stderr))
        except Exception as e:
            results['failed'] = True
            results['error'] = traceback.format_exc()
            results['msg'] = "Unhandled exception: %s" % e

    module.exit_json(**results)


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=False,
    )
    run(module)


if __name__ == '__main__':
    main()
