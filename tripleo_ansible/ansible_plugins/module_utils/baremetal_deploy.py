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

import collections
from copy import deepcopy as dcopy
import os

import jsonschema

import metalsmith
from metalsmith import sources


_IMAGE_SCHEMA = {
    'type': 'object',
    'properties': {
        'href': {'type': 'string'},
        'checksum': {'type': 'string'},
        'kernel': {'type': 'string'},
        'ramdisk': {'type': 'string'},
    },
    'required': ['href'],
    'additionalProperties': False,
}

_NIC_SCHEMA = {
    'type': 'object',
    'properties': {
        'network': {'type': 'string'},
        'port': {'type': 'string'},
        'fixed_ip': {'type': 'string'},
        'subnet': {'type': 'string'},
    },
    'additionalProperties': False
}

_NETWORK_CONFIG_SCHEMA = {
    'type': 'object',
    'properties': {
        'template': {'type': 'string'},
        'physical_bridge_name': {'type': 'string'},
        'public_interface_name': {'type': 'string'},
        'network_config_update': {'type': 'boolean'},
        'net_config_data_lookup': {'type': 'object'},
        'default_route_network': {
            'type': 'array',
            'items': {'type': 'string'},
        },
        'networks_skip_config': {
            'type': 'array',
            'items': {'type': 'string'}
        },
        'dns_search_domains': {'type': 'string'},
        'bond_interface_ovs_options': {'type': 'string'},
        'num_dpdk_interface_rx_queues': {'type': 'integer'}
    },
    'additionalProperties': False
}

_NETWORK_SCHEMA = {
    'type': 'object',
    'properties': {
        'network': {'type': 'string'},
        'port': {'type': 'string'},
        'fixed_ip': {'type': 'string'},
        'subnet': {'type': 'string'},
        'vif': {'type': 'boolean'}
    },
    'additionalProperties': False
}

_CONFIG_DRIVE_SCHEMA = {
    'type': 'object',
    'properties': {
        'cloud_config': {'type': 'object'},
        'meta_data': {'type': 'object'},
    },
    'additionalProperties': False
}

_INSTANCE_SCHEMA = {
    'type': 'object',
    'properties': {
        'capabilities': {'type': 'object'},
        'conductor_group': {'type': 'string'},
        'config_drive': _CONFIG_DRIVE_SCHEMA,
        'hostname': {
            'type': 'string',
            'minLength': 2,
            'maxLength': 255
        },
        'image': _IMAGE_SCHEMA,
        'name': {'type': 'string'},
        'netboot': {'type': 'boolean'},
        'nics': {'type': 'array',
                 'items': _NIC_SCHEMA},
        'network_config': _NETWORK_CONFIG_SCHEMA,
        'networks': {'type': 'array',
                     'items': _NETWORK_SCHEMA},
        'passwordless_sudo': {'type': 'boolean'},
        'profile': {'type': 'string'},
        'provisioned': {'type': 'boolean'},
        'resource_class': {'type': 'string'},
        'root_size_gb': {'type': 'integer', 'minimum': 4},
        'ssh_public_keys': {'type': 'string'},
        'swap_size_mb': {'type': 'integer', 'minimum': 64},
        'traits': {
            'type': 'array',
            'items': {'type': 'string'}
        },
        'user_name': {'type': 'string'},
        'managed': {'type': 'boolean'},
        'management_ip': {'type': 'string'},
    },
    'additionalProperties': False,
}


_INSTANCES_SCHEMA = {
    'type': 'array',
    'items': _INSTANCE_SCHEMA
}
"""JSON schema of the instances list."""

_no_nics = dcopy(_INSTANCE_SCHEMA)
_no_networks = dcopy(_INSTANCE_SCHEMA)
del _no_nics['properties']['nics']
del _no_networks['properties']['networks']

_ROLE_DEFAULTS_SCHEMA = {
    'anyOf': [_no_nics, _no_networks]
}
"""JSON schema of the role defaults."""

_INSTANCES_INPUT_SCHEMA = {
    'type': 'array',
    'items': {'anyOf': [_no_nics, _no_networks]},
}
"""JSON schema of the instances input."""

_ROLE_ANSIBLE_PLAYBOOKS_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'playbook': {'type': 'string'},
            'extra_vars': {'type': 'object'}
        },
        'additionalProperties': False,
        'required': ['playbook'],
    }
}
"""JSON schema of the role ansible_playbooks input."""

_ROLES_INPUT_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'hostname_format': {'type': 'string'},
            'count': {'type': 'integer', 'minimum': 0},
            'defaults': _ROLE_DEFAULTS_SCHEMA,
            'instances': _INSTANCES_INPUT_SCHEMA,
            'ansible_playbooks': _ROLE_ANSIBLE_PLAYBOOKS_SCHEMA,
        },
        'additionalProperties': False,
        'required': ['name'],
    }
}
"""JSON schema of the roles list."""


class BaremetalDeployException(Exception):
    pass


def expand(roles, stack_name, expand_provisioned=True, default_image=None,
           default_network=None, user_name=None, ssh_public_keys=None,
           default_network_config=None):

    def _remove_vif_key(nets):
        for net in nets:
            net.pop('vif', None)

    for role in roles:
        defaults = role.setdefault('defaults', {})
        if default_image:
            defaults.setdefault('image', default_image)
        if ssh_public_keys:
            defaults.setdefault('ssh_public_keys', ssh_public_keys)
        if user_name:
            defaults.setdefault('user_name', user_name)
        if default_network:
            default_networks = defaults.setdefault('networks', [])
            default_networks.extend([x for x in default_network
                                     if x not in default_networks])
        if default_network_config:
            default_network_config = defaults.setdefault('network_config', {})

        if 'profile' in defaults:
            capabilities = defaults.setdefault('capabilities', {})
            capabilities.setdefault('profile', defaults['profile'])
            del defaults['profile']

        # Set config-drive metadata instance-name to the role name
        config_drive = defaults.setdefault('config_drive', {})
        meta_data = config_drive.setdefault('meta_data', {})
        meta_data['instance-type'] = role['name']

        for inst in role.get('instances', []):
            merge_config_drive_defaults(defaults, inst)
            merge_networks_defaults(defaults, inst)
            merge_network_config_defaults(defaults, inst)

            for k, v in defaults.items():
                if k != 'config_drive':
                    # Need to use deepcopy here so defaults are not accidentally
                    # changed by per-instance manipulations
                    inst.setdefault(k, dcopy(v))

            # Set the default hostname now for duplicate hostname
            # detection during validation
            if 'hostname' not in inst and 'name' in inst:
                inst['hostname'] = inst['name']

    validate_roles(roles)

    instances = []
    hostname_map = {}
    parameter_defaults = {'HostnameMap': hostname_map}
    role_net_map = {}
    hostname_role_map = {}
    for role in roles:
        name = role['name']
        role_net_map.setdefault(name, set())
        hostname_format = build_hostname_format(
            role.get('hostname_format'), name)
        count = role.get('count', 1)
        unprovisioned_indexes = []

        # build a map of all potential generated names
        # with the index number which generates the name
        potential_gen_names = {}
        for index in range(count + len(role.get('instances', []))):
            potential_gen_names[build_hostname(
                hostname_format, index, stack_name)] = index

        # build a list of instances from the specified
        # instances list
        role_instances = []
        for instance in role.get('instances', []):
            inst = {}
            inst.update(instance)

            # create a hostname map entry now if the specified hostname
            # is a valid generated name
            if inst.get('hostname') in potential_gen_names:
                hostname_map[inst['hostname']] = inst['hostname']

            role_instances.append(inst)

        # add generated instance entries until the desired count of
        # provisioned instances is reached
        while len([i for i in role_instances
                   if i.get('provisioned', True)]) < count:
            inst = {}
            inst.update(role['defaults'])
            role_instances.append(inst)

        # NOTE(dtantsur): our hostname format may differ from THT defaults,
        # so override it in the resulting environment
        parameter_defaults['%sHostnameFormat' % name] = (
            hostname_format)

        # ensure each instance has a unique non-empty hostname
        # and a hostname map entry and add nics entry for vif networks.
        # Also build a list of indexes for unprovisioned instances
        index = 0
        for inst in role_instances:
            provisioned = inst.get('provisioned', True)
            gen_name = None
            hostname = inst.get('hostname')

            if hostname not in hostname_map:
                while (not gen_name
                        or gen_name in hostname_map):
                    gen_name = build_hostname(
                        hostname_format, index, stack_name)
                    index += 1
                inst.setdefault('hostname', gen_name)
                hostname = inst.get('hostname')
                hostname_map[gen_name] = inst['hostname']

            if not provisioned:
                if gen_name:
                    unprovisioned_indexes.append(
                        potential_gen_names[gen_name])
                elif hostname in potential_gen_names:
                    unprovisioned_indexes.append(
                        potential_gen_names[hostname])

            vif_networks = [x for x in dcopy(inst.get('networks', []))
                            if x.get('vif')]
            if vif_networks:
                _remove_vif_key(vif_networks)
                inst.setdefault('nics', vif_networks)

            if 'profile' in inst:
                capabilities = inst.setdefault('capabilities', {})
                capabilities['profile'] = inst['profile']
                del inst['profile']

        if unprovisioned_indexes:
            parameter_defaults['%sRemovalPolicies' % name] = [{
                'resource_list': unprovisioned_indexes
            }]

        provisioned_count = 0
        for inst in role_instances:
            provisioned = inst.pop('provisioned', True)

            if provisioned:
                provisioned_count += 1

            # Only add instances which match the desired provisioned state
            if provisioned == expand_provisioned:
                instances.append(inst)

                role_net_map[name].update(
                    [x['network'] for x in inst.get('networks', [])])
                hostname_role_map[inst['hostname']] = name

        parameter_defaults['%sCount' % name] = (
            provisioned_count)

    validate_instances(instances, _INSTANCES_SCHEMA)
    if expand_provisioned:
        env = {'parameter_defaults': parameter_defaults}
    else:
        env = {}
    return instances, env, role_net_map, hostname_role_map


def merge_network_config_defaults(defaults, instance):
    d_network_config = defaults.get('network_config', {})
    i_network_config = instance.get('network_config', {})
    if not d_network_config:
        return

    # only merge network_config not already defined on the instance
    for k, v in d_network_config.items():
        i_network_config.setdefault(k, v)


def merge_networks_defaults(defaults, instance):
    d_networks = defaults.get('networks', [])
    i_networks = instance.get('networks', [])
    if not d_networks:
        return

    i_dict = {x['network']: x for x in i_networks}
    d_dict = {x['network']: x for x in d_networks}

    # only merge networks not already defined on the instance
    for key in d_dict:
        if key not in i_dict:
            i_networks.append(d_dict[key])

    # only set non-empty networks value on the instance
    if i_networks:
        instance['networks'] = i_networks


def merge_config_drive_defaults(defaults, instance):
    d_config_drive = defaults.get('config_drive', {})
    i_config_drive = instance.get('config_drive', {})

    def merge(key):
        d_dict = d_config_drive.get(key, {})
        i_dict = i_config_drive.get(key, {})

        # start with a shallow copy of the defaults and update
        # with the instance value
        f_dict = dict(d_dict)
        f_dict.update(i_dict)

        # only set non-empty merge results
        if f_dict:
            i_config_drive[key] = f_dict

    merge('cloud_config')
    merge('meta_data')

    # only set non-empty config_drive value on the instance
    if i_config_drive:
        instance['config_drive'] = i_config_drive


def check_existing(instances, provisioner, baremetal):
    validate_instances(instances, _INSTANCES_SCHEMA)

    # Due to the name shadowing we should import other way
    import importlib
    sdk = importlib.import_module('openstack')

    not_found = []
    found = []
    unmanaged = []
    existing_by_hostname = collections.defaultdict(list)
    existing_by_name = collections.defaultdict(list)
    if baremetal:
        for node in baremetal.nodes(associated=True, fields=['uuid', 'name', 'instance_info']):
            existing_by_name[node.name].append(node.id)
            display_name = node.instance_info.get('display_name')
            if display_name:
                existing_by_hostname[display_name].append(node.id)

    for request in instances:

        hostname = request['hostname']
        name = request.get('name')
        hostname_matches = len(existing_by_hostname[hostname])
        name_matches = name and len(existing_by_name[name]) or 0
        if hostname_matches == 0:
            if name_matches == 0:
                # try the hostname, there may be an allocation with that name
                ident = hostname
            elif name_matches == 1:
                ident = name
            else:
                message = ('There is more than one existing node with name=%s. '
                           'Replace this name with a specific node uuid to match the desired instance.'
                           % hostname)
                raise BaremetalDeployException(message)
        elif hostname_matches == 1:
            ident = existing_by_hostname[hostname][0]
        else:
            message = ('There is more than one existing instance with instance_info.display_name=%s. '
                       'Replace this hostname with a specific node uuid to match the desired instance.'
                       % hostname)
            raise BaremetalDeployException(message)

        if not request.get('managed', True):
            unmanaged.append(request)
            continue
        elif not baremetal:
            message = ('Instance %s is not specified as pre-provisioned '
                       '(managed: False), and no connection to '
                       'the baremetal service was provided.'
                       % ident)
            raise BaremetalDeployException(message)

        try:
            instance = provisioner.show_instance(ident)
        # TODO(dtantsur): replace Error with a specific exception
        except (sdk.exceptions.ResourceNotFound,
                metalsmith.exceptions.Error):
            not_found.append(request)
        except Exception as exc:
            message = ('Failed to request instance information for %s'
                       % ident)
            raise BaremetalDeployException(
                "%s. %s: %s" % (message, type(exc).__name__, exc))
        else:
            if (not instance.allocation
                    and instance.state == metalsmith.InstanceState.ACTIVE
                    and 'name' in request):
                try:
                    baremetal.get_allocation(request['hostname'])
                    raise BaremetalDeployException(
                        'An allocation with the requested hostname %s '
                        'already exists. Refusing to proceed to avoid '
                        'confusing results. Please either change the node '
                        'name or use a different hostname'
                        % request['hostname'])
                except sdk.exceptions.ResourceNotFound:
                    pass

                # Existing node is missing an allocation record,
                # so create one without triggering allocation
                baremetal.create_allocation(
                    resource_class=request.get('resource_class', 'baremetal'),
                    name=request['hostname'],
                    node=request['name']
                )

                # Refresh the instance after adding the allocation
                # See: https://bugs.launchpad.net/tripleo/+bug/1929555
                instance = provisioner.show_instance(instance.uuid)

            # NOTE(dtantsur): metalsmith can match instances by node names,
            # provide a safeguard to avoid conflicts
            if (instance.hostname
                    and instance.hostname != request['hostname']):
                try:
                    allocation = baremetal.get_allocation(request['hostname'])
                    node = baremetal.get_node(allocation.node_id)
                    if (node.instance_info.get('display_name')
                            != request['hostname']):
                        error = ("Requested hostname %s was not found, but "
                                 "the deployed node %s has a matching name. "
                                 "Refusing to proceed to avoid confusing "
                                 "results. Please either rename the node or "
                                 "use a different hostname") % (
                                     request['hostname'], instance.uuid)
                        raise BaremetalDeployException(error)
                except sdk.exceptions.ResourceNotFound:
                    continue
            found.append(instance)

    return found, not_found, unmanaged


def populate_environment(instance_uuids, provisioner, environment,
                         ctlplane_network, templates):

    resource_registry = environment.setdefault(
        'resource_registry', {})
    resource_registry.setdefault(
        'OS::TripleO::DeployedServer::ControlPlanePort',
        os.path.join(templates, 'deployed-server/deployed-neutron-port.yaml'))
    port_map = (environment.setdefault('parameter_defaults', {})
                .setdefault('DeployedServerPortMap', {}))
    for uuid in instance_uuids:
        instance = provisioner.show_instance(uuid)
        nets = nics_to_port_map(instance.nics(), provisioner.connection)
        ctlplane_net = nets.get(ctlplane_network)
        if not ctlplane_net:
            continue
        ctlplane = {}
        ctlplane['fixed_ips'] = ctlplane_net.get('fixed_ips', [])

        port_map['%s-%s' % (instance.hostname.lower(),
                            ctlplane_network)] = ctlplane
    return environment


def build_hostname_format(hostname_format, role_name):
    if not hostname_format:
        hostname_format = '%stackname%-{}-%index%'.format(
            'novacompute' if role_name == 'Compute' else role_name.lower())
    return hostname_format


def build_hostname(hostname_format, index, stack):
    gen_name = hostname_format.replace('%index%', str(index))
    gen_name = gen_name.replace('%stackname%', stack)
    return gen_name


def validate_instances(instances, schema):
    jsonschema.validate(instances, schema)
    hostnames = set()
    names = set()
    fixed_ips = set()
    for inst in instances:
        name = inst.get('hostname', inst.get('name'))
        # NOTE(dtantsur): validate image parameters
        get_source(inst)

        if inst.get('hostname'):
            if inst['hostname'] in hostnames:
                raise ValueError('Hostname %s is used more than once' %
                                 inst['hostname'])
            hostnames.add(inst['hostname'])

        if inst.get('name'):
            if inst['name'] in names:
                raise ValueError('Node %s is requested more than once' %
                                 inst['name'])
            names.add(inst['name'])

        inst_ips = {net['fixed_ip'] for net in inst.get('networks', [])
                    if net.get('fixed_ip')}
        if inst_ips.intersection(fixed_ips):
            raise ValueError(
                'One or more IP address {ips} for Node {name} is requested '
                'more than once'.format(
                    ips=', '.join(inst_ips.intersection(fixed_ips)),
                    name=name))
            fixed_ips.update(inst_ips)

        if not inst.get('managed', True):
            if not inst_ips and not inst.get('management_ip'):
                raise ValueError('Node %s that is managed: false requires '
                                 'either a fixed IP address, or a management '
                                 'ip address' % name)


def validate_roles(roles):
    jsonschema.validate(roles, _ROLES_INPUT_SCHEMA)

    for item in roles:
        count = item.get('count', 1)
        instances = item.get('instances', [])
        instances = [i for i in instances if i.get('provisioned', True)]
        name = item.get('name')
        if len(instances) > count:
            raise ValueError(
                "%s: number of instance entries %s "
                "cannot be greater than count %s" %
                (name, len(instances), count)
            )

        defaults = item.get('defaults', {})
        if 'hostname' in defaults:
            raise ValueError("%s: cannot specify hostname in defaults"
                             % name)
        if 'name' in defaults:
            raise ValueError("%s: cannot specify name in defaults"
                             % name)
        if 'provisioned' in defaults:
            raise ValueError("%s: cannot specify provisioned in defaults"
                             % name)
        if 'instances' in item:
            validate_instances(item['instances'], _INSTANCES_INPUT_SCHEMA)


def get_source(instance):
    image = instance.get('image', {})
    return sources.detect(image=image.get('href'),
                          kernel=image.get('kernel'),
                          ramdisk=image.get('ramdisk'),
                          checksum=image.get('checksum'))


def nics_to_port_map(nics, connection):
    """Build a port map from a metalsmith instance."""
    port_map = {}
    for nic in nics:
        for ip in nic.fixed_ips:
            net_name = getattr(nic.network, 'name', None) or nic.network.id
            subnet = connection.network.get_subnet(ip['subnet_id'])
            net_info = port_map.setdefault(
                net_name, {'network': nic.network.to_dict(),
                           'fixed_ips': [], 'subnets': []})
            net_info['fixed_ips'].append({'ip_address': ip['ip_address']})
            net_info['subnets'].append(subnet.to_dict())
    return port_map
