#!/usr/bin/env python
# Copyright (c) 2022 Red Hat, Inc.
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

from collections import deque
import copy
import weakref
import yaml


class TripleoInventoryHost:
    def __init__(self, name):
        self.name = name
        self.vars = {}
        self._groups = {}

    def add_group(self, group):
        self._groups[group.name] = weakref.ref(group)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}('{}')".format(
            self.__class__.__name__,
            self.name
        )

    @property
    def groups(self):
        return {n: r() for n, r in self._groups.items()}

    def resolve_vars(self):
        """Returns the resulting vars for this host including group vars"""
        vars = copy.deepcopy(self.vars)
        for group in self.groups.values():
            group_vars = copy.deepcopy(group.vars)
            group_vars.update(vars)
            vars = group_vars
        return vars


class TripleoInventoryGroup:
    def __init__(self, name):
        self.name = name
        self._hosts = {}
        self.vars = {}
        self._children = {}
        self._parents = {}

    def add_parent(self, group):
        if self in group.get_ancestors():
            raise RuntimeError(
                "Adding group '{}' as parent of '{}' creates a recursive dependency loop".format(
                    group.name, self.name
                )
            )
        self._parents[group.name] = weakref.ref(group)

    def add_child(self, group):
        if self in group.get_descendants():
            raise RuntimeError(
                "Adding group '{}' as child of '{}' creates a recursive dependency loop".format(
                    group.name, self.name
                )
            )
        self._children[group.name] = weakref.ref(group)

    def add_host(self, host):
        self._hosts[host.name] = weakref.ref(host)

    def get_ancestors(self):
        ancestors = set(self.parents.values())
        parents_todo = deque(self.parents.values())
        while parents_todo:
            parent = parents_todo.popleft()
            parent_ancestors = parent.parents.values()
            ancestors.update(parent_ancestors)
            parents_todo.extend(parent_ancestors)
        return list(ancestors)

    def get_descendants(self):
        descendants = set(self.children.values())
        children_todo = deque(self.children.values())
        while children_todo:
            child = children_todo.popleft()
            child_descendents = child.children.values()
            descendants.update(child_descendents)
            children_todo.extend(child_descendents)
        return list(descendants)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}('{}')".format(
            self.__class__.__name__,
            self.name
        )

    @property
    def hosts(self):
        return {n: r() for n, r in self._hosts.items()}

    @property
    def children(self):
        return {n: r() for n, r in self._children.items()}

    @property
    def parents(self):
        return {n: r() for n, r in self._parents.items()}


class TripleoInventoryManager:
    """Container class for a tree of inventory hosts/groups"""
    def __init__(self, inventory_file=None):
        self.host = {}
        self.groups = {}
        if inventory_file is not None:
            self.parse_inventory_file(inventory_file)

    def parse_inventory_file(self, inventory_file):
        """Parse a yaml ansible inventory file"""
        self.hosts, self.groups = self._read_yaml_inventory(inventory_file)

    def get_hosts(self, groupname):
        """Return a list of host objects for the given group"""
        hosts = []
        groups = deque([])
        if groupname in self.groups:
            groups.append(self.groups[groupname])
        while groups:
            group = groups.popleft()
            hosts += group.hosts.values()
            groups.extend(group.children.values())
        return hosts

    def _read_yaml_inventory(self, inventory_file):
        with open(inventory_file) as in_file:
            data = yaml.safe_load(in_file)
        return self._parse_inventory(data)

    def _parse_inventory(self, data):
        groups = {}
        hosts = {}

        # Initialize groups_to_parse
        # As child groups are encountered they will be appended
        groups_to_parse = deque([
            # (name, parent, data)
            (group_name, None, group_data) for group_name, group_data in data.items()
        ])

        # Build the tree.
        # InventoryManager holds a reference to all object so can just use weak-refs
        # for the cyclic parent/child relationships
        while groups_to_parse:
            group_name, parent_group, group_data = groups_to_parse.popleft()
            group = groups.setdefault(group_name, TripleoInventoryGroup(group_name))
            if parent_group is not None:
                group.add_parent(parent_group)
                parent_group.add_child(group)
            group_hosts = group_data.get('hosts', {})
            if isinstance(group_hosts, str):
                host_name = group_hosts
                host = hosts.setdefault(host_name, TripleoInventoryHost(host_name))
                host.add_group(group)
                group.add_host(host)
            else:
                for host_name, host_data in group_hosts.items():
                    host = hosts.setdefault(host_name, TripleoInventoryHost(host_name))
                    if host_data is not None:
                        host.vars.update(host_data)
                    host.add_group(group)
                    group.add_host(host)
            group.vars.update(group_data.get('vars', {}))
            for child_name, child_data in group_data.get('children', {}).items():
                groups_to_parse.append((child_name, group, child_data))
        return hosts, groups
