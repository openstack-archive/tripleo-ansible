#!/usr/bin/python
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
__metaclass__ = type

import hashlib
import os
import uuid


from ansible.errors import AnsibleAction
from ansible.errors import AnsibleActionFail
from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.plugins.action import display


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        scp_source = self._task.args.get('scp_source', None)
        scp_continue = self._task.args.get('scp_continue_on_error', False)
        state = self._task.args.get('state', 'present')

        try:
            # Ensure it's a valid uuid
            image_id = str(uuid.UUID(self._task.args.get('id')))
        except ValueError:
            raise AnsibleError(
                "Invalid image id: {}".format(
                    self._task.args.get('id')
                 )
            )

        cache_dir = task_vars.get(
            'tripleo_nova_cache_dir',
            '/var/lib/nova/instances/_base'
        )
        cache_fn = hashlib.sha1(image_id.encode('utf-8')).hexdigest()
        cache_file = os.path.join(cache_dir, cache_fn)
        cache_tmp = os.path.join(
            cache_dir,
            'ansible_tripleo_nova_cache_tmp_{}'.format(os.getpid())
        )
        tmp_file = os.path.join(cache_tmp, cache_fn)
        container_cli = task_vars.get('container_cli', 'podman')

        result.update({'actions': []})

        try:
            # Ensure target directory exists
            command_args = {
                '_raw_params':
                    (
                        "{} exec -u nova nova_compute /bin/bash -c "
                        "\"mkdir -p '{}'; chmod 755 '{}'\""
                    ).format(container_cli, cache_dir, cache_dir),
                'creates': cache_dir

            }
            command_task_vars = {
                'become': True,
                'ansible_facts': task_vars.get('ansible_facts', {}),
                'ansible_delegated_vars': task_vars.get('ansible_delegated_vars', {})
            }
            command_result = self._execute_module(
                'command',
                module_args=command_args,
                task_vars=command_task_vars
            )
            command_result['name'] = 'Ensure nova cache dir exists'
            result['actions'].append(command_result)
            cmd = self._connection._shell.exists(cache_file)
            cache_file_exists_res = self._low_level_execute_command(
                cmd,
                sudoable=True
            )
            cache_file_exists = self._parse_returned_data(
                cache_file_exists_res).get('rc', 0) == 0
            result['actions'].append({
                'name': 'Check if cache file exists',
                'exists': cache_file_exists
            })

            new_module_args = self._task.args.copy()
            new_module_args.pop('scp_source', None)
            new_module_args['_cache_dir'] = cache_dir
            new_module_args['_cache_file'] = cache_file

            if state == 'present' and \
                    not cache_file_exists and \
                    scp_source is not None:
                # Create tmp dir
                command_args = {
                    '_raw_params':
                        (
                            "{} exec -u nova nova_compute /bin/bash -c "
                            "\"mkdir -p '{}'; chmod 755 '{}'\""
                        ).format(container_cli, cache_tmp, cache_tmp),
                }
                command_task_vars = {
                    'become': True,
                    'ansible_facts': task_vars.get('ansible_facts', {}),
                    'ansible_delegated_vars': task_vars.get('ansible_delegated_vars', {})
                }
                command_result = self._execute_module(
                    'command',
                    module_args=command_args,
                    task_vars=command_task_vars
                )
                command_result['name'] = 'Create tmp dir'
                result['actions'].append(command_result)

                command_args = {
                    '_raw_params':
                        "{} exec -u nova nova_compute scp {}:'{}' '{}'".format(
                            container_cli,
                            scp_source,
                            cache_file,
                            cache_tmp
                        )
                }
                command_task_vars = {
                    'become': True,
                    'ignore_errors': True,
                    'ansible_facts': task_vars.get('ansible_facts', {}),
                    'ansible_delegated_vars': task_vars.get('ansible_delegated_vars', {})
                }
                command_result = self._execute_module(
                    'command',
                    module_args=command_args,
                    task_vars=command_task_vars)
                command_result['name'] = 'Fetch image from {}'.format(
                    scp_source
                )
                result['actions'].append(command_result)
                if command_result['rc'] == 0:
                    new_module_args['_prefetched_path'] = tmp_file
                elif not scp_continue:
                    raise AnsibleActionFail(
                        '{} failed: {}'.format(
                            command_result['name'],
                            command_result['msg']
                        )
                    )

            command_result = self._execute_module(
                'tripleo_nova_image_cache',
                module_args=new_module_args,
                task_vars=task_vars
            )
            result['actions'] += command_result.pop('actions', [])
            result.update(command_result)

        except AnsibleAction as e:
            result.update(e.result)
        finally:
            cmd = self._connection._shell.remove(cache_tmp, recurse=True)
            tmp_rm_res = self._low_level_execute_command(cmd, sudoable=True)
            tmp_rm_data = self._parse_returned_data(tmp_rm_res)
            if tmp_rm_data.get('rc', 0) != 0:
                display.warning(
                    'Error deleting remote temporary files '
                    ' (rc: %s, stderr: %s})' % (
                        tmp_rm_res.get('rc'),
                        tmp_rm_res.get('stderr', 'No error string available.')
                    )
                )
            self._remove_tmp_path(self._connection._shell.tmpdir)
        return result
