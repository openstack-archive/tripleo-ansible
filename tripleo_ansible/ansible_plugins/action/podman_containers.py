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

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

DISPLAY = Display()


class ActionModule(ActionBase):
    """Action plugin for podman_container module"""

    _VALID_ARGS = frozenset((
        'containers',
    ))

    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)

    def run(self, tmp=None, task_vars=None):
        self._supports_check_mode = True
        self._supports_async = True
        del tmp  # tmp no longer has any effect
        if task_vars is None:
            task_vars = {}

        if 'containers' not in self._task.args:
            return {'failed': True,
                    'msg': 'Task must have "containers" argument!'}
        containers = self._task.args.get('containers')
        if not containers:
            return {'failed': True,
                    'msg': 'Task must have non empty "containers" argument!'}
        DISPLAY.vvvv('Running for containers: %s' % str(containers))
        wrap_async = self._task.async_val and (
            not self._connection.has_native_async)
        results = [self._execute_module(
            module_name='podman_container',
            module_args=container,
            task_vars=task_vars, wrap_async=wrap_async
        ) for container in containers]

        changed = any([i.get('changed', False) for i in results])
        skipped = all([i.get('skipped', False) for i in results])
        failed = any([i.get('failed', False) for i in results])

        try:
            if not wrap_async:
                # remove a temporary path we created
                self._remove_tmp_path(self._connection._shell.tmpdir)
        except Exception:
            pass
        finally:
            if skipped:
                return {'results': results,
                        'changed': False,
                        'skipped': skipped}
            if failed:
                msg = "\n".join([i.get('msg', '') for i in results])
                return {'results': results,
                        'changed': changed,
                        'failed': failed,
                        'msg': msg}
            return {'results': results,
                    'changed': changed,
                    'failed': False,
                    'msg': 'All items completed'}
