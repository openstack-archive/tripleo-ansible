#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2018 OpenStack Foundation
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ansible.module_utils.basic import AnsibleModule

import json
import subprocess

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: Podman
author:
    - Jill Rouleau (@jillrouleau)
version_added: '2.8'
short_description: Manage containers with Podman
notes: []
description:
    - Start or stop containers with Podman
options:
  name:
    description:
      - Name of the container(s) to start or stop.
    required: True
  state:
    description:
      - The desired state for the container.
    default: started
    choices:
      - started
      - stopped
  restart:
    description:
      - Use with started state to force a matching container to be stopped
      and restarted.
"""

EXAMPLES = """
# Start a container
- name: Start the myapp container
  podman_container:
    name: myapp
    state: started

# Stop a container
- name: Stop the myapp container
  podman_container:
    name: myapp
    state: stopped
"""


class PodmanContainerInstance(object):
    """Gather information about a container instance. """
    def __init__(self, name):
        super(PodmanContainerInstance, self).__init__()
        self.parameters = None
        self.name = name
        output = subprocess.check_output(
            ['podman', 'container', 'inspect', self.name])
        self.parameters = json.loads(output)[0]


class PodmanContainerManager(object):

    def __init__(self, module, results):

        super(PodmanContainerManager, self).__init__()

        self.module = module
        self.results = results
        self.name = self.module.params.get('name')
        self.state = self.module.params.get('state')
        self.restart = self.module.params.get('restart')
        self.executable = \
            self.module.get_bin_path(module.params.get('executable'),
                                     required=True)
        self.container_instance = PodmanContainerInstance(self.name)
        """
        so what i actually need to do here is:
        identify if the container already exists and is running or not;
        figure out what the user wants the state to ultimately be;
        act accordingly
        """

        if self.state in ['started'] and \
                self.container_instance.parameters['State']['Status'] \
                != 'running':
            self.start_container(self.name)
        elif self.state in ['started'] and \
                self.container_instance.parameters['State']['Status'] \
                == 'running' and self.restart is True:
            self.stop_container(self.name)
            self.start_container(self.name)
        elif self.state in ['stopped'] and \
                self.container_instance.parameters['State']['Status'] \
                != 'exited':
            self.stop_container(self.name)

    def start_container(self, name):
        command = [self.executable, 'start', name]
        self.results['action'].append('Starting container {}'.format(name))
        self.results['changed'] = True
        if not self.module.check_mode:
            rc, out, err = self.module.run_command(command)

            if rc != 0:
                self.module.fail_json(
                    msg="Unable to start container '{0}': '{1}'".format(
                        name, err))

    def stop_container(self, name):
        command = [self.executable, 'stop', name]
        self.results['action'].append('Stopping container {}'.format(name))
        self.results['changed'] = True
        if not self.module.check_mode:
            rc, out, err = self.module.run_command(command)

            if rc != 0:
                self.module.fail_json(
                    msg="Unable to stop container '{0}': '{1}'".format(
                        name, err))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            executable=dict(type='str', default='podman'),
            # TODO(jillr): handle lists of containers
            name=dict(type='str'),
            state=dict(type='str', default='started', choices=['started',
                                                               'stopped']),
            restart=dict(type='bool', default=False),
        ),
        supports_check_mode=True,
    )

    results = dict(
        changed=False,
        original_message='',
        message='',
        action=[]
    )

    if module.check_mode:
        return results

    PodmanContainerManager(module, results)
    module.exit_json(**results)


if __name__ == '__main__':
    main()
