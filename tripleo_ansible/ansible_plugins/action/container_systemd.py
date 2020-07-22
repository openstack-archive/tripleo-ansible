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
import os

import tenacity
import yaml

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display


DISPLAY = Display()

DOCUMENTATION = """
module: container_systemd
author:
  - "TripleO team"
version_added: '2.9'
short_description: Create systemd files and manage services to run containers
notes: []
description:
  - Manage the systemd unit files for containers with a restart policy and
    then make sure the services are started so the containers are running.
    It takes the container config data in entry to figure out how the unit
    files will be configured. It returns a list of services that were
    restarted.
requirements:
  - None
options:
  container_config:
    description:
      - List of container configurations
    type: list
    elements: dict
  systemd_healthchecks:
    default: true
    description:
      - Whether or not we cleanup the old healthchecks with SystemD.
    type: boolean
  restart_containers:
    description:
      - List of container names to be restarted
    default: []
    type: list
  debug:
    default: false
    description:
      - Whether or not debug is enabled.
    type: boolean
"""
EXAMPLES = """
- name: Manage container systemd services
  container_systemd:
    container_config:
      - keystone:
          image: quay.io/tripleo/keystone
          restart: always
      - mysql:
          image: quay.io/tripleo/mysql
          stop_grace_period: 25
          restart: always
"""
RETURN = """
restarted:
    description: List of services that were restarted
    returned: always
    type: list
    sample:
      - tripleo_keystone.service
      - tripleo_mysql.service
"""


class ActionModule(ActionBase):
    """Class for the container_systemd action plugin.
    """

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

    def _cleanup_requires(self, container_names, task_vars):
        """Cleanup systemd requires files.

        :param container_names: List of container names.
        :param task_vars: Dictionary of Ansible task variables.
        """
        for name in container_names:
            path = "/etc/systemd/system/tripleo_{}.requires".format(name)
            if self.debug:
                DISPLAY.display('Removing {} file'.format(path))
            results = self._execute_module(
                module_name='file',
                module_args=dict(path=path, state='absent'),
                task_vars=task_vars
            )
            if results.get('changed', False):
                self.changed = True

    def _get_template(self, template):
        """Return systemd unit template data

        :param template: template file with its extension
        :returns data: Template data.
        """
        if self._task._role:
            file_path = self._task._role._role_path
        else:
            file_path = self._loader.get_basedir()
        # NOTE: if templates doesn't exist, it'll always return
        # file_path/systemd-service.j2
        # This file is required to exist from the
        # tripleo_container_manage role, as there is no
        # parameter to override it now.
        source = self._loader.path_dwim_relative(
            file_path,
            'templates',
            template
        )
        if not os.path.exists(source):
            raise AnsibleActionFail('Template {} was '
                                    'not found'.format(source))
        with open(source) as template_file:
            data = template_file.read()
        return data

    def _create_systemd_file(self, path, data, task_vars):
        sysd_file = self._execute_module(
            module_name='copy',
            module_args=dict(src=data,
                             dest=path,
                             mode='0644',
                             owner='root',
                             group='root'),
            task_vars=task_vars)
        return sysd_file

    def _manage_units(self, container_config, task_vars):
        """Create systemd units and get list of changed services

        :param container_config: List of dictionaries for container configs.
        :param task_vars: Dictionary of Ansible task variables.
        :returns changed_containers: List of containers which has a new unit.
        """
        try:
            remote_user = self._get_remote_user()
        except Exception:
            remote_user = task_vars.get('ansible_user')
            if not remote_user:
                remote_user = self._play_context.remote_user
        tmp = self._make_tmp_path(remote_user)
        unit_template = self._get_template('systemd-service.j2')
        changed_containers = []
        for container in container_config:
            for name, config in container.items():
                dest = '/etc/systemd/system/tripleo_{}.service'.format(name)
                task_vars['container_data'] = container
                unit = (self._templar.template(unit_template,
                                               preserve_trailing_newlines=True,
                                               escape_backslashes=False,
                                               convert_data=False))
                del task_vars['container_data']
                remote_data = self._transfer_data(
                    self._connection._shell.join_path(tmp, 'source'), unit)

                results = self._create_systemd_file(dest, remote_data,
                                                    task_vars)
                if results.get('changed', False):
                    changed_containers.append(name)
        if self.debug:
            DISPLAY.display('Systemd unit files were created or updated for: '
                            '{}'.format(changed_containers))
        return changed_containers

    def _manage_healthchecks(self, container_config, task_vars):
        """Create systemd healthchecks and get list of changed services

        :param container_config: List of dictionaries for container configs.
        :param task_vars: Dictionary of Ansible task variables.
        :returns changed_healthchecks: List of healthchecks which changed.
        """
        try:
            remote_user = self._get_remote_user()
        except Exception:
            remote_user = task_vars.get('ansible_user')
            if not remote_user:
                remote_user = self._play_context.remote_user
        tmp = self._make_tmp_path(remote_user)
        changed_healthchecks = []
        for container in container_config:
            for name, config in container.items():
                if 'healthcheck' not in config:
                    continue
                for t in ['service', 'timer']:
                    template = self._get_template('systemd-healthcheck-'
                                                  '{}.j2'.format(t))
                    task_vars['container_data'] = container
                    service = (
                        self._templar.template(template,
                                               preserve_trailing_newlines=True,
                                               escape_backslashes=False,
                                               convert_data=False)
                        )
                    del task_vars['container_data']
                    dest = ('/etc/systemd/system/tripleo_{}_'
                            'healthcheck.{}'.format(name, t))
                    remote_data = self._transfer_data(
                        self._connection._shell.join_path(tmp, 'source'),
                        service)

                    results = self._create_systemd_file(dest, remote_data,
                                                        task_vars)
                    if results.get('changed', False) and (
                            name not in changed_healthchecks):
                        changed_healthchecks.append(name)
        if self.debug:
            DISPLAY.display('Systemd healthcheck was created or updated for:'
                            ' {}'.format(changed_healthchecks))
        return changed_healthchecks

    def _systemd_reload(self, task_vars):
        """Reload systemd to load new units.

        :param task_vars: Dictionary of Ansible task variables.
        """
        if self.debug:
            DISPLAY.display('Running systemd daemon reload')
        results = self._execute_module(
            module_name='systemd',
            module_args=dict(daemon_reload=True),
            task_vars=task_vars
        )
        if results.get('changed', False):
            self.changed = True

    def _add_systemd_requires(self, services, task_vars):
        """Add systemd dependencies for healthchecks.

        :param services: List for service names.
        :param task_vars: Dictionary of Ansible task variables.
        """
        for name in services:
            service = 'tripleo_{}'.format(name)
            if self.debug:
                DISPLAY.display('Adding systemd dependency for '
                                '{}'.format(service))

            command = ('systemctl add-requires {}.service '.format(service)
                       + '{}_healthcheck.timer'.format(service))
            results = self._execute_module(
                module_name='command',
                module_args=dict(cmd=command),
                task_vars=task_vars
            )
            if results.get('changed', False):
                self.changed = True

    @tenacity.retry(
        reraise=True,
        stop=tenacity.stop_after_attempt(5),
        wait=tenacity.wait_fixed(5)
    )
    def _restart_service(self, name, extension, task_vars):
        """Restart a systemd service with retries and delay.

        :param name: String for service name to restart.
        :param extension: String for service to restart.
        :param task_vars: Dictionary of Ansible task variables.
        """
        tvars = copy.deepcopy(task_vars)
        results = self._execute_module(
            module_name='systemd',
            module_args=dict(state='restarted',
                             name='tripleo_{}.{}'.format(name, extension),
                             enabled=True,
                             daemon_reload=False),
            task_vars=tvars
        )
        if 'Result' in results['status']:
            if results['status']['Result'] == 'success':
                if results.get('changed', False):
                    self.changed = True
                    self.restarted.append('tripleo_{}.{}'.format(name,
                                                                 extension))
                return
        raise AnsibleActionFail('Service {} has not started yet'.format(name))

    def _restart_services(self, service_names, task_vars, extension='service'):
        """Restart systemd services.

        :param service_names: List of services to restart.
        :param extension: String for service to restart.
        :param task_vars: Dictionary of Ansible task variables.
        """
        for name in service_names:
            if self.debug:
                DISPLAY.display('Restarting systemd service for '
                                '{}'.format(name))
            self._restart_service(name, extension, task_vars)

    def _add_requires(self, services, task_vars):
        """Add systemd requires for healthchecks.

        :param services: List of services to manage.
        """
        for s in services:
            # TODO
            pass

    def run(self, tmp=None, task_vars=None):
        self.changed = False
        self.restarted = []

        if task_vars is None:
            task_vars = dict()
        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp

        # parse args
        args = self._get_args()

        container_config = args['container_config']
        restart_containers = args['restart_containers']
        self.systemd_healthchecks = args['systemd_healthchecks']
        self.debug = args['debug']

        extra_restarts = []
        for c in restart_containers:
            s_path = os.path.join('/etc/systemd/system',
                                  'tripleo_{}.service'.format(c))
            service_stat = self._execute_module(
                module_name='stat',
                module_args=dict(path=s_path),
                task_vars=task_vars
            )
            if service_stat.get('stat', {}).get('exists', False):
                if self.debug:
                    DISPLAY.display('Systemd unit file found for {}, the '
                                    'container will be restarted'.format(c))
                extra_restarts.append(c)

        container_names = []
        for container in container_config:
            for name, config in container.items():
                container_names.append(name)

        self._cleanup_requires(container_names, task_vars)

        changed_services = self._manage_units(container_config, task_vars)
        if len(changed_services) > 0:
            self._systemd_reload(task_vars)
        service_names = set(changed_services + extra_restarts)
        self._restart_services(service_names, task_vars)

        if self.systemd_healthchecks:
            healthchecks_to_restart = []
            changed_healthchecks = self._manage_healthchecks(container_config,
                                                             task_vars)
            for h in changed_healthchecks:
                healthchecks_to_restart.append(h + '_healthcheck')
            if len(healthchecks_to_restart) > 0:
                self._systemd_reload(task_vars)
            self._restart_services(healthchecks_to_restart,
                                   task_vars,
                                   extension='timer')
            self._add_systemd_requires(changed_healthchecks, task_vars)

        result['changed'] = self.changed
        result['restarted'] = self.restarted
        return result
