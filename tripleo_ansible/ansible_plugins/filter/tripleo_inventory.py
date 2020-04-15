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

import collections
import six
import sys
import yaml


def to_inventory_hostmap(data):
    # Flattens inventory to a group->host mapping
    if isinstance(data, six.string_types):
        inventory = yaml.safe_load(data)
    else:
        inventory = data

    group_host_map = {}

    todo = collections.deque(inventory.keys())
    while todo:
        group = todo.popleft()
        if 'hosts' in inventory[group]:
            group_host_map[group] = list(inventory[group]['hosts'])
        else:
            if 'children' in inventory[group]:
                for child in inventory[group]['children']:
                    # Children have not all been flattened yet
                    # so postpone flattening this group
                    if child in todo:
                        todo.append(group)
                        break
                else:
                    group_host_map[group] = []
                    for child in inventory[group]['children']:
                        group_host_map[group] += group_host_map[child]
                    group_host_map[group].sort()
    return group_host_map


def to_inventory_rolemap(data):
    # Falttens inventory to a group->role mapping
    if isinstance(data, six.string_types):
        inventory = yaml.safe_load(data)
    else:
        inventory = data

    group_role_map = {}

    todo = collections.deque(inventory.keys())
    while todo:
        group = todo.popleft()
        if 'tripleo_role_name' in inventory[group].get('vars', {}):
            group_role_map[group] = [inventory[group]['vars']['tripleo_role_name']]
        else:
            if 'children' in inventory[group]:
                for child in inventory[group]['children']:
                    # Children have not all been flattened yet
                    # so postpone flattening this group
                    if child in todo:
                        todo.append(group)
                        break
                else:
                    group_role_map[group] = []
                    for child in inventory[group]['children']:
                        group_role_map[group] += group_role_map[child]
                    group_role_map[group].sort()
    return group_role_map


def to_inventory_roles(data):
    # Returns list of tripleo roles in inventory
    if isinstance(data, six.string_types):
        inventory = yaml.safe_load(data)
    else:
        inventory = data

    roles = {}
    for group, group_data in six.iteritems(inventory):
        group_role = group_data.get('vars', {}).get('tripleo_role_name', None)
        if group_role is not None:
            roles[group_role] = True
    return sorted(list(roles))


class FilterModule(object):
    def filters(self):
        return {
            'to_inventory_hostmap': to_inventory_hostmap,
            'to_inventory_rolemap': to_inventory_rolemap,
            'to_inventory_roles': to_inventory_roles,
        }
