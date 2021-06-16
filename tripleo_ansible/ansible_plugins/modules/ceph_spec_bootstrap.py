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
"""Create Ceph Orchestrator specification file based on TripleO parameters"""

import os
import re
import yaml

from ansible.module_utils.basic import AnsibleModule
try:
    from ansible.module_utils import ceph_spec
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import ceph_spec


ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: ceph_spec_bootstrap module
short_description: Create Ceph Orchestrator specification file based on TripleO parameters
description:
    - "The ceph_spec_bootstrap module uses information from both the composed services in TripleO roles and the deployed hosts file ('openstack overcloud node provision' output), or just the inventory file (tripleo-ansible-inventory output) to determine what Ceph services should run on what hosts and generate a valid Ceph spec. This allows the desired end state defined in TripleO to be translated into an end state defined in Ceph orchestrator. The intention is to use this module when bootstraping a new Ceph cluster."
options:
    deployed_metalsmith:
        description: The absolute path to a file like deployed_metal.yaml, as genereated by 'openstack overcloud node provision --output deployed_metal.yaml'. This file is used to map which ceph_service_types map to which deployed hosts. Use this option if you have deployed servers with metalsmith but do not yet have an inventory genereated from the overcloud in Heat. Either tripleo_ansible_inventory xor deployed_metalsmith must be used (not both).
        required: False
        type: str
    tripleo_ansible_inventory:
        description: The absolute path to an Ansible inventory genereated by running the tripleo-ansible-inventory command. This file is used to map which ceph_service_types map to which deployed hosts. Use this option if you already have an inventory genereated from the overcloud in Heat. Either tripleo_ansible_inventory xor deployed_metalsmith must be used (not both).
        required: False
        type: str
    new_ceph_spec:
        description: The absolute path to a new file which will be created by the module and contain the resultant Ceph specification. If not provided, defaults to /home/stack/ceph_spec.yaml.
        required: False
        type: str
    ceph_service_types:
        description: List of Ceph services being deployed on overcloud. All service names must be a valid service_type as described in the Ceph Orchestrator CLI service spec documentation. If not provided, defaults to ['mon', 'mgr', 'osd'], which are presently the only supported service types this module supports.
        required: False
        type: list
    tripleo_roles:
        description: The absolute path to the TripleO roles file. Only necessary if deployed_metalsmith is used. If not provided then defaults to /usr/share/openstack-tripleo-heat-templates/roles_data.yaml. This file is used to map which ceph_service_types map to which roles. E.g. all roles with OS::TripleO::Services::CephOSD will get the Ceph service_type 'osd'. This paramter is ignored if tripleo_ansible_inventory is used.
        required: False
        type: str
    osd_spec:
        description: A valid osd service specification. If not passed defaults to using all available data devices (data_devices all true).
        required: False
        type: dict
    fqdn:
        description: When true, the "hostname" and "hosts" in the generated Ceph spec will have their fully qualified domain name. This paramter defaults to false and only has an effect when tripleo_ansible_inventory is used.
        required: False
        type: bool
author:
    - John Fulton (fultonj)
'''

EXAMPLES = '''
- name: make spec from 'openstack overcloud node provision' output
  ceph_spec_bootstrap:
    new_ceph_spec: "{{ playbook_dir }}/ceph_spec.yaml"
    deployed_metalsmith: ~/overcloud-baremetal-deployed.yaml

- name: make spec from tripleo-ansible-inventory output
  ceph_spec_bootstrap:
    new_ceph_spec: "{{ playbook_dir }}/ceph_spec.yaml"
    tripleo_ansible_inventory: ~/config-download/overcloud/tripleo-ansible-inventory.yaml

- name: make spec from inventory with FQDNs and custom osd_spec
  ceph_spec_bootstrap:
    new_ceph_spec: "{{ playbook_dir }}/ceph_spec.yaml"
    tripleo_ansible_inventory: ~/config-download/overcloud/tripleo-ansible-inventory.yaml
    fqdn: true
    osd_spec:
      data_devices:
        paths:
          - /dev/ceph_vg/ceph_lv_data

- name: make spec with only Ceph mons and managers
  ceph_spec_bootstrap:
    new_ceph_spec: "{{ playbook_dir }}/ceph_spec.yaml"
    deployed_metalsmith: ~/overcloud-baremetal-deployed.yaml
    ceph_service_types:
      - mon
      - mgr

- name: make spec with composed roles/ HDDs for data/ SSDs for db
  ceph_spec_bootstrap:
    new_ceph_spec: "{{ playbook_dir }}/ceph_spec.yaml"
    deployed_metalsmith: ~/overcloud-baremetal-deployed.yaml
    tripleo_roles: ~/templates/custom_roles_data.yaml
    osd_spec:
      data_devices:
        rotational: 1
      db_devices:
        rotational: 0
'''

RETURN = '''
'''

# Map tripleo services to ceph spec service_types
SERVICE_MAP = {
    'CephMon': ['mon'],
    'CephMgr': ['mgr'],
    'CephOSD': ['osd']
}

# Support for the following are not yet available
#   'CephMds': ['mds'],
#   'CephRbdMirror': ['rbd-mirror'],
#   'CephRgw': ['rgw'],
#   'CephGrafana': ['alertmanager', 'grafana', 'node-exporter'],


def get_inventory_hosts_to_ips(inventory, roles, fqdn=False):
    """Return a map of hostnames to IP addresses, e.g.
         {'oc0-ceph-0': '192.168.24.13',
          'oc0-compute-0': '192.168.24.21',
          'oc0-controller-0': '192.168.24.23',
          'oc0-controller-1': '192.168.24.15',
          'oc0-controller-2': '192.168.24.7'}
    Uses ansible inventory as source
    """
    hosts_to_ips = {}
    for key in inventory:
        if key in roles:
            for host in inventory[key]['hosts']:
                ip = inventory[key]['hosts'][host]['ansible_host']
                if fqdn:
                    hostname = inventory[key]['hosts'][host]['canonical_hostname']
                else:
                    hostname = host
                hosts_to_ips[hostname] = ip
    return hosts_to_ips


def get_deployed_hosts_to_ips(metalsmith_data_file):
    """Return a map of hostnames to IP addresses, e.g.
         {'oc0-ceph-0': '192.168.24.13',
          'oc0-compute-0': '192.168.24.21',
          'oc0-controller-0': '192.168.24.23',
          'oc0-controller-1': '192.168.24.15',
          'oc0-controller-2': '192.168.24.7'}
    Uses output of metalsmith deployed hosts file as source
    """
    hosts_to_ips = {}
    with open(metalsmith_data_file, 'r') as stream:
        try:
            metal = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
        try:
            port_map = metal['parameter_defaults']['DeployedServerPortMap']
            for host, host_map in port_map.items():
                try:
                    ip = host_map['fixed_ips'][0]['ip_address']
                except Exception:
                    raise RuntimeError(
                        'The DeployedServerPortMap is missing the first '
                        'fixed_ip in the data file: {metalsmith_data_file}'.format(
                            metalsmith_data_file=metalsmith_data_file))
                hosts_to_ips[host.replace('-ctlplane', '')] = ip
        except Exception:
            raise RuntimeError(
                'The DeployedServerPortMap is not defined in '
                'data file: {metalsmith_data_file}'.format(
                metalsmith_data_file=metalsmith_data_file))
    return hosts_to_ips


def get_inventory_roles_to_hosts(inventory, roles, fqdn=False):
    """Return a map of roles to host lists, e.g.
         roles_to_hosts['CephStorage'] = ['oc0-ceph-0', 'oc0-ceph-1']
         roles_to_hosts['Controller'] = ['oc0-controller-0']
         roles_to_hosts['Compute'] = ['oc0-compute-0']
    Uses ansible inventory as source
    """
    roles_to_hosts = {}
    for key in inventory:
        if key in roles:
            roles_to_hosts[key] = []
            for host in inventory[key]['hosts']:
                if fqdn:
                    hostname = inventory[key]['hosts'][host]['canonical_hostname']
                else:
                    hostname = host
                roles_to_hosts[key].append(hostname)
    return roles_to_hosts


def get_deployed_roles_to_hosts(metalsmith_data_file, roles):
    """Return a map of roles to host lists, e.g.
         roles_to_hosts['CephStorage'] = ['oc0-ceph-0', 'oc0-ceph-1']
         roles_to_hosts['Controller'] = ['oc0-controller-0']
         roles_to_hosts['Compute'] = ['oc0-compute-0']
    Uses output of metalsmith deployed hosts file as source
    """
    roles_to_hosts = {}
    with open(metalsmith_data_file, 'r') as stream:
        try:
            metal = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
        try:
            name_map = metal['parameter_defaults']['HostnameMap']
            for role in roles:
                for item in metal['parameter_defaults']:
                    if item == role + 'HostnameFormat':
                        host_fmt = metal['parameter_defaults'][item]
                        pat = host_fmt.replace('%stackname%', '.*').replace('-%index%', '')
                        reg = re.compile(pat)
                        matching_hosts = []
                        for host in name_map:
                            if reg.match(host):
                                matching_hosts.append(name_map[host])
                roles_to_hosts[role] = matching_hosts
        except Exception:
            raise RuntimeError(
                'The expected HostnameMap and RoleHostnameFormat are '
                'not defined in data file: {metalsmith_data_file}'.format(
                metalsmith_data_file=metalsmith_data_file))
    return roles_to_hosts


def get_roles_to_svcs_from_inventory(inventory):
    """Return a map of map of TripleO Roles to TripleO Ceph Services, e.g.
         {'CephStorage': ['CephOSD'],
          'Controller': ['CephMgr', 'CephMon']}
       Uses inventory file as source
    """
    # This approach is backwards but lets the larger program stay consistent
    # and not require the roles file when the inventory is provided. The method
    # of inventory is only used to deploy ceph during overcloud (not before).
    roles_to_services = {}
    inverse_service_map = {}
    ceph_services = []
    for tripleo_name, ceph_list in SERVICE_MAP.items():
        for ceph_name in ceph_list:
            ceph_services.append(ceph_name)
            inverse_service_map[ceph_name] = tripleo_name
    for key in inventory:
        key_rename = key.replace('ceph_', '')
        if key_rename in ceph_services:
            for role in inventory[key]['children'].keys():
                if role in roles_to_services.keys():
                    roles_to_services[role].append(inverse_service_map[key_rename])
                else:
                    roles_to_services[role] = [inverse_service_map[key_rename]]
    return roles_to_services


def get_roles_to_svcs_from_roles(roles_file):
    """Return a map of map of TripleO Roles to TripleO Ceph Services, e.g.
         {'Compute': [],
          'CephStorage': ['CephOSD'],
          'Controller': ['CephMgr', 'CephMon']}
       Uses roles file as source
    """
    roles_to_services = {}
    with open(roles_file, 'r') as stream:
        try:
            roles = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
        try:
            for role in roles:
                svcs = []
                for svc in role['ServicesDefault']:
                    svc_short = svc.replace('OS::TripleO::Services::', '')
                    if svc_short in SERVICE_MAP.keys():
                        svcs.append(svc_short)
                    roles_to_services[role['name']] = svcs
        except Exception:
            raise RuntimeError(
                'Unable to extract the name or ServicesDefault list from '
                'data file: {roles_file}'.format(roles_file=roles_file))
    return roles_to_services


def get_label_map(hosts_to_ips, roles_to_svcs, roles_to_hosts, ceph_service_types):
    """Return a map of hostname to list of ceph service to run on that host, e.g.
         label_map['oc0-ceph-0'] = ['osd']
         label_map['oc0-controller-0'] = ['mon', 'mgr', '_admin']
    """
    label_map = {}
    for host in hosts_to_ips:
        label_map[host] = []
        for role, host_list in roles_to_hosts.items():
            if host in host_list:
                for tripleo_svc in roles_to_svcs[role]:
                    for potential_ceph_svc in SERVICE_MAP[tripleo_svc]:
                        if potential_ceph_svc in ceph_service_types:
                            label_map[host].append(potential_ceph_svc)
                        if potential_ceph_svc == 'mon':
                            label_map[host].append('_admin')
    return label_map


def get_specs(hosts_to_ips, label_map, ceph_service_types, osd_spec={}):
    """Build specs from hosts map, label_map, and ceph_service_types list
       Create a ceph_spec object for each host or service
       Returns a list of dictionaries.
    """
    specs = []
    # Create host entries
    for host, ip in hosts_to_ips.items():
        if len(label_map[host]) > 0:
            spec = ceph_spec.CephHostSpec('host', ip, host, label_map[host])
            specs.append(spec.make_daemon_spec())

    # Create service entries for supported services in SERVICE_MAP
    labels = []
    placement_pattern = ''
    spec_dict = {}
    for svc in ceph_service_types:
        host_list = []
        for host, label_list in label_map.items():
            if svc in label_list:
                host_list.append(host)
        if svc in ['mon', 'mgr']:
            d = ceph_spec.CephDaemonSpec(svc, svc, svc, host_list,
                                         placement_pattern, None,
                                         spec_dict, labels)
        if svc in ['osd']:
            if osd_spec == {}:
                # default to all devices
                osd_spec = {
                    'data_devices': {
                        'all': True
                    }
                }
            d = ceph_spec.CephDaemonSpec(svc, 'default_drive_group',
                                         'osd.default_drive_group',
                                         host_list, placement_pattern,
                                         None, spec_dict, labels, **osd_spec)
        specs.append(d.make_daemon_spec())
    return specs


def render(specs, output):
    """Write a multiline yaml file from a list of dicts
    """
    open(output, 'w').close()  # reset file
    for spec in specs:
        with open(output, 'a') as f:
            f.write('---\n')
            f.write(yaml.dump(spec))


def flatten(t):
    """Merge a list of lists into a single list
    """
    return [item for sublist in t for item in sublist]


def main():
    """Main method of Ansible module
    """
    result = dict(
        changed=False,
        msg='',
        specs=[]
    )
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
    )
    # Set payload defaults
    result['failed'] = False
    specs = []
    errors = []

    # Collect inputs
    deployed_metalsmith = module.params.get('deployed_metalsmith')
    tripleo_ansible_inventory = module.params.get('tripleo_ansible_inventory')
    new_ceph_spec = module.params.get('new_ceph_spec')
    ceph_service_types = module.params.get('ceph_service_types')
    tripleo_roles = module.params.get('tripleo_roles')
    osd_spec = module.params.get('osd_spec')
    fqdn = module.params.get('fqdn')

    # Set defaults
    if ceph_service_types is None:
        ceph_service_types = ['mon', 'mgr', 'osd']
    if new_ceph_spec is None:
        new_ceph_spec = "/home/stack/ceph_spec.yaml"
    if tripleo_roles is None:
        tripleo_roles = "/usr/share/openstack-tripleo-heat-templates/roles_data.yaml"
    if osd_spec is None:
        osd_spec = {}
    if fqdn is None:
        fqdn = False

    # Validate inputs
    # 0. Are they using metalsmith xor an inventory as their method?
    method = ""
    required_files = []
    if deployed_metalsmith is None and tripleo_ansible_inventory is not None:
        method = 'inventory'
        required_files.append(tripleo_ansible_inventory)
    elif deployed_metalsmith is not None and tripleo_ansible_inventory is None:
        method = 'metal'
        required_files.append(deployed_metalsmith)
        required_files.append(tripleo_roles)
    else:
        error = "You must provide either the "
        error += "tripleo_ansible_inventory or deployed_metalsmith "
        error += "parameter (but not both)."
        errors.append(error)
        result['failed'] = True
    # 1. The required files must all be an existing path to a file
    for fpath in required_files:
        if not os.path.isfile(fpath):
            error = str(fpath) + " is not a valid file."
            errors.append(error)
            result['failed'] = True
    # 2. The directory for the spec file must be an existing path
    fpath = os.path.dirname(new_ceph_spec)
    if not os.path.isdir(fpath):
        error = str(fpath) + " is not a valid directory."
        errors.append(error)
        result['failed'] = True
    # 3. argument_spec already ensures osd_spec is a dictionary
    # 4. Must be one of the ceph_spec.ALLOWED_DAEMONS used in the SERVICE_MAP
    supported_services = flatten(SERVICE_MAP.values())
    for service_type in ceph_service_types:
        if service_type not in supported_services:
            error = "'" + str(service_type) + "' must be one of "
            error += str(supported_services)
            errors.append(error)
            result['failed'] = True
    # 5. fqdn is only supported for the inventory method
    if method != 'inventory' and fqdn:
        error = "The fqdn option may only be true when using tripleo_ansible_inventory"
        errors.append(error)
        result['failed'] = True

    if not result['failed']:
        # Build data structures to map roles/services/hosts/labels
        if method == 'metal':
            roles_to_svcs = get_roles_to_svcs_from_roles(tripleo_roles)
            roles_to_hosts = get_deployed_roles_to_hosts(deployed_metalsmith,
                                                         roles_to_svcs.keys())
            hosts_to_ips = get_deployed_hosts_to_ips(deployed_metalsmith)
        elif method == 'inventory':
            with open(tripleo_ansible_inventory, 'r') as stream:
                inventory = yaml.safe_load(stream)
            roles_to_svcs = get_roles_to_svcs_from_inventory(inventory)
            roles_to_hosts = get_inventory_roles_to_hosts(inventory,
                                                          roles_to_svcs.keys(),
                                                          fqdn)
            hosts_to_ips = get_inventory_hosts_to_ips(inventory,
                                                      roles_to_svcs.keys(),
                                                      fqdn)
        # regardless of how we built our maps, assign the correct labels
        label_map = get_label_map(hosts_to_ips, roles_to_svcs,
                                  roles_to_hosts, ceph_service_types)
        # Build specs as list of ceph_spec objects from data structures
        specs = get_specs(hosts_to_ips, label_map, ceph_service_types, osd_spec)
        # Render specs list to file
        render(specs, new_ceph_spec)

    # Set payloads
    result['msg'] = "  ".join(errors)
    result['specs'] = specs

    # exit and pass the key/value results
    module.exit_json(**result)


if __name__ == '__main__':
    main()
