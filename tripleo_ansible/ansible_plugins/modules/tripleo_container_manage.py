#!/usr/bin/python3
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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.parsing.convert_bool import boolean

import glob
import os
import time
import yaml
import json

from concurrent.futures import ThreadPoolExecutor

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: tripleo_container_manage
author:
  - "Alex Schultz (@mwhahaha)"
version_added: '2.9'
short_description: Create containers from a set of json configurations
notes: []
description:
  - Generate puppet containers configs
requirements:
  - None
options:
  config_id:
    description:
      - Config id for the label
    type: str
    required: True
  config_dir:
    description:
      - Path to the json container definitions
    type: str
    required: True
  config_patterns:
    description:
      - Glob for configuration files
    type: str
    default: "*.json"
  config_overrides:
    description:
      - Allows to override any container configuration which will take
        precedence over the JSON files.
    default: {}
    required: False
    type: dict
  log_base_path:
    description:
      - Log base path directory
    type: str
    default: '/var/log/containers/stdouts'
  concurrency:
    description:
      - Number of podman actions to run at the same time
    type: int
    default: 1
  debug:
    description:
      - Enable debug
    type: bool
    default: False
"""

EXAMPLES = """
- name: Run containers
  tripleo_container_manage
    config_id: tripleo_step1
    config_dir: /var/lib/tripleo-config/container-startup-config/step_1
"""


from ansible_collections.containers.podman.plugins.module_utils.podman.podman_container_lib import PodmanManager, ARGUMENTS_SPEC_CONTAINER  # noqa: F402


class ExecFailure(Exception):
    def __init__(self, msg, stdout=None, stderr=None):
        super().__init__(msg)
        self.msg = msg
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return f"ERROR: {self.msg}\nstderr: {self.stderr}"


class TripleoContainerManage:
    """Notes about this module.

    It will generate container config that will be consumed by the
    tripleo-container-manage role that is using podman_container module.
    """

    def __init__(self, module, results):
        self.module = module
        self.results = results

        # parse args
        args = self.module.params

        # Set parameters
        self.concurrency = args.get('concurrency', 4)
        self.config_id = args.get('config_id')
        self.config_dir = args.get('config_dir')
        self.config_patterns = args.get('config_patterns')
        self.config_overrides = args['config_overrides']
        self.log_base_path = args.get('log_base_path')
        self.debug = args.get('debug')

        self.run()

        self.module.exit_json(**self.results)

    # container_config_data.py without overrides
    def _get_configs(self):
        configs = {}
        if not os.path.exists(self.config_dir):
            self.module.warn('Configuration directory does not exist '
                             f'{self.config_dir}')
            return configs

        matches = glob.glob(os.path.join(self.config_dir,
                                         self.config_patterns))
        for match in matches:
            name = os.path.splitext(os.path.basename(match))[0]
            with open(match, 'r') as data:
                config = json.loads(data.read())
            if self.debug:
                self.module.debug(f'Config found for {name}: {config}')
            configs.update({name: config})

        # handle overrides similar to container_config_data
        if self.config_overrides:
            for k in self.config_overrides.keys():
                if k in configs:
                    for mk, mv in self.config_overrides[k].items():
                        if self.debug:
                            self.module.debug(f'Override found for {k}: {mk} '
                                              f'will be set to {mv}')
                        configs[k][mk] = mv
        return configs

    def _get_version(self):
        rc, out, err = self.module.run_command(['podman', b'--version'])
        if rc != 0 or not out or 'version' not in out:
            self.module.fail_json(msg='Can not determine podman version')
        return out.split('versio')[1].strip()

    def _container_opts_defaults(self):
        default = {}
        opts = ARGUMENTS_SPEC_CONTAINER
        for k, v in opts.items():
            if 'default' in v:
                default[k] = v['default']
            else:
                default[k] = None
        return default

    def _container_opts_update(self, container_opts):
        opts_dict = self._container_opts_defaults()
        aliases = {}
        for k, v in ARGUMENTS_SPEC_CONTAINER.items():
            if 'aliases' in v:
                for alias in v['aliases']:
                    aliases[alias] = k
        for k in list(container_opts):
            if k in aliases:
                key = aliases[k]
                opts_dict[key] = container_opts[k]
                container_opts.pop(k)
        opts_dict.update(container_opts)
        return opts_dict

    def _container_opts_types(self, container_opts):
        # convert data types since magic ansible option conversion doesn't
        # occur here.
        for k, v in container_opts.items():
            if v is None:
                continue
            if ARGUMENTS_SPEC_CONTAINER.get(k) is None:
                if self.debug:
                    self.module.debug(f"Container opt '{k}' is unknown")
                continue
            opt_type = ARGUMENTS_SPEC_CONTAINER.get(k).get('type')
            if opt_type in ['raw', 'path']:
                continue
            if not isinstance(v, eval(opt_type)):
                if isinstance(v, str) and opt_type == 'list':
                    container_opts[k] = [v]
                elif isinstance(v, str) and opt_type == 'bool':
                    container_opts[k] = boolean(v)
                elif isinstance(v, str) and opt_type == 'int':
                    container_opts[k] = int(v)
                elif isinstance(v, int) and opt_type == 'str':
                    container_opts[k] = str(v)
                else:
                    raise TypeError(f"Container {container_opts['name']} "
                                    f"option ({k}, {v}) is not "
                                    f"type {opt_type} is {type(v)}")
        return container_opts

    def _list_or_dict_arg(self, data, cmd, key, arg):
        """Utility to build a command and its argument with list or dict data.

        The key can be a dictionary or a list, the returned arguments will be
        a list where each item is the argument name and the item data.
        """
        if key not in data:
            return
        value = data[key]
        if isinstance(value, dict):
            for k, v in sorted(value.items()):
                if v:
                    cmd.append(f'{arg}={k}={v}')
                elif k:
                    cmd.append(f'{arg}={k}')
        elif isinstance(value, list):
            for v in value:
                if v:
                    cmd.append(f'{arg}={v}')

    def check_running_container(self, name, retries=10):
        count = 0
        running = False
        while not running and count < retries:
            cmd = ['podman', 'inspect', name]
            rc, out, err = self.module.run_command(cmd)
            if rc == 0:
                data = json.loads(out)[0]
                running = data.get('State', {}).get('Running', False)
                if running:
                    return True
            self.module.debug(f"{name} is not running, waiting...")
            count = count + 1
            time.sleep(6)
        return False

    def exec_container(self, name, config):
        # check to see if the container we're going to exec into is running
        target_container = config['command'][0]
        if not self.check_running_container(target_container):
            msg = f"Cannot run {name} because target container is not running {target_container}"
            self.module.warn(msg)
            return False

        cmd = ['podman', 'exec', f"--user={config.get('user', 'root')}"]
        if 'privileged' in config:
            cmd.append('--privileged=%s' % str(config['privileged']).lower())
        self._list_or_dict_arg(config, cmd, 'environment', '--env')
        cmd.extend(config['command'])
        rc, out, err = self.module.run_command(cmd)
        if rc != 0:
            msg = f"Failure running exec '{name}'. rc={rc}, stdout={out}, stderr={err}"
            self.module.warn(msg)
            return False
        return True

    def manage_container(self, name, config):
        opts = {
            'name': name,
            'state': "started",
            'label': {
                'config_id': self.config_id,
                'container_name': name,
                'managed_by': 'tripleo_ansible',
                'config_data': config
            },
            'conmon_pidfile': f"/run/{name}.pid",
            'debug': self.debug,
            'log_driver': 'k8s-file',
            'log_level': 'info',
            'log_opt': {"path": f"{self.log_base_path}/{name}.log"},
        }
        opts.update(config)
        # do horible things to convert THT format to ansible module format
        if 'volumes' in opts:
            opts['volume'] = opts.pop('volumes')
        if 'environment' in opts:
            opts['env'] = opts.pop('environment')
        if 'healthcheck' in opts and isinstance(opts['healthcheck'], dict):
            opts['healthcheck'] = opts['healthcheck'].get('test', None)
        if 'check_interval' in opts:
            opts['healthcheck_interval'] = opts.pop('check_interval')
        if 'remove' in opts:
            opts['rm'] = opts.pop('remove')
        if 'restart' in opts:
            # NOTE(mwhahaha): converation from tripleo format to podman as
            # systemd handles this restart config
            opts['restart'] = False
        if 'stop_grace_period' in opts:
            opts['stop_timeout'] = opts.pop('stop_grace_period')

        success = True
        try:
            container_opts = self._container_opts_update(opts)
            container_opts = self._container_opts_types(container_opts)
            PodmanManager(self.module, container_opts).execute()
        except ExecFailure as e:
            print(e)
            self.module.warn(str(e))
            success = False
        return success

    def run_container(self, data):
        name, config = data
        action = config.get('action', 'create')
        retries = config.pop('retries', 0)
        retry_sleep = config.pop('retry_sleep', 30)

        success = False
        while True:
            if action == 'exec':
                success = self.exec_container(name, config)
            else:
                success = self.manage_container(name, config)

            if success or retries <= 0:
                break
            else:
                self.module.warn(f'Remaining retries for {name}: {retries}')
                retries -= 1
                time.sleep(retry_sleep)

        return (name, success)

    def check_failures(self, results):
        failed = []
        for result in results:
            name, res = result
            if not res:
                failed.append(name)
        return failed

    def batch_start_order(self, configs):
        data = {}
        for k in configs:
            start_order = configs[k].get('start_order', 0)
            if start_order not in data:
                data[start_order] = []
            data[start_order].append((k, configs.get(k)))
        return data

    def run(self):
        configs = self._get_configs()
        # sort configs by start_order
        # launch containers?
        data = self.batch_start_order(configs)
        failed = []

        def exe_fail_json(**kwargs):
            raise ExecFailure(**kwargs)

        # NOTE: fix because PodmanManager calls fail_json directly so we want
        # to handle those all at once at the end
        orig_fail = self.module.fail_json
        self.module.fail_json = exe_fail_json
        # loop through keys sorted
        for start_order in sorted(data.keys()):
            with ThreadPoolExecutor(max_workers=self.concurrency) as exc:
                results = exc.map(self.run_container, data[start_order])
            failed.extend(self.check_failures(results))
        self.module.fail_json = orig_fail

        if len(failed) > 0:
            self.module.fail_json(
                msg=f"Failed containers: {', '.join(failed)}")
        self.results['changed'] = True


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
    )
    results = dict(
        changed=False
    )
    TripleoContainerManage(module, results)


if __name__ == '__main__':
    main()
