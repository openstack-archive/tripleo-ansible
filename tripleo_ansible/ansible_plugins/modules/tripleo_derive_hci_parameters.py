#!/usr/bin/env python
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
"""Derive paramters for HCI (hyper-converged) deployments"""

import re
import yaml

from ansible.module_utils.basic import AnsibleModule


ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tripleo_derive_hci_parameters
short_description: Tune Nova scheduler parameters to reserve resources for collocated Ceph OSDs
description:
    - "When collocating Ceph OSDs on Nova Compute hosts (hyperconverged or hci) the Nova Scheduler does not take into account the CPU/Memory needs of the OSDs. This module returns  recommended NovaReservedHostMemory and NovaCPUAllocationRatio parmaters so that the host reseves memory and CPU for Ceph. The values are based on workload description, deployment configuration, and Ironic data. The workload description is the expected average_guest_cpu_utilization_percentage and average_guest_memory_size_in_mb."
options:
    tripleo_environment_parameters:
        description: Map from key environment_parameters from output of the tripleo_get_flatten_stack module stack_data. Used to determine number of OSDs in deployment per role
        required: True
        type: map
    tripleo_role_name:
        description: TripleO role name whose parameters are being derived
        required: True
        type: string
    introspection_data:
        description: Output of the tripleo_get_introspected_data module. Used to determine available memory and CPU of each instance from any role with the CephOSD service
        required: True
        type: map
    average_guest_cpu_utilization_percentage:
        description: Percentage of CPU utilization expected for average guest, e.g. 99 means 99% and 10 means 10%
        required: False
        type: int
        default: 0
    average_guest_memory_size_in_mb:
        description: Amount of memory in MB required by the average guest
        required: False
        type: int
        default: 0
    derived_parameters:
        description: any previously derived parameters which should be included in the final result
        required: False
        type: map
    new_heat_environment_path:
        description: Path to file new where resultant derived parameters will be written; result will be valid input to TripleO client, e.g. /home/stack/derived_paramaters.yaml
        required: False
        type: str
    report_path:
        description: Path to file new where a report on how HCI paramters were derived be written, e.g. /home/stack/hci_derived_paramaters.txt
        required: False
        type: str
author:
    - John Fulton (fultonj)
'''

EXAMPLES = '''
- name: Add Derived HCI parameters to existing derived parameters for ComputeHCI role
  tripleo_derive_hci_parameters:
    tripleo_environment_parameters: "{{ tripleo_environment_parameters }}"
    introspection_data: "{{ hw_data }}"
    derived_parameters: "{{ derived_parameters }}"
    tripleo_role_name: "ComputeHCI"
    average_guest_cpu_utilization_percentage: 90
    average_guest_memory_size_in_mb: 8192
    new_heat_environment_path: "/home/stack/hci_result.yaml"
    report_path: "/home/stack/hci_report.txt"
  register: derived_parameters_result

- name: Show derived HCI Memory result
  debug:
    msg: "{{ derived_parameters_result['derived_parameters']['ComputeHCIParameters']['NovaReservedHostMemory'] }}"

- name: Show derived HCI CPU result
  debug:
    msg: "{{ derived_parameters_result['derived_parameters']['ComputeHCIParameters']['NovaCPUAllocationRatio'] }}"

- name: Update deployment plan with derived_parameters
  tripleo_plan_parameters_update:
    container: "{{ plan }}"
    parameter_key: 'derived_parameters'
    parameters: "{{ derived_parameters_result['derived_parameters'] }}"
    validate: true
'''

RETURN = '''
message:
    description: A description of the HCI derived parameters calculation or an error message
    type: str
    returned: always
derived_parameters:
    description: map with derived hci paramters and any previously derived parameters
    required: False
    type: map
'''

MB_PER_GB = 1024


def derive(mem_gb, vcpus, osds, average_guest_memory_size_in_mb=0,
           average_guest_cpu_utilization_percentage=0,
           mem_gb_per_osd=5, vcpus_per_osd=1.0, total_memory_threshold=0.8):
    """
    Determines the recommended Nova scheduler values based on Ceph needs
    and described average Nova guest workload in CPU and Memory utilization.
    If expected guest utilization is not provided result is less accurate.
    Returns dictionary containing the keys: cpu_allocation_ratio (float),
    nova_reserved_mem_mb (int), message (string), failed (boolean).
    """
    gb_overhead_per_guest = 0.5  # based on measurement in test environment

    # seed the result
    derived = {}
    derived['message'] = ""
    derived['failed'] = False

    if average_guest_memory_size_in_mb == 0 and \
       average_guest_cpu_utilization_percentage == 0:
        workload = False
    else:
        workload = True

    # catch possible errors in parameters
    if mem_gb < 1:
        msg = "Unable to determine the amount of physical memory "
        msg += "(no 'memory_mb' found in introspection_data)."
        derived['message'] += msg + "\n"
        derived['failed'] = True

    if vcpus < 1:
        msg = "Unable to determine the number of CPU cores. "
        msg += "Either no 'cpus' found in introspection_data or "
        msg += "NovaVcpuPinSet is not correctly set."
        derived['message'] += msg + "\n"
        derived['failed'] = True

    if osds < 1:
        msg = "No OSDs were found in deployment definition under CephAnsibleDisksConfig"
        derived['message'] += msg + "\n"
        derived['failed'] = True

    if average_guest_memory_size_in_mb < 0 and workload:
        msg = "If average_guest_memory_size_in_mb is used it must be greater than 0"
        derived['message'] += msg + "\n"
        derived['failed'] = True

    if average_guest_cpu_utilization_percentage < 0 and workload:
        msg = "If average_guest_cpu_utilization_percentage is used it must be greater than 0"
        derived['message'] += msg + "\n"
        derived['failed'] = True

    left_over_mem = mem_gb - (mem_gb_per_osd * osds)

    if left_over_mem < 0:
        msg = "There is not enough memory to run %d OSDs. " % (osds)
        msg += "%d GB RAM - (%d GB per OSD * %d OSDs) is < 0" % (mem_gb, mem_gb_per_osd, osds)
        derived['message'] += msg + "\n"
        derived['failed'] = True

    if derived['failed']:
        return derived

    # perform the calculation
    if workload:
        average_guest_size = average_guest_memory_size_in_mb / float(MB_PER_GB)
        average_guest_util = average_guest_cpu_utilization_percentage * 0.01
        number_of_guests = int(left_over_mem
                               / (average_guest_size + gb_overhead_per_guest))
        nova_reserved_mem_mb = MB_PER_GB * ((mem_gb_per_osd * osds)
                                            + (number_of_guests * gb_overhead_per_guest))
        nonceph_vcpus = vcpus - (vcpus_per_osd * osds)
        guest_vcpus = nonceph_vcpus / average_guest_util
        cpu_allocation_ratio = guest_vcpus / vcpus
    else:
        nova_reserved_mem_mb = MB_PER_GB * (mem_gb_per_osd * osds)

    # save calculation results
    derived['nova_reserved_mem_mb'] = int(nova_reserved_mem_mb)
    if workload:
        derived['cpu_allocation_ratio'] = cpu_allocation_ratio

    # capture derivation details in message
    msg = "Derived Parameters results"
    msg += "\n Inputs:"
    msg += "\n - Total host RAM in GB: %d" % mem_gb
    msg += "\n - Total host vCPUs: %d" % vcpus
    msg += "\n - Ceph OSDs per host: %d" % osds
    if workload:
        msg += "\n - Average guest memory size in GB: %d" % average_guest_size
        msg += "\n - Average guest CPU utilization: %.0f%%" % \
               average_guest_cpu_utilization_percentage
    msg += "\n "
    msg += "\n Outputs:"
    if workload:
        msg += "\n - number of guests allowed based on memory = %d" % number_of_guests
        msg += "\n - number of guest vCPUs allowed = %d" % int(guest_vcpus)
        msg += "\n - nova.conf cpu_allocation_ratio = %2.2f" % cpu_allocation_ratio
    msg += "\n - nova.conf reserved_host_memory = %d MB" % nova_reserved_mem_mb
    msg += "\n "
    if workload:
        msg += "\nCompare \"guest vCPUs allowed\" to \"guests allowed based on memory\""
        msg += "\nfor actual guest count."
        msg += "\n "

    warning_msg = ""
    if nova_reserved_mem_mb > (MB_PER_GB * mem_gb * total_memory_threshold):
        warning_msg += "ERROR: %d GB is not enough memory to run hyperconverged\n" % mem_gb
        derived['failed'] = True
    if workload:
        if cpu_allocation_ratio < 0.5:
            warning_msg += "ERROR: %d is not enough vCPU to run hyperconverged\n" % vcpus
            derived['failed'] = True
        if cpu_allocation_ratio > 16.0:
            warning_msg += "WARNING: do not increase vCPU overcommit ratio beyond 16:1\n"
    else:
        warning_msg += "WARNING: the average guest workload was not provided. \n"
        warning_msg += "Both average_guest_cpu_utilization_percentage and \n"
        warning_msg += "average_guest_memory_size_in_mb are defaulted to 0. \n"
        warning_msg += "The HCI derived parameter calculation cannot set the \n"
        warning_msg += "Nova cpu_allocation_ratio. The Nova reserved_host_memory_mb \n"
        warning_msg += "will be set based on the number of OSDs but the Nova \n"
        warning_msg += "guest memory overhead will not be taken into account. \n"
    derived['message'] = warning_msg + msg

    return derived


def count_osds(tripleo_environment_parameters):
    """
    Counts the requested OSDs in the tripleo_environment_parameters.
    Returns an integer representing the count.
    """
    total = 0
    try:
        disks_config = tripleo_environment_parameters['CephAnsibleDisksConfig']
        for key in ['devices', 'lvm_volumes']:
            total = total + len(disks_config[key])
    except KeyError:
        pass
    return total


def count_memory(ironic):
    """
    Counts the memory found in the ironic introspection data as
    represented by memory_mb. Returns integer of memory in GB.
    """
    try:
        memory = ironic['data']['memory_mb'] / float(MB_PER_GB)
    except KeyError:
        memory = 0
    return memory


def convert_range_to_number_list(range_list):
    """
    Returns list of numbers from descriptive range input list
    E.g. ['12-14', '^13', '17'] is converted to [12, 14, 17]
    Returns string with error message if unable to parse input
    """
    # borrowed from jpalanis@redhat.com
    num_list = []
    exclude_num_list = []
    try:
        for val in range_list:
            val = val.strip(' ')
            if '^' in val:
                exclude_num_list.append(int(val[1:]))
            elif '-' in val:
                split_list = val.split("-")
                range_min = int(split_list[0])
                range_max = int(split_list[1])
                num_list.extend(range(range_min, (range_max + 1)))
            else:
                num_list.append(int(val))
    except ValueError as exc:
        return "Parse Error: Invalid number in input param 'num_list': %s" % exc
    return [num for num in num_list if num not in exclude_num_list]


def count_nova_vcpu_pins(module):
    """
    Returns the number of CPUs defined in NovaVcpuPinSet as set in
    the environment or derived parameters. If multiple NovaVcpuPinSet
    parameters are defined, priority is given to role, then the default
    value for all roles, and then what's in previously derived_parameters
    """
    tripleo_role_name = module.params['tripleo_role_name']
    tripleo_environment_parameters = module.params['tripleo_environment_parameters']
    derived_parameters = module.params['derived_parameters']
    # NovaVcpuPinSet can be defined in multiple locations, and it's
    # important to select the value in order of precedence:
    # 1) User specified value for this role
    # 2) User specified default value for all roles
    # 3) Value derived by a previous derived parameters playbook run
    #
    # Set an exclusive prioritized possible_location to get the NovaVcpuPinSet
    if tripleo_role_name + 'Parameters' in tripleo_environment_parameters:  # 1
        possible_location = tripleo_environment_parameters[tripleo_role_name + 'Parameters']
    elif 'NovaVcpuPinSet' in tripleo_environment_parameters:  # 2
        possible_location = tripleo_environment_parameters
    elif tripleo_role_name + 'Parameters' in derived_parameters:  # 3
        possible_location = derived_parameters[tripleo_role_name + 'Parameters']
    else:  # default the possible_location to an empty dictionary
        possible_location = {}
    if 'NovaVcpuPinSet' in possible_location:
        converted = convert_range_to_number_list(possible_location['NovaVcpuPinSet'])
        if isinstance(converted, str):
            module.fail_json(converted)
        if isinstance(converted, list):
            return len(converted)
    return 0


def count_vcpus(module):
    # if only look at ironic data if NovaVcpuPinSet is not used
    vcpus = count_nova_vcpu_pins(module)
    if vcpus == 0:
        try:
            vcpus = module.params['introspection_data']['data']['cpus']
        except KeyError:
            vcpus = 0
    return vcpus


def get_vcpus_per_osd(ironic, tripleo_environment_parameters, num_osds):
    """
    Dynamically sets the vCPU to OSD ratio based the OSD type to:
      HDD  | OSDs per device: 1 | vCPUs per device: 1
      SSD  | OSDs per device: 1 | vCPUs per device: 4
      NVMe | OSDs per device: 4 | vCPUs per device: 3
    Gets requested OSD list from tripleo_environment_parameters input
    and looks up the device type in ironic input. Returns the vCPUs
    per OSD, an explanation message, and a boolean warning if settings
    are non-optimal.
    """
    msg_pre = "OSD type distribution: \n"
    msg = ""
    cpus = 1.0
    nvme_re = re.compile('.*nvme.*')
    type_map = {}
    hdd_count = ssd_count = nvme_count = 0
    warning = False
    try:
        devices = tripleo_environment_parameters['CephAnsibleDisksConfig']['devices']
    except KeyError:
        devices = []
        msg = "No devices defined in CephAnsibleDisksConfig"
        warning = True
    try:
        ironic_disks = ironic['data']['inventory']['disks']
    except KeyError:
        ironic_disks = []
        msg = "No disks found in introspection data inventory"
        warning = True
    if len(devices) != num_osds:
        msg = "Not all OSDs are in the devices list. "
        msg += "Unable to determine hardware type for all OSDs. "
        msg += "This might be because lvm_volumes was used to define some OSDs. "
        warning = True
    elif len(devices) > 0 and len(ironic_disks) > 0:
        disks_config = tripleo_environment_parameters['CephAnsibleDisksConfig']
        for osd_dev in disks_config['devices']:
            for ironic_dev in ironic_disks:
                for key in ('name', 'by_path', 'wwn'):
                    if key in ironic_dev:
                        if osd_dev == ironic_dev[key]:
                            if 'rotational' in ironic_dev:
                                if ironic_dev['rotational']:
                                    type_map[osd_dev] = 'hdd'
                                    hdd_count += 1
                                elif nvme_re.search(osd_dev):
                                    type_map[osd_dev] = 'nvme'
                                    nvme_count += 1
                                else:
                                    type_map[osd_dev] = 'ssd'
                                    ssd_count += 1
        msg = "  HDDs %i | Non-NVMe SSDs %i | NVMe SSDs %i \n  " % \
              (hdd_count, ssd_count, nvme_count)
        if hdd_count > 0 and ssd_count == 0 and nvme_count == 0:
            cpus = 1  # default
            msg += "vCPU to OSD ratio: %i" % cpus
        elif hdd_count == 0 and ssd_count > 0 and nvme_count == 0:
            cpus = 4
            msg += "vCPU to OSD ratio: %i" % cpus
        elif hdd_count == 0 and ssd_count == 0 and nvme_count > 0:
            # did they set OSDs per device?
            if 'osds_per_device' in disks_config:
                osds_per_device = disks_config['osds_per_device']
            else:
                osds_per_device = 1  # default defined in ceph-ansible
            if osds_per_device == 4:
                # All NVMe OSDs so 12 vCPUs per OSD for optimal IO performance
                cpus = 3
            else:
                cpus = 4  # use standard SSD default
                msg += "\nWarning: osds_per_device not set to 4 "
                msg += "but all OSDs are of type NVMe. \n"
                msg += "Recomentation to improve IO: "
                msg += "set osds_per_device to 4 and re-run \n"
                msg += "so that vCPU to OSD ratio is 3 "
                msg += "for 12 vCPUs per OSD."
                warning = True
            msg += "vCPU to OSD ratio: %i" % cpus
            msg += " (found osds_per_device set to: %i)" % osds_per_device
        elif hdd_count == 0 and ssd_count == 0 and nvme_count == 0:
            cpus = 1  # default
            msg += "vCPU to OSD ratio: %i" % cpus
            msg += "\nWarning: unable to determine OSD types. "
            msg += "Unable to recommend optimal ratio so using default."
            warning = True
        else:
            cpus = 1  # default
            msg += "vCPU to OSD ratio: %i" % cpus
            msg += "\nWarning: Requested OSDs are of mixed type. "
            msg += "Unable to recommend optimal ratio so using default."
            warning = True

    return cpus, msg_pre + msg, warning


def main():
    """Main method of Ansible module
    """
    result = dict(
        changed=False,
        message=''
    )
    module_args = dict(
        tripleo_environment_parameters=dict(type=dict, required=True),
        tripleo_role_name=dict(type=str, required=True),
        introspection_data=dict(type=dict, required=True),
        average_guest_cpu_utilization_percentage=dict(type=int, required=False, default=0),
        average_guest_memory_size_in_mb=dict(type=int, required=False, default=0),
        derived_parameters=dict(type=dict, required=False),
        new_heat_environment_path=dict(type=str, required=False),
        report_path=dict(type=str, required=False),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
    if module.params['derived_parameters'] is None:
        module.params['derived_parameters'] = {}

    vcpus = count_vcpus(module)
    num_osds = count_osds(module.params['tripleo_environment_parameters'])
    mem_gb = count_memory(module.params['introspection_data'])

    mem_gb_per_osd = 5
    vcpu_ratio, vcpu_ratio_msg, vcpu_warn = get_vcpus_per_osd(
        module.params['introspection_data'],
        module.params['tripleo_environment_parameters'],
        num_osds)

    # Derive HCI parameters
    derivation = derive(mem_gb, vcpus, num_osds,
                        module.params['average_guest_memory_size_in_mb'],
                        module.params['average_guest_cpu_utilization_percentage'],
                        mem_gb_per_osd, vcpu_ratio)

    # directly set failed status and message
    result['failed'] = derivation['failed']
    result['message'] = derivation['message']
    if vcpu_warn:
        result['message'] += "\n" + "Warning: " + vcpu_ratio_msg + "\n"
    else:
        result['message'] += "\n" + vcpu_ratio_msg + "\n"

    # make a copy of the existing derived_parameters (e.g. perhaps from NFV)
    existing_params = module.params['derived_parameters']
    # add HCI derived paramters for Nova scheduler
    if not derivation['failed']:
        role_derivation = {}
        role_derivation['NovaReservedHostMemory'] = derivation['nova_reserved_mem_mb']
        if 'cpu_allocation_ratio' in derivation:
            role_derivation['NovaCPUAllocationRatio'] = derivation['cpu_allocation_ratio']
        role_name_parameters = module.params['tripleo_role_name'] + 'Parameters'
        existing_params[role_name_parameters] = role_derivation
        # write out to file if requested
        if module.params['new_heat_environment_path'] and not module.check_mode:
            output = {}
            output['parameter_defaults'] = existing_params
            with open(module.params['new_heat_environment_path'], 'w') as outfile:
                yaml.safe_dump(output, outfile, default_flow_style=False)
            # because we wrote a file we're making a change on the target system
            result['changed'] = True
        if module.params['report_path'] and not module.check_mode:
            with open(module.params['report_path'], 'w') as outfile:
                outfile.write(result['message'])
            # because we wrote a file we're making a change on the target system
            result['changed'] = True

    # return existing derived parameters with the new HCI parameters too
    result['derived_parameters'] = existing_params

    # Exit and pass the key/value results
    module.exit_json(**result)


if __name__ == '__main__':
    main()
