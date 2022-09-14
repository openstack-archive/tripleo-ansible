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
from ansible.module_utils.parsing.convert_bool import boolean

import glob
import json
import os
import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: container_config_data
author:
  - Emilien Macchi <emilien@redhat.com>
version_added: '2.8'
short_description: Generates a dictionary which contains all container configs
notes: []
description:
  - This module reads container configs in JSON files and generate a dictionary
    which later will be used to manage the containers.
options:
  config_path:
    description:
      - The path of a directory or a file where the JSON files are.
        This parameter is required.
    required: True
    type: str
  config_pattern:
    description:
      - Search pattern to find JSON files.
    default: '*.json'
    required: False
    type: str
  config_overrides:
    description:
      - Allows to override any container configuration which will take
        precedence over the JSON files.
    default: {}
    required: False
    type: dict
  debug:
    description:
      - Whether or not debug is enabled.
    default: False
    required: False
    type: bool
"""

EXAMPLES = """
- name: Generate containers configs data
  container_config_data:
    config_path: /var/lib/tripleo-config/container-startup-config/step_1
- name: Generate containers configs data for HAproxy and override image
  container_config_data:
    config_path: /var/lib/tripleo-config/container-startup-config/step_1
    config_pattern: 'haproxy.json'
    config_overrides:
      haproxy:
        image: my-registry.io/tripleo/haproxy:mytag
"""

RETURN = """
configs:
    description:
      - Dictionary with container configs ready to be consumed by
        tripleo_container_manage role.
    returned: always
    type: dict
"""


class ContainerConfigDataManager(object):
    """Notes about this module.

    It will generates a dictionary which contains all container configs,
    later consumed by tripleo_container_manage role.
    """

    def __init__(self, module, results):

        self.module = module
        self.results = results

        # parse args
        args = self.module.params

        # Set parameters
        config_path = args['config_path']
        config_pattern = args['config_pattern']
        config_overrides = args['config_overrides']
        self.debug = args['debug']

        # Generate dict from JSON files that match search pattern
        if os.path.exists(config_path):
            matched_configs = glob.glob(os.path.join(config_path,
                                                     config_pattern))
            config_dict = {}
            for mc in matched_configs:
                name = os.path.splitext(os.path.basename(mc))[0]
                config = json.loads(self._slurp(mc))
                if self.debug:
                    self.module.debug('Config found for {}: {}'.format(name,
                                                                       config))
                config_dict.update({name: config})

            # Merge the config dict with given overrides
            self.results['configs'] = self._merge_with_overrides(
                    config_dict, config_overrides)
        else:
            self.module.debug(
                msg='{} does not exists, skipping step'.format(config_path))
            self.results['configs'] = {}

        # Returns data
        self.module.exit_json(**self.results)

    def _merge_with_overrides(self, config, merge_with=None):
        """Merge config with a given dict of overrides.

        :param config: dictionary of configs
        :param merge_with: dictionary of overrides
        :return: dict
        """
        merged_dict = config
        if merge_with is None:
            merge_with = {}
        for k in merge_with.keys():
            if k in config:
                for mk, mv in merge_with[k].items():
                    if self.debug:
                        self.module.debug('Override found for {}: {} will be '
                                          'set to {}'.format(k, mk, mv))
                    merged_dict[k][mk] = mv
                break
        return merged_dict

    def _slurp(self, path):
        """Slurps a file and return its content.

        :param path: string
        :returns: string
        """
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        else:
            self.module.warn('{} was not found.'.format(path))
            return ''


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
    )
    results = dict(
        changed=False,
        configs={}
    )
    ContainerConfigDataManager(module, results)


if __name__ == '__main__':
    main()
