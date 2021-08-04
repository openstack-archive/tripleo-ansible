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

from ansible.module_utils.basic import AnsibleModule
try:
    from ansible.module_utils import tripleo_common_utils as tc
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import tripleo_common_utils as tc
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: tripleo_get_dpdk_nics_numa_info
author:
  - Jaganathan Palanisamy <jpalanis@redhat.com>
version_added: '2.8'
short_description: Gets the DPDK nics numa details
notes: []
description:
  - This module gets the DPDK nics numa details.
options:
  container:
    description:
      - Name of plan / container
        This parameter is required.
    type: str
    required: true
  role_name:
    description:
      - Name of the role
        This parameter is required.
    type: str
    required: true
  inspect_data:
    description:
      - Hardware data
        This parameter is required
    required: True
    type: dict
  mtu_default:
    description:
      - MTU default value
    default: 1500
    required: False
    type: int
"""

EXAMPLES = """
- name: Gets DPDK nics numa details
  tripleo_get_dpdk_nics_numa_info:
    container: overcloud
    role_name: ComputeOvsDpdk
    inspect_data: {}
    mtu_default: 1500
"""

RETURN = """
dpdk_nics_numa_info:
    description:
      - DPDK NICS NUMA details list
    returned: always
    type: list
"""

import glob
import json
import os
import re
import yaml

from tripleo_common.utils import stack_parameters as stack_param_utils


# Sorting active nics
def _natural_sort_key(s):
    nsre = re.compile('([0-9]+)')
    return [int(text) if text.isdigit() else text
            for text in re.split(nsre, s)]


# Finds embedded nic or not
def _is_embedded_nic(nic):
    if (nic.startswith('em') or nic.startswith('eth')
            or nic.startswith('eno')):
        return True
    return False


# Ordering the nics
def _ordered_nics(interfaces):
    embedded_nics = []
    nics = []
    for iface in interfaces:
        nic = iface.get('name', '')
        if _is_embedded_nic(nic):
            embedded_nics.append(nic)
        else:
            nics.append(nic)
    active_nics = (sorted(embedded_nics,
                          key=_natural_sort_key) + sorted(
                              nics, key=_natural_sort_key))
    return active_nics


# Gets numa node id for physical NIC name
def _find_numa_node_id(numa_nics, nic_name):
    for nic_info in numa_nics:
        if nic_info.get('name', '') == nic_name:
            return nic_info.get('numa_node', None)
    return None


# Get physical interface name for NIC name
def _get_physical_iface_name(ordered_nics, nic_name):
    if nic_name.startswith('nic'):
        # Nic numbering, find the actual interface name
        nic_number = int(nic_name.replace('nic', ''))
        if nic_number > 0:
            iface_name = ordered_nics[nic_number - 1]
            return iface_name
    return nic_name


# Gets dpdk interfaces and mtu info for dpdk config
# Default mtu(recommended 1500) is used if no MTU is set for DPDK NIC
def _get_dpdk_interfaces(dpdk_objs, mtu_default):
    mtu = mtu_default
    dpdk_ifaces = []
    for dpdk_obj in dpdk_objs:
        obj_type = dpdk_obj.get('type')
        mtu = dpdk_obj.get('mtu', mtu_default)
        if obj_type == 'ovs_dpdk_port':
            # Member interfaces of ovs_dpdk_port
            dpdk_ifaces.extend(dpdk_obj.get('members', []))
        elif obj_type == 'ovs_dpdk_bond':
            # ovs_dpdk_bond will have multiple ovs_dpdk_ports
            for bond_member in dpdk_obj.get('members', []):
                if bond_member.get('type') == 'ovs_dpdk_port':
                    dpdk_ifaces.extend(bond_member.get('members', []))
    return (dpdk_ifaces, mtu)


def _get_dpdk_nics_numa_info(network_configs, inspect_data, mtu_default=1500):
    interfaces = inspect_data.get('inventory',
                                  {}).get('interfaces', [])
    # Checks whether inventory interfaces information is not available
    # in introspection data.
    if not interfaces:
        msg = 'Introspection data does not have inventory.interfaces'
        raise tc.DeriveParamsError(msg)

    numa_nics = inspect_data.get('numa_topology',
                                 {}).get('nics', [])
    # Checks whether numa topology nics information is not available
    # in introspection data.
    if not numa_nics:
        msg = 'Introspection data does not have numa_topology.nics'
        raise tc.DeriveParamsError(msg)

    active_interfaces = [iface for iface in interfaces
                         if iface.get('has_carrier', False)]

    # Checks whether active interfaces are not available
    if not active_interfaces:
        msg = 'Unable to determine active interfaces (has_carrier)'
        raise tc.DeriveParamsError(msg)

    dpdk_nics_numa_info = []
    ordered_nics = _ordered_nics(active_interfaces)
    # Gets DPDK network config and parses to get DPDK NICs
    # with mtu and numa node id
    for config in network_configs:
        if config.get('type', '') == 'ovs_user_bridge':
            bridge_name = config.get('name', '')
            addresses = config.get('addresses', [])
            members = config.get('members', [])
            dpdk_ifaces, mtu = _get_dpdk_interfaces(members, mtu_default)
            for dpdk_iface in dpdk_ifaces:
                type = dpdk_iface.get('type', '')
                if type == 'sriov_vf':
                    name = dpdk_iface.get('device', '')
                else:
                    name = dpdk_iface.get('name', '')
                phy_name = _get_physical_iface_name(
                     ordered_nics, name)
                node = _find_numa_node_id(numa_nics, phy_name)
                if node is None:
                    msg = ('Unable to determine NUMA node for '
                           'DPDK NIC: %s' % phy_name)
                    raise tc.DeriveParamsError(msg)

                dpdk_nic_info = {'name': phy_name,
                                 'numa_node': node,
                                 'mtu': mtu,
                                 'bridge_name': bridge_name,
                                 'addresses': addresses}
                dpdk_nics_numa_info.append(dpdk_nic_info)
    return dpdk_nics_numa_info


def main():
    result = dict(
        dpdk_nics_numa_info=[],
        success=False,
        error=None,
    )

    module = AnsibleModule(
        openstack_full_argument_spec(
            **yaml.safe_load(DOCUMENTATION)['options']
        ),
        **openstack_module_kwargs()
    )
    _, conn = openstack_cloud_from_module(module)
    tripleo = tc.TripleOCommon(session=conn.session)
    network_configs = {}
    try:
        # Get the network configs data for the required role name
        network_configs = stack_param_utils.get_network_configs(
            tripleo.get_object_client(),
            tripleo.get_orchestration_client(),
            container=module.params["container"],
            role_name=module.params["role_name"]
        )
    except Exception as exp:
        result['error'] = str(exp)
        result['msg'] = 'Error getting network configs for role name {}: {}'.format(
            module.params["role_name"],
            exp
        )
        module.fail_json(**result)

    try:
        result['dpdk_nics_numa_info'] = _get_dpdk_nics_numa_info(
            module.params["network_configs"],
            module.params["inspect_data"],
            module.params["mtu_default"]
        )
    except tc.DeriveParamsError as dexp:
        result['error'] = str(dexp)
        result['msg'] = 'Error pulling DPDK NICs NUMA information : {}'.format(
            dexp
        )
        module.fail_json(**result)
    except Exception as exp:
        result['error'] = str(exp)
        result['msg'] = 'Error pulling DPDK NICs NUMA information : {}'.format(
            exp
        )
        module.fail_json(**result)
    else:
        result['success'] = True
        module.exit_json(**result)


if __name__ == '__main__':
    main()
