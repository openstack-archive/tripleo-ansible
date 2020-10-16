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

DOCUMENTATION = """
module: lvm2_physical_devices_facts
short_description: Gather list of block devices in use by LVM2
version_added: '1.0.0'
description: Gather list of block devices in use by LVM2 as PVs
author:
  - "Giulio Fidente (@gfidente)"
"""

EXAMPLES = """
- name: Get list of LVM2 PVs
  lvm2_physical_devices_facts:
"""

RETURN = """
ansible_facts:
    description: List of PVs in use
    returned: always
    type: dict
    contains:
      lvm2_active_pvs:
        description: List of LVM2 volumes hosting active LVs
        type: list
        returned: always but it might be empty
        sample: ['/dev/sdb2']
"""

from ansible.module_utils.basic import AnsibleModule


def get_vgs_with_active_lvs(module):
    command = ['lvs', '--noheadings', '--options', 'vg_name', '--select', 'lv_active=active']
    rc, out, err = module.run_command(command)
    if rc != 0:
        module.fail_json(msg="Failed to run LVM2 lvs command", err=err)
    if not out:
        return []
    vgs = list(set(out.split()))
    return vgs


def get_pvs_in_use_by_active_vg(module, active_vg):
    command = ['vgs', '--noheadings', '--options', 'pv_name', active_vg]
    rc, out, err = module.run_command(command)
    if rc != 0:
        module.fail_json(msg="Failed to run LVM2 vgs command for %s" % (active_vg), err=err)
    if not out:
        return []
    pvs = list(set(out.split()))
    return pvs


def run_module():
    module_args = {}

    result = dict(
        changed=False,
        ansible_facts=dict(),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    if module.check_mode:
        module.exit_json(**result)

    active_vgs = get_vgs_with_active_lvs(module)
    active_pvs = []
    for vg in active_vgs:
        active_pvs.extend(get_pvs_in_use_by_active_vg(module, vg))
    pvs = {'lvm2_active_pvs': list(set(active_pvs))}
    result['ansible_facts'] = pvs

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
