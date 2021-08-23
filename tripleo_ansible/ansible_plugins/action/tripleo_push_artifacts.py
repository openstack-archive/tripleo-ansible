#!/usr/bin/python
# Copyright 2020 Red Hat, Inc.
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

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

import os
import requests
import subprocess
import tempfile


ARTIFACTS_ANCHOR = '/var/lib/tripleo/artifacts'

DISPLAY = Display()

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: tripleo_push_artifacts
short_description: Push RPM/tar.gz artifact files from a local path
version_added: "2.9"
author: "Kevin Carter (@cloudnull)"
description:
  - Takes a set of fully qualified paths as inputs, pushes the content
    and deploys them on the remote system.
  - When installing multiple RPMs all of them will be installed using
    a single transaction with DNF. This improves performance, while
    maintaining the package ordering.
options:
  artifact_paths:
    description:
      - List of artifact full paths
    required: true
    type: list
  artifact_urls:
    description:
      - List of artifact full paths
    required: true
    type: list
'''

RETURN = """
"""

EXAMPLES = """
- name: Push artifacts
  tripleo_push_artifacts:
    artifact_paths:
    - /var/lib/tripleo/artifacts/container1/foo.rpm
    - /var/lib/tripleo/artifacts/container2/foo.tar.gz
    artifact_urls:
    - https://example.tld/packages/package.rpm
"""


class ActionModule(ActionBase):
    """Batch process artifacts."""

    def _run_module(self, module_name, module_args):
        """Execute an ansible module."""

        DISPLAY.vv('Running module name: {}'.format(module_name))

        results = self._execute_module(
            module_name=module_name,
            module_args=module_args,
            task_vars=self.task_vars_meta
        )
        DISPLAY.vv('Result {}'.format(results))

        if results.get('changed', False):
            self.changed = True

        if results.get('failed', False):
            raise AnsibleActionFail(
                'Module {} failed. Message: {}'.format(
                    module_name,
                    results.get('msg')
                )
            )

        return results

    def _get_filetype(self, filename):
        """Get file type information."""

        try:
            r = subprocess.run(
                "file -b {}".format(filename),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
        except Exception as e:
            raise Exception('Unable to determine file type: %s' & e)
        else:
            if 'RPM' in r.stdout:
                return 'rpm'
            elif 'gzip compressed data' in r.stdout:
                return 'targz'

        raise AnsibleActionFail(
            'Filename {} is an unknown type'.format(filename)
        )

    def _get_url(self, url):
        """Run file download operation."""

        path_path = os.path.join(tempfile.gettempdir(), 'artifacts')
        os.makedirs(path_path)
        package_name = os.path.join(
            path_path,
            os.path.basename(url)
        )
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(package_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return package_name

    def _transfer_files(self, filename, destination):
        """Run file transfer operation."""

        # Access to protected method is unavoidable in Ansible
        # NOTE(cloudnull): Access to private method is unavoidable in Ansible
        transferred_file = self._transfer_file(
            local_path=filename,
            remote_path=self._connection._shell.join_path(self.tmp, 'source')
        )
        self._run_module(
            module_name='copy',
            module_args=dict(
                src=transferred_file,
                dest=destination,
                _original_basename=os.path.basename(filename),
                follow=True,
            )
        )

    def deploy_rpm(self, filename):
        """Sync RPM to remote host."""

        DISPLAY.vv('Running package deployment')
        package_path = os.path.join(
            ARTIFACTS_ANCHOR,
            os.path.basename(filename)
        )
        self._run_module(
            module_name='file',
            module_args=dict(
                path=os.path.dirname(package_path),
                state='directory'
            )
        )
        self._transfer_files(filename=filename, destination=package_path)

        return package_path

    def install_rpms(self, rpms):
        """Run RPM installation."""

        DISPLAY.vv('Running package install for: {}'.format(rpms))
        self._run_module(
            module_name='dnf',
            module_args=dict(
                name=rpms
            )
        )
        for rpm in rpms:
            self._run_module(
                module_name='file',
                module_args=dict(
                    path=rpm,
                    state='absent'
                )
            )
        self.installed_artifacts.extend(
            [os.path.basename(i) for i in rpms]
        )

    def deploy_targz(self, filename):
        """Run unarchive deployment."""

        DISPLAY.vv('Running archive deployment')
        package_path = os.path.join(
            ARTIFACTS_ANCHOR,
            os.path.basename(filename)
        )
        self._run_module(
            module_name='file',
            module_args=dict(
                path=os.path.dirname(package_path),
                state='directory'
            )
        )
        self._transfer_files(filename=filename, destination=package_path)
        results = self._low_level_execute_command(
            "tar xvz -C / -f {}".format(package_path),
            executable='/bin/bash'
        )
        DISPLAY.vv('Result {}'.format(results))
        if results['rc'] > 0:
            DISPLAY.error(msg='Failed command: {}'.format(results))
            raise AnsibleActionFail(
                'Unable to perform unarchive {}.'.format(package_path)
            )
        self._run_module(
            module_name='file',
            module_args=dict(
                path=package_path,
                state='absent'
            )
        )
        self.installed_artifacts.append(os.path.basename(filename))

    def _run(self, task_vars=None):
        """Run the artifact push batcher.

        All pushed artifacts will be deployed to the inventory target.
        """

        self.changed = False
        self.installed_artifacts = list()

        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(task_vars=task_vars)

        self.task_vars_meta = task_vars

        # parse args
        download_artifacts = self._task.args.get('artifact_urls', list())
        local_artifacts = self._task.args.get('artifact_paths', list())
        if not local_artifacts and not download_artifacts:
            raise AnsibleActionFail(
                'Neither artifact_paths or artifact_urls has any value.'
                ' Check configuration and try again.'
            )

        for artifact in download_artifacts:
            local_artifacts.append(
                self._get_url(url=artifact)
            )

        rpms = list()
        for artifact in local_artifacts:
            filetype = self._get_filetype(filename=artifact)
            DISPLAY.vv(
                'Artifact type: {}, file: {}'.format(
                    filetype,
                    artifact
                )
            )
            if filetype == 'rpm':
                pushed_artifact = self.deploy_rpm(filename=artifact)
                rpms.append(pushed_artifact)
            elif filetype == 'targz':
                self.deploy_targz(filename=artifact)

        if rpms:
            self.install_rpms(rpms=rpms)

        result['changed'] = self.changed
        result['installed_artifacts'] = self.installed_artifacts

        return result

    def run(self, tmp=None, task_vars=None):
        """Begin action plugin execution."""

        del tmp  # tmp no longer has any effect

        try:
            self.tmp = self._make_tmp_path(
                remote_user=self._play_context.remote_user
            )
            return self._run(task_vars=task_vars)
        finally:
            self._remove_tmp_path(self.tmp)
