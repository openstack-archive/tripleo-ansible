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

import json

from collections import OrderedDict
from operator import itemgetter


class FilterModule(object):
    def filters(self):
        return {
            'singledict': self.singledict,
            'subsort': self.subsort,
            'needs_delete': self.needs_delete
        }

    def subsort(self, dict_to_sort, attribute, null_value=None):
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

    def singledict(self, list_to_convert):
        """Generate a single dictionary from a list of dictionaries.

        This filter will return a single dictionary from a list of
        dictionaries.
        """
        return_dict = {}
        for i in list_to_convert:
            return_dict.update(i)
        return return_dict

    def needs_delete(self, container_infos, config, config_id):
        """Returns a list of containers which need to be removed.

        This filter will check which containers need to be removed for these
        reasons: no config_data, updated config_data or container not
        part of the global config.
        """
        to_delete = []
        to_skip = []
        installed_containers = []
        for c in container_infos:
            c_name = c['Name']
            installed_containers.append(c_name)

            # Don't delete containers not managed by tripleo-ansible
            if c['Config']['Labels'].get('managed_by') != 'tripleo_ansible':
                to_skip += [c_name]
                continue

            # Only remove containers managed in this config_id
            if c['Config']['Labels'].get('config_id') != config_id:
                to_skip += [c_name]
                continue

            # Remove containers with no config_data
            # e.g. broken config containers
            if 'config_data' not in c['Config']['Labels']:
                to_delete += [c_name]
                continue

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
            try:
                c_facts = [c['Config']['Labels']['config_data']
                           for c in container_infos if c_name == c['Name']]
            except KeyError:
                continue
            c_facts = c_facts[0] if len(c_facts) == 1 else {}

            # 0 was picked since it's the null_value for the subsort filter.
            # When a container config doesn't provide the start_order, it'll be
            # 0 by default, therefore it needs to be added in the config_data
            # when comparing with the actual container_infos results.
            if 'start_order' not in config_data:
                config_data['start_order'] = 0

            # TODO(emilien) double check the comparing here and see if
            # types are accurate (string vs dict, etc)
            if c_facts != json.dumps(config_data):
                to_delete += [c_name]
                continue

        return to_delete
