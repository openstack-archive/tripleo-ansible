#!/usr/bin/env python
# Copyright 2019 Red Hat, Inc.
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

import ast
import json
import re
import six

from collections import OrderedDict
from operator import itemgetter


# cmp() doesn't exist on python3
if six.PY3:
    def cmp(a, b):
        return 0 if a == b else 1


class FilterModule(object):
    def filters(self):
        return {
            'singledict': self.singledict,
            'subsort': self.subsort,
            'needs_delete': self.needs_delete,
            'haskey': self.haskey,
            'list_of_keys': self.list_of_keys,
            'container_exec_cmd': self.container_exec_cmd,
            'get_key_from_dict': self.get_key_from_dict,
            'get_role_assignments': self.get_role_assignments,
            'get_domain_id': self.get_domain_id,
            'get_changed_containers': self.get_changed_containers,
            'get_failed_containers': self.get_failed_containers
        }

    def subsort(self, dict_to_sort, attribute, null_value=0):
        """Sort a hash from a sub-element.

        This filter will return an dictionary ordered by the attribute
        part of each item.
        """
        for k, v in dict_to_sort.items():
            if attribute not in v:
                dict_to_sort[k][attribute] = null_value

        data = {}
        for d in dict_to_sort.items():
            if d[1][attribute] not in data:
                data[d[1][attribute]] = []
            data[d[1][attribute]].append({d[0]: d[1]})

        sorted_list = sorted(
            data.items(),
            key=lambda x: x[0]
        )
        ordered_dict = {}
        for o, v in sorted_list:
            ordered_dict[o] = v
        return ordered_dict

    def singledict(self, list_to_convert, merge_with={}):
        """Generate a single dictionary from a list of dictionaries.

        This filter will return a single dictionary from a list of
        dictionaries.
        If merge_with is set, the return dict will be merged with it.
        """
        return_dict = {}
        for i in list_to_convert:
            return_dict.update(i)
            for k in merge_with.keys():
                if k in return_dict:
                    for mk, mv in merge_with[k].items():
                        return_dict[k][mk] = mv
                    break
        return return_dict

    def needs_delete(self, container_infos, config, config_id,
                     clean_orphans=True, check_config=True):
        """Returns a list of containers which need to be removed.

        This filter will check which containers need to be removed for these
        reasons: no config_data, updated config_data or container not
        part of the global config.

        :param container_infos: list
        :param config: dict
        :param config_id: string
        :param clean_orphans: bool
        :param check_config: bool to whether or not check if config changed
        :returns: list
        """
        to_delete = []
        to_skip = []
        installed_containers = []

        # If config has no item, it's probably due to a user error where
        # the given pattern match no container.
        # If config has one item, it's because we want to manage only one
        # container.
        # In both cases, we don't want to remove the others in the same
        # config_id.
        if len(config) <= 1:
            clean_orphans = False

        for c in container_infos:
            c_name = c['Name']
            installed_containers.append(c_name)
            labels = c['Config'].get('Labels')
            if not labels:
                labels = dict()
            managed_by = labels.get('managed_by', 'unknown').lower()

            # Check containers have a label
            if not labels:
                to_skip += [c_name]
                continue

            # Don't delete containers NOT managed by tripleo* or paunch*
            elif not re.findall(r"(?=("+'|'.join(['tripleo', 'paunch'])+r"))",
                                managed_by):
                to_skip += [c_name]
                continue

            # Only remove containers managed in this config_id
            elif labels.get('config_id') != config_id:
                to_skip += [c_name]
                continue

            # Remove containers with no config_data
            # e.g. broken config containers
            elif 'config_data' not in labels and clean_orphans:
                to_delete += [c_name]

        for c_name, config_data in config.items():
            # don't try to remove a container which doesn't exist
            if c_name not in installed_containers:
                continue

            # already tagged to be removed
            if c_name in to_delete:
                continue

            if c_name in to_skip:
                continue

            # Remove containers managed by tripleo-ansible when config_data
            # changed. Since we already cleaned the containers not in config,
            # this check needs to be in that loop.
            # e.g. new TRIPLEO_CONFIG_HASH during a minor update
            c_datas = list()
            for c in container_infos:
                if c_name == c['Name']:
                    try:
                        c_datas.append(c['Config']['Labels']['config_data'])
                    except KeyError:
                        pass

            # Build c_facts so it can be compared later with config_data
            for c_data in c_datas:
                try:
                    c_data = ast.literal_eval(c_data)
                except (ValueError, SyntaxError):  # may already be data
                    try:
                        c_data = dict(c_data)  # Confirms c_data is type safe
                    except ValueError:  # c_data is not data
                        c_data = dict()

                if cmp(c_data, config_data) != 0 and check_config:
                    to_delete += [c_name]

        # Cleanup installed containers that aren't in config anymore.
        for c in installed_containers:
            if c not in config.keys() and c not in to_skip and clean_orphans:
                to_delete += [c]

        return to_delete

    def haskey(self, data, attribute, value=None, reverse=False, any=False):
        """Return dict data with a specific key.

        This filter will take a list of dictionaries (data)
        and will return the dictionnaries which have a certain key given
        in parameter with 'attribute'.
        If reverse is set to True, the returned list won't contain dictionaries
        which have the attribute.
        If any is set to True, the returned list will match any value in
        the list of values for "value" parameter which has to be a list.
        """
        return_list = []
        for i in data:
            for k, v in json.loads(json.dumps(i)).items():
                if attribute in v and not reverse:
                    if value is None:
                        return_list.append(i)
                    else:
                        if isinstance(value, list) and any:
                            if v[attribute] in value:
                                return_list.append({k: v})
                        elif any:
                            raise TypeError("value has to be a list if any is "
                                            "set to True.")
                        else:
                            if v[attribute] == value:
                                return_list.append({k: v})
                if attribute not in v and reverse:
                    return_list.append({k: v})
        return return_list

    def list_of_keys(self, keys_to_list):
        """Return a list of keys from a list of dictionaries.

        This filter takes in input a list of dictionaries and for each of them
        it will add the key to list_of_keys and returns it.
        """
        list_of_keys = []
        for i in keys_to_list:
            for k, v in i.items():
                list_of_keys.append(k)
        return list_of_keys

    def get_key_from_dict(self, data, key, strict=False, default=None):
        """Return a list of unique values from a specific key from a dict.

        This filter takes in input a list of dictionaries and for each of them
        it will add the value of a specific key into returned_list and
        returns it sorted. If the key has to be part of the dict, set strict to
        True. A default can be set if the key doesn't exist but strict has to
        be set to False.
        """
        returned_list = []
        for i in data.items():
            value = i[1].get(key)
            if value is None and not strict and default is not None:
                value = default
            if value is None:
                if strict:
                    raise TypeError('Missing %s key in '
                                    '%s' % (key, i[0]))
                else:
                    continue
            if isinstance(value, list):
                for v in value:
                    if v not in returned_list:
                        returned_list.append(v)
            elif isinstance(value, dict):
                for k, v in value.items():
                    if v not in returned_list:
                        returned_list.append({k: v})
            else:
                if value not in returned_list:
                    returned_list.append(value)
        return returned_list

    def list_or_dict_arg(self, data, cmd, key, arg):
        """Utility to build a command and its argument with list or dict data.

        The key can be a dictionary or a list, the returned arguments will be
        a list where each item is the argument name and the item data.
        """
        if key not in data:
            return
        value = data[key]
        if isinstance(value, dict):
            for k, v in sorted(value.items()):
                if v:
                    cmd.append('%s=%s=%s' % (arg, k, v))
                elif k:
                    cmd.append('%s=%s' % (arg, k))
        elif isinstance(value, list):
            for v in value:
                if v:
                    cmd.append('%s=%s' % (arg, v))

    def container_exec_cmd(self, data, cli='podman'):
        """Return a list of all the arguments to execute a container exec.

        This filter takes in input the container exec data and the cli name
        to return the full command in a list of arguments that will be used
        by Ansible command module.
        """
        cmd = [cli, 'exec']
        cmd.append('--user=%s' % data.get('user', 'root'))
        if 'privileged' in data:
            cmd.append('--privileged=%s' % str(data['privileged']).lower())
        self.list_or_dict_arg(data, cmd, 'environment', '--env')
        cmd.extend(data['command'])
        return cmd

    def get_role_assignments(self, data, default_role='admin',
                             default_project='service'):
        """Return a dict of all roles and their users.

        This filter takes in input the keystone resources data and
        returns a dict where each key is a role and its users assigned.
        If 'domain' or 'project' are specified, they are added to the user
        entry; so the user will be assign to the domain or the project.
        If no domain and no project are specified, default_project will be
        used.
        Note that domain and project are mutually exclusive in Keystone v3.
        """
        returned_dict = {}
        for d in data:
            for k, v in d.items():
                roles = v.get('roles', default_role)
                domain = v.get('domain')
                project = v.get('project')

                if domain is not None and project is not None:
                    raise TypeError('domain and project need to be mutually '
                                    'exclusive for user: %s' % k)

                if isinstance(roles, list):
                    for r in roles:
                        if r not in returned_dict:
                            returned_dict[r] = []
                        if domain is not None:
                            returned_dict[r].append({k: {'domain': domain}})
                        elif project is not None:
                            returned_dict[r].append({k: {'project': project}})
                        else:
                            returned_dict[r].append({k: {'project':
                                                         default_project}})
                else:
                    if roles not in returned_dict:
                        returned_dict[roles] = []
                    if domain is not None:
                        returned_dict[roles].append({k: {'domain': domain}})
                    elif project is not None:
                        returned_dict[roles].append({k: {'project': project}})
                    else:
                        returned_dict[roles].append({k: {'project':
                                                         default_project}})
        return returned_dict

    def get_domain_id(self, domain_name, all_domains):
        """Return the ID of a domain by its name.

        This filter taks in input a domain name and a dictionary with all
        domain informations.
        """
        if domain_name == '':
            return
        for d in all_domains:
            if d.get('name') == domain_name:
                return d.get('id')
        raise KeyError('Could not get domain ID for "%s"' % domain_name)

    def get_changed_containers(self, async_results):
        """Return a list of containers that changed.

        This filter takes in input async results of a podman_container
        invocation and returns the list of containers with actions, so we
        know which containers have changed.
        """
        changed = []
        for item in async_results:
            if item.get('podman_actions'):
                if item['container'].get('Name'):
                    changed.append(item['container'].get('Name'))
        return changed

    def get_failed_containers(self, async_results):
        """Return a list of containers that failed to start on time.

        This filter takes in input async results of a podman_container
        invocation and returns the list of containers that did not
        finished correctly.
        """
        failed = []
        for item in async_results:
            if item['failed'] or not item['finished']:
                async_result_item = item['create_async_result_item']
                for k, v in async_result_item['container_data'].items():
                    failed.append(k)
        return failed
