#!/usr/bin/python
# Copyright 2021 Red Hat, Inc.
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

import netaddr
import os
import yaml

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: tripleo_findif_for_ip
author:
    - OpenStack TripleO Contributors
version_added: '1.0'
short_description: Finds the interface that an IP address is assigned to.
notes: []
requirements:
description:
    - Locates the interface that has the provided IP address assigned to it
options:
  ip_address:
    description:
      - The IP address to look for
    type: str

  debug:
    description:
      - Print debug output.
    type: bool
    default: false
"""

EXAMPLES = """
- name: Find the interface for the provided IP address
  tripleo_find_if_for_ip:
    ip_address: 192.168.24.22
"""

RETURN = """
interface:
  description:
    - if not empty, the interface that has the given IP address
  returned: always
  type: str
"""


def find_interface(module, ip_address):
    rc, out, err = module.run_command(['ip', '-br', 'addr'])

    result = {
        'changed': False,
        'interface': ''
    }
    for ifline in out.splitlines():
        columns = ifline.strip().split()
        if len(columns) == 0:
            continue
        interface_name = columns[0]
        ips = columns[2:]
        for addr in ips:
            ip = addr.split('/')[0]
            if ip == ip_address:
                result['interface'] = interface_name
                return result
    return result


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
    )
    results = dict(
        changed=False
    )
    # parse args
    ip_address = module.params['ip_address']

    if netaddr.valid_ipv6(ip_address) or netaddr.valid_ipv4(ip_address):
        results = find_interface(module, ip_address)
    else:
        module.fail_json(msg='%s is not a valid ip address' % ip_address)

    module.exit_json(**results)


if __name__ == '__main__':
    main()
