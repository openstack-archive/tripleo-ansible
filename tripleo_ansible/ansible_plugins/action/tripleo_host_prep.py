#!/usr/bin/env python3
# Copyright 2021 Red Hat, Inc.
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

import os
import tempfile
import yaml

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

DISPLAY = Display()

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: tripleo_host_prep
author:
  - Alex Schultz <aschultz@redhat.com>
version_added: '2.9'
short_description: Apply host prep data to a host
notes: []
description:
  - This module processes a complex hash provided to it that expresses
    users, groups, files, directories and some selinux related options that
    should applied to the host. This module leverages the existing ansible
    modules to apply the data. users (ansible.builtin.user),
    groups (ansible.builtin.group), files (ansible.builtin.copy),
    directories (ansible.builtin.file), seboolean (ansible.posix.seboolean),
    sefcontext (community.general.sefcontext).  All options exposed by these
    modules are available.
options:
  host_prep_data:
    description:
      - Dictionary containing users, groups, files, directories, etc to apply.
    required: True
    type: dict
  debug:
    description:
      - Whether or not debug is enabled.
    default: False
    required: False
    type: bool
"""

EXAMPLES = """
- name: Apply host prep
  tripleo_host_prep:
    host_prep_data:
      service_a:
        users:
          "foo":
            uid: 1233
            group: foobar
        groups:
          "foobar":
            gid: 1233
        files:
          "/var/tmp/foo/bar":
            content: |
              data
            mode: "0644"
        directories:
          "/var/tmp/foo":
            mode: "0700"
        seboolean:
          "virt_sandbox_use_netlink":
            persistent: true
            state: true
        sefcontext:
          "/var/tmp/foo(/.*)?":
            setype: container_file_t
      service_b:
        directories:
          "/var/tmp/bar":
            mode: "0750"
        files:
          "/var/tmp/bar/baz":
            content: "fizz"
            mode: "0600"
            owner: root
"""

RETURN = """
"""


class ActionModule(ActionBase):
    """Tripleo host prep module

    """

    TRANSFERS_FILES = True

    _VALID_ARGS = yaml.safe_load(DOCUMENTATION)['options']

    class PrepTaskFailure(Exception):
        """exception to stop processing"""

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

    def _get_data_type(self, data_type):
        data = {}
        for svc in self.host_prep_data.items():
            items = svc[1].get(data_type, {})
            for item in items:
                if item in data:
                    if data[item] != items[item]:
                        DISPLAY.warning(f'{item} defined multiple times with '
                                        'different settings. The first '
                                        'instance will be used.')
                    else:
                        DISPLAY.debug(f'{item} already handled, skipping')
                    continue
                data[item] = items.get(item)
        return data

    def _handle_result(self, result):
        if result.get('changed', False):
            self.changed = True
        if result.get('failed', False):
            self.fail_result = result
            raise self.PrepTaskFailure()

    def apply_groups(self, task_vars):
        """Apply groups to a system"""
        group_data = self._get_data_type('groups')
        for group in group_data:
            # create group
            args = group_data[group] or {}
            args.setdefault('name', group)
            group_result = self._execute_module(
                module_name='group',
                module_args=args,
                task_vars=task_vars
            )
            self._handle_result(group_result)

    def apply_users(self, task_vars):
        """Apply users to a system"""
        user_data = self._get_data_type('users')
        for user in user_data:
            # create user
            args = user_data[user] or {}
            args.setdefault('name', user)
            user_result = self._execute_module(
                module_name='user',
                module_args=args,
                task_vars=task_vars
            )
            self._handle_result(user_result)

    def apply_dirs(self, task_vars):
        """Create directories on a system"""
        dir_data = self._get_data_type('directories')
        for dirname in dir_data:
            # create dir
            args = dir_data[dirname] or {}
            args.setdefault('path', dirname)
            args.setdefault('state', 'directory')

            dir_result = self._execute_module(
                module_name='file',
                module_args=args,
                task_vars=task_vars
            )
            self._handle_result(dir_result)

    def apply_files(self, task_vars):
        """Copy file or file data to a remote system"""
        file_data = self._get_data_type('files')
        for filename in file_data:
            # create file
            args = file_data[filename] or {}
            args.setdefault('dest', filename)
            tempfile_path = None
            if 'content' in args:
                # copy content to the remote system
                tempfile_path = self._transfer_data(
                        remote_path=self._connection._shell.join_path(
                            self.remote_tmp,
                            next(tempfile._get_candidate_names())),
                        data=args.pop('content')
                )
            elif not args.get('remote_src', False) and 'src' in args:
                # copy the local src to the remote system
                tempfile_path = self._transfer_file(
                        local_path=args['src'],
                        remote_path=self._connection._shell.join_path(
                            self.remote_tmp,
                            next(tempfile._get_candidate_names()))
                )
            if tempfile_path:
                args['src'] = tempfile_path
                # since we already handled the copy, tell copy module it
                # is a remote src location
                args['remote_src'] = True
            try:
                # the copy module always assumes remote host, the action
                # plugin version does the copy action.
                file_result = self._execute_module(
                    module_name='copy',
                    module_args=args,
                    task_vars=task_vars
                )
                self._handle_result(file_result)
            finally:
                # do temp file cleanup
                if tempfile_path:
                    try:
                        # delete remote temp
                        self._execute_module(
                            module_name='file',
                            module_args={'path': tempfile_path,
                                         'state': 'absent'},
                            task_vars=task_vars
                        )
                    finally:
                        # delete local if exists
                        if os.path.exists(tempfile_path):
                            os.remove(tempfile_path)

    def apply_seboolean(self, task_vars):
        """Apply a list of sebooleans"""
        sebool_data = self._get_data_type('seboolean')
        for sebool in sebool_data:
            # manage seboolean
            args = sebool_data[sebool] or {}
            args.setdefault('name', sebool)
            sebool_result = self._execute_module(
                module_name='ansible.posix.seboolean',
                module_args=args,
                task_vars=task_vars
            )
            self._handle_result(sebool_result)

    def apply_sefcontext(self, task_vars):
        """Apply a list of sefcontexts"""
        sefctx_data = self._get_data_type('sefcontext')
        for sefctx in sefctx_data:
            # manage sefctx
            args = sefctx_data[sefctx] or {}
            args.setdefault('target', sefctx)
            sefctx_result = self._execute_module(
                module_name='community.general.sefcontext',
                module_args=args,
                task_vars=task_vars
            )
            self._handle_result(sefctx_result)

    def run(self, tmp=None, task_vars=None):
        self._supports_check_mode = True
        self.changed = False

        if task_vars is None:
            task_vars = dict()
        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp
        # parse args
        args = self._get_args()

        self.fail_result = None
        self.host_prep_data = args['host_prep_data']
        self.debug = args['debug']

        try:
            # create a remote temp for our usage with the files call
            self.remote_tmp = self._make_tmp_path(
                remote_user=self._play_context.remote_user
            )
            # Apply the data in a specific order
            self.apply_groups(task_vars)
            # users need groups
            self.apply_users(task_vars)
            # directories needs users/groups
            self.apply_dirs(task_vars)
            # files need directories/users/groups
            self.apply_files(task_vars)
            # selinux bits can be applied last
            self.apply_seboolean(task_vars)
            self.apply_sefcontext(task_vars)
            # update result with changed flag
            result['changed'] = self.changed
        except self.PrepTaskFailure:
            result = self.fail_result
        finally:
            if self.remote_tmp:
                self._remove_tmp_path(self.remote_tmp)
        return result
