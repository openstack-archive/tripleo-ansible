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

import glob
import json
import os
import shutil
import yaml

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: container_startup_config
author:
  - "TripleO team"
version_added: '2.9'
short_description: Generate startup containers configs
notes: []
description:
  - It will generate container startup configs that will be consumed by the
    tripleo-container-manage role that is using podman_container module.
requirements:
  - None
options:
  config_base_dir:
    description:
      - Config base directory
    type: str
    default: '/var/lib/tripleo-config/container-startup-config'
  config_data:
    description:
      - Dictionary of container configs data
    type: dict
    required: true
"""

EXAMPLES = """
- name: Generate startup container config for all the steps
  container_startup_config:
    config_data:
      step_1:
        haproxy:
          image: quay.io/haproxy
        memcached:
          image: quay.io/memcached
      step_2:
        mysql:
          image: quay.io/mysql
"""


class ContainerStartupManager:
    """Class for container_startup_config module."""

    def __init__(self, module, results):

        super(ContainerStartupManager, self).__init__()
        self.module = module
        self.results = results

        # parse args
        args = self.module.params

        # Set parameters
        self.config_base_dir = args['config_base_dir']
        self.config_data = args['config_data']

        # Cleanup old configs created by previous releases
        self._cleanup_old_configs()

        # Create config_base_dir
        if not os.path.exists(self.config_base_dir):
            os.makedirs(self.config_base_dir)
            os.chmod(self.config_base_dir, 0o600)
            self.results['changed'] = True

        # Generate the container configs per step
        for step, step_config in self.config_data.items():
            step_dir = os.path.join(self.config_base_dir, step)
            self._recreate_dir(step_dir)
            for container, container_config in step_config.items():
                container_config_path = os.path.join(self.config_base_dir,
                                                     step, container + '.json')
                self._create_config(container_config_path, container_config)

        self.module.exit_json(**self.results)

    def _recreate_dir(self, path):
        """Creates a directory.

        :param path: string
        """
        os.makedirs(path)

    def _create_config(self, path, config):
        """Update a container config.

        :param path: string
        :param config: string
        """
        with open(path, "wb") as config_file:
            config_file.write(json.dumps(config, indent=2).encode('utf-8'))
        os.chmod(path, 0o600)
        self.results['changed'] = True

    def _cleanup_old_configs(self):
        """Cleanup old container configurations from previous releases.
        """
        pattern = '*docker-container-startup-config*.json'
        old_configs = glob.glob(os.path.join('/var/lib/tripleo-config',
                                             pattern))
        for config in old_configs:
            os.remove(config)

        step_dirs = glob.glob(self.config_base_dir + '/step_*')
        for step_dir in step_dirs:
            shutil.rmtree(step_dir, ignore_errors=True)


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
    )
    results = dict(
        changed=False
    )
    ContainerStartupManager(module, results)


if __name__ == '__main__':
    main()
