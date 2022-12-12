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

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_text
from ansible.playbook.included_file import IncludedFile
from ansible.plugins.loader import action_loader
from ansible.plugins.strategy import StrategyBase
from ansible.utils.display import Display

DOCUMENTATION = '''
    strategy: tripleo_base
    short_description: Base tripleo strategy shared with linear & free
    description:
    version_added: "2.9"
    author: Alex Schultz <aschultz@redhat.com>
'''

display = Display()


class TripleoBase(StrategyBase):

    def __init__(self, *args, **kwargs):
        super(TripleoBase, self).__init__(*args, **kwargs)
        self._any_errors_fatal = False
        self._callback_sent = False
        self._has_work = False
        self._host_pinned = False
        self._hosts_left = []
        self._iterator = None
        self._play_context = None
        self._strat_results = []
        self.noop_task = None
        self._fail_cache = {}
        # these were defined in 2.9
        self._has_hosts_cache = False
        self._has_hosts_cache_all = False

    def _print(self, msg, host=None, level=1):
        # host needs to be a string or bad things happen. LP#1904917
        if host and not isinstance(host, str):
            host = None
        display.verbose(msg, host=host, caplevel=level)

    def _debug(self, msg, host=None):
        self._print(msg, host, 3)

    def _get_action(self, task):
        """Get action based on task"""
        self._debug('_get_action...')
        try:
            action = action_loader.get(task.action, class_only=True)
        except KeyError:
            action = None
        return action

    def _send_task_callback(self, task, templar):
        """Send a task callback for task start"""
        self._debug('_send_task_callback...')
        if self._callback_sent:
            return
        name = task.name
        try:
            task.name = to_text(templar.template(task.name,
                                                 fail_on_undefined=False),
                                nonstring='empty')
        except Exception:
            self._debug('templating failed')
        self._tqm.send_callback('v2_playbook_on_task_start',
                                task,
                                is_conditional=False)
        task.name = name
        self._callback_sent = True

    def _get_fail_percent(self, host):
        """Return maximum percentage failure per role"""
        if host and host in self._fail_cache:
            return self._fail_cache[host]

        fail_vars = self._variable_manager.get_vars(play=self._iterator._play,
                                                    host=host,
                                                    task=None)
        percent = fail_vars.get('max_fail_percentage', 0)
        role = fail_vars.get('tripleo_role_name', 'default')
        self._fail_cache[host] = (percent, role)
        return (percent, role)

    def _check_fail_percent(self, host, current_failures):
        """Check if max fail pourcentage was reached

       When a failure occurs for a host, check if we reached
       the max percentage of failure for the group in which
       the host is part from.
       """
        percent, role = self._get_fail_percent(host)
        current_failed = current_failures.get(role, 1)

        groups = self._inventory.get_groups_dict()
        group_count = len(groups.get(role, []))
        if group_count == 0:
            return True
        failed_percent = (current_failed / group_count) * 100
        if failed_percent > percent:
            return True
        return False

    def _get_current_failures(self):
        """Return the number of failures per role"""
        failures = {}
        for host, _ in self._iterator.get_failed_hosts().items():
            host_obj = self._inventory.get_host(host)
            per, role = self._get_fail_percent(host_obj)
            if role in failures:
                failures[role] += 1
            else:
                failures[role] = 1
        return failures

    def _get_task_attr(self, task, name):
        # Ansible < 2.14 replaced _valid_attrs by FieldAttributes
        # https://github.com/ansible/ansible/pull/73908
        if hasattr(task, 'fattributes'):
            return task.fattributes.get(name)
        return task._valid_attrs[name]

    def _get_task_errors_fatal(self, task, templar):
        """Return parsed any_errors_fatal from a task"""
        return task.get_validated_value(
            'any_errors_fatal',
            self._get_task_attr(task, 'any_errors_fatal'),
            templar.template(task.any_errors_fatal),
            None)

    def process_includes(self, host_results, noop=False):
        """Handle includes

        This function processes includes and adds them tasks to the hosts.
        It will return False if there was a failure during the include
        """
        self._debug('process_includes...')
        include_files = IncludedFile.process_include_results(
                host_results,
                iterator=self._iterator,
                loader=self._loader,
                variable_manager=self._variable_manager
        )

        include_success = True
        if len(include_files) == 0:
            self._debug('No include files')
            return include_success

        all_blocks = dict((host, []) for host in self._hosts_left)
        for include in include_files:
            self._debug('Adding include...{}'.format(include))
            try:
                if include._is_role:
                    ir = self._copy_included_file(include)
                    new_blocks, handler_blocks = ir.get_block_list(
                        play=self._iterator._play,
                        variable_manager=self._variable_manager,
                        loader=self._loader)
                else:
                    new_blocks = self._load_included_file(
                        include, iterator=self._iterator)
                for block in new_blocks:
                    vars_params = {'play': self._iterator._play,
                                   'task': block._parent}
                    # ansible <2.9 compatibility
                    if self._has_hosts_cache:
                        vars_params['_hosts'] = self._hosts_cache
                    if self._has_hosts_cache_all:
                        vars_params['_hosts_all'] = self._hosts_cache_all

                    task_vars = self._variable_manager.get_vars(**vars_params)
                    final_block = block.filter_tagged_tasks(task_vars)

                    for host in self._hosts_left:
                        if host in include._hosts:
                            all_blocks[host].append(final_block)
            except AnsibleError as e:
                for host in include._hosts:
                    self._tqm._failed_hosts[host.get_name()] = True
                    self._iterator.mark_host_failed(host)
                display.error(to_text(e), wrap_text=False)
                include_success = False
                continue

        for host in self._hosts_left:
            self._iterator.add_tasks(host, all_blocks[host])

        return include_success
