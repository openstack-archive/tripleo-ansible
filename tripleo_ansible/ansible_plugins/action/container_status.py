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

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import copy
import tenacity
import yaml

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

DISPLAY = Display()

# Default delay/retries used to fetch containers status and wait for them to be
# finished.
DELAY = 10
RETRIES = 30
TIMEOUT = DELAY * RETRIES

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
module: container_status
author:
  - "TripleO team"
version_added: '2.9'
short_description: Check and report containers status
notes: []
description:
  - For each container that isn't an exec or a container supposed to be
    controlled by systemd, we expect it to terminate with a return code.
    This module will check that code and make sure it's correct. If not, it
    will report the failure for easier debug.
requirements:
  - None
options:
  container_async_results:
    description:
      - Async results of a podman_container invocation.
    type: list
  container_data:
    description:
      - List of dictionaries which have the container configurations.
    type: list
  valid_exit_codes:
    description:
      - List of valid container exit codes.
    default: []
    type: list
  debug:
    description:
      - Whether or not debug is enabled.
    default: False
    type: boolean
"""
EXAMPLES = """
- name: Check containers status
  containers_status:
    container_async_results: "{{ create_async_poll_results.results }}"
    container_data:
      - keystone:
          image: docker.io/keystone
      - mysql_bootstrap:
          image: docker.io/mysql
    valid_exit_codes:
      - 0
      - 2
"""
RETURN = """
changed_containers:
    description: List of containers which changed.
    returned: always
    type: list
    sample:
      - keystone
      - mysql
commands:
    description: List of container cli commands that would be run.
    returned: always
    type: list
    sample:
      - podman rm -f keystone
      - podman run keystone
"""


class ActionModule(ActionBase):
    """Action plugin for container status"""

    _VALID_ARGS = yaml.safe_load(DOCUMENTATION)['options']

    def _get_args(self):
        missing = []
        args = {}

        for option, vals in self._VALID_ARGS.items():
            if 'default' not in vals:
                if self._task.args.get(option, None) is None:
                    missing.append(option)
                    continue
                args[option] = self._task.args.get(option)
            else:
                args[option] = self._task.args.get(option, vals['default'])

        if missing:
            raise AnsibleActionFail('Missing required parameters: {}'.format(
                ', '.join(missing)))
        return args

    def _get_containers_to_check(self, data):
        """Return a list of containers that we need to check.

        Given some container_data, figure out what containers terminate with
        a return code so later we can check that code.

        :param data: Dictionary of container data.
        :returns: List of containers that need to be checked.
        """
        containers_exec = []
        containers_run = []
        # loop through container data to get specific container
        for container in data:
            # get container name and data
            for name, values in container.items():
                if 'restart' in values:
                    continue
                if 'action' in values:
                    containers_exec.append(name)
                if 'image' in values:
                    # We assume that container configs that don't have a
                    # restart policy nor action (used for podman exec) but have
                    # an image set, will run something and then exit with a
                    # return code.
                    containers_run.append(name)
        if self.debug and len(containers_run) > 0:
            DISPLAY.display('These containers are supposed to terminate with '
                            'a valid exit code and will be checked: '
                            '{}'.format(containers_run))
        if self.debug and len(containers_exec) > 0:
            DISPLAY.display('These containers exec are supposed to terminate '
                            'with a valid exit code and will be checked: '
                            '{}'.format(containers_exec))
        return containers_run

    def _get_commands(self, results):
        """Return a list of commands that were executed by container tool.

        :param results: Ansible task results.
        :returns commands: List of commands.
        """
        commands = []
        for item in results:
            try:
                if item['changed']:
                    commands.extend(item['podman_actions'])
            except KeyError:
                if 'cmd' in item:
                    commands.append(' '.join(item['cmd']))
                else:
                    raise AnsibleActionFail('Wrong async result data, missing'
                                            ' podman_actions or cmd:'
                                            ' {}'.format(item))
        return commands

    def _is_container_running(self, container):
        """Return True if a container has Running State.

        :params container: Dictionary for container infos.
        :returns running: Boolean of container running status.
        """
        state = container.get('State', {})
        running = state.get('Running', False)
        return running

    def _get_container_infos(self, containers, task_vars):
        """Return container infos.

        :params containers: List of containers.
        :params task_vars: Dictionary of Ansible tasks variables.
        :returns container_results: Dictionary of container infos.
        """
        tvars = copy.deepcopy(task_vars)
        result = self._execute_module(
            module_name='containers.podman.podman_container_info',
            module_args=dict(name=containers),
            task_vars=tvars
        )
        return [c for c in result["containers"] if "containers" in result]

    @tenacity.retry(
        reraise=True,
        stop=tenacity.stop_after_attempt(RETRIES),
        wait=tenacity.wait_fixed(DELAY)
    )
    def _fetch_container_state(self, containers, task_vars):
        """Return container states of finished containers with retries.

        :params containers: List of containers.
        :params task_vars: Dictionary of Ansible tasks variables.
        :returns container_results: Dictionary of container infos.
        """
        containers_results = self._get_container_infos(containers, task_vars)
        for container in containers_results:
            name = container.get('Name')
            if self._is_container_running(container):
                raise AnsibleActionFail('Container {} has not finished yet, '
                                        'retrying...'.format(name))
        return containers_results

    def _check_container_state(self, containers, exit_codes, task_vars):
        """Return a tuple of running and failed containers.

        :params containers: List of containers to check.
        :params exit_codes: List of valid exit codes.
        :params task_vars: Dictionary of Ansible tasks variables.
        :returns running, failed: Tuple of lists.
        """
        running = []
        failed = []
        try:
            self._fetch_container_state(containers, task_vars)
        except AnsibleActionFail:
            # We fail at the end with all the other infos
            if self.debug:
                DISPLAY.display('One or more containers did not finish on '
                                'time, the failure will be reported later.')
            pass
        containers_results = self._get_container_infos(containers, task_vars)
        for container in containers_results:
            container_name = container.get('Name')
            container_state = container.get('State')
            if self._is_container_running(container):
                running.append(container_name)
            elif container_state.get('ExitCode') not in exit_codes:
                failed.append(container_name)
        return (running, failed)

    def _check_errors_in_ansible_async_results(self, results):
        """Get a tuple with changed and failed containers.

        :param results: Ansible results from "Check podman create status"
        :returns: Tuple of containers that changed or failed
        """
        changed = []
        create_failed = []
        exec_failed = []
        for item in results:
            # if Ansible is run in check mode, the async_results items will
            # not contain failed or finished keys.
            if self._play_context.check_mode:
                break
            if 'create_async_result_item' in item:
                async_item = item['create_async_result_item']
                if item['changed']:
                    for name, c in async_item['container_data'].items():
                        changed.append(name)
                if (item['failed'] or not item['finished']
                        or ('stderr' in async_item
                            and async_item['stderr'] != '')):
                    for name, c in async_item['container_data'].items():
                        create_failed.append(name)
            if 'exec_async_result_item' in item:
                async_item = item['exec_async_result_item']
                if item['rc'] != 0:
                    for name, c in async_item['container_exec_data'].items():
                        exec_failed.append(name)
        return (changed, create_failed, exec_failed)

    def run(self, tmp=None, task_vars=None):
        self._supports_check_mode = True
        self.changed = False
        self.changed_containers = []
        container_commands = []
        running = []
        failed = []

        if task_vars is None:
            task_vars = dict()
        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp
        # parse args
        args = self._get_args()

        async_results = args['container_async_results']
        container_data = args['container_data']
        valid_exit_codes = args['valid_exit_codes']
        self.debug = args['debug']

        containers_run_to_check = self._get_containers_to_check(container_data)

        # Check that the containers which are supposed to finish have
        # actually finished and also terminated with the right exit code.
        if len(valid_exit_codes) > 0 and len(containers_run_to_check) > 0:
            (running, failed) = self._check_container_state(
                containers_run_to_check,
                valid_exit_codes,
                task_vars)

        # Check the Ansible async results for containers which:
        # - reported a changed resources (podman_container created or updated
        #   a container) and return it as self.changed_containers.
        # - reported a failed resource (podman_container failed to create
        #   the container and return it as self.failed_containers.
        # - didn't finish on time and return it as self.failed_containers.
        (self.changed_containers, async_failed, exec_failed) = (
            self._check_errors_in_ansible_async_results(async_results))

        if len(exec_failed) > 0:
            DISPLAY.error('Container(s) exec commands which failed to execute'
                          ': {}'.format(failed))
        if len(failed) > 0:
            DISPLAY.error('Container(s) which finished with wrong return code'
                          ': {}'.format(failed))
        if len(async_failed) > 0:
            DISPLAY.error('Container(s) which failed to be created by '
                          'podman_container module: {}'.format(async_failed))
        if len(running) > 0:
            DISPLAY.error('Container(s) which did not finish after {} '
                          'minutes: {}'.format(TIMEOUT, running))
        total_errors = list(set(failed + exec_failed + async_failed + running))
        if len(total_errors) > 0:
            raise AnsibleActionFail('Failed container(s): {}, check logs in '
                                    '/var/log/containers/'
                                    'stdouts/'.format(total_errors))

        container_commands = self._get_commands(async_results)
        if len(container_commands) > 0 and \
                (self._play_context.check_mode or self.debug):
            for cmd in container_commands:
                DISPLAY.display(cmd)

        if len(container_commands) > 0:
            self.changed = True

        result['changed_containers'] = self.changed_containers
        result['commands'] = container_commands
        result['changed'] = self.changed
        return result
