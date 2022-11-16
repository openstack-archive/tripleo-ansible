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

import os
import time

from ansible import constants as C
from ansible.errors import AnsibleAssertionError
from ansible.executor.play_iterator import FailedStates
from ansible.executor.play_iterator import IteratingStates
from ansible.playbook.block import Block
from ansible.playbook.task import Task
from ansible.template import Templar
from ansible.utils.display import Display

try:
    import importlib.util
    BASESPEC = importlib.util.spec_from_file_location(
        'tripleo_base',
        os.path.join(os.path.dirname(__file__), 'tripleo_base.py')
    )
    BASE = importlib.util.module_from_spec(BASESPEC)
    BASESPEC.loader.exec_module(BASE)
except ImportError:
    import imp
    BASE = imp.load_source(
        'tripleo_base',
        os.path.join(os.path.dirname(__file__), 'tripleo_base.py')
    )

DOCUMENTATION = '''
    strategy: tripleo_linear
    short_description: TripleO specific linear strategy
    description:
        - Based on the 'linear' strategy from Ansible
        - Logic broken up to allow for future improvements
    version_added: "2.9"
    author: Alex Schultz <aschultz@redhat.com>
'''

display = Display()


class TripleoLinearTerminated(Exception):
    """Exception for terminated state"""
    pass


class TripleoLinearNoHostTask(Exception):
    """Exception for no host task"""
    pass


class TripleoLinearRunOnce(Exception):
    """Exception for run once"""
    pass


class StrategyModule(BASE.TripleoBase):

    def __init__(self, *args, **kwargs):
        super(StrategyModule, self).__init__(*args, **kwargs)

    def _create_noop_task(self):
        """Create noop task"""
        self._debug('_create_noop_task...')
        noop_task = Task()
        noop_task.action = 'meta'
        noop_task.args['_raw_params'] = 'noop'
        noop_task.set_loader(self._iterator._play._loader)
        return noop_task

    def _advance_hosts(self, hosts, host_tasks, cur_block, cur_state):
        """Move hosts to next task"""
        self._debug('_advance_hosts...')
        noop_task = self._create_noop_task()
        returns = []
        for host in hosts:
            host_state_task = host_tasks.get(host.name)
            if host_state_task is None:
                continue
            (s, t) = host_state_task
            self._print('task: {}'.format(t))
            s = self._iterator.get_active_state(s)
            if t is None:
                continue
            self._print('task.action: {}'.format(t.action))
            if s.run_state == cur_state and s.cur_block == cur_block:
                _ = self._iterator.get_next_task_for_host(host)
                returns.append((host, t))
            else:
                returns.append((host, noop_task))
        return returns

    def _get_next_tasks(self, hosts):
        """Get next set of tasks"""
        self._debug('_get_next_tasks...')
        host_tasks = {}
        task_counts = {}

        self._debug('populate next tasks for all hosts')
        for host in hosts:
            host_tasks[host.name] = self._iterator.get_next_task_for_host(
                host, peek=True)

        self._debug('organize tasks by state')
        host_tasks_to_run = [(host, state_task)
                             for host, state_task in host_tasks.items()
                             if state_task and state_task[1]]

        # figure out our current block
        if host_tasks_to_run:
            try:
                lowest_cur_block = min(
                    (self._iterator.get_active_state(s).cur_block
                     for h, (s, t) in host_tasks_to_run
                     if s.run_state != IteratingStates.COMPLETE))
            except ValueError:
                lowest_cur_block = None
        else:
            lowest_cur_block = None

        # build counts for tasks by run state
        for (k, v) in host_tasks_to_run:
            (s, t) = v
            s = self._iterator.get_active_state(s)
            if s.cur_block > lowest_cur_block:
                continue

            # count up tasks based on state, we only care about:
            # IteratingStates.SETUP
            # IteratingStates.TASKS
            # IteratingStates.RESCUE
            # IteratingStates.ALWAYS
            if not task_counts.get(s.run_state):
                task_counts[s.run_state] = 1
            else:
                task_counts[s.run_state] += 1

        # Iterate through the different task states we care about
        # to execute them in a specific order. If there are tasks
        # in that state, we run all those tasks and then noop the
        # rest of the hosts with tasks not currently in that state
        for state_type in [IteratingStates.SETUP,
                           IteratingStates.TASKS,
                           IteratingStates.RESCUE,
                           IteratingStates.ALWAYS]:
            if state_type in task_counts:
                return self._advance_hosts(hosts,
                                           host_tasks,
                                           lowest_cur_block,
                                           state_type)

        # all done so move on by returning None for the next task in
        # the return value.
        return [(host, None) for host in hosts]

    def _replace_with_noop(self, target):
        """Replace task with a noop task"""
        self._debug('_replace_with_noop...')
        if self.noop_task is None:
            raise AnsibleAssertionError('noop_task is None')

        result = []
        for t in target:
            if isinstance(t, Task):
                result.append(self.noop_task)
            elif isinstance(t, Block):
                result.append(self._create_noop_block_from(t, t._parent))
        return result

    def _create_noop_block_from(self, original_block, parent):
        """Create a noop block from a block"""
        self._debug('_create_noop_block_from...')
        noop_block = Block(parent_block=parent)
        noop_block.block = self._replace_with_noop(original_block.block)
        noop_block.always = self._replace_with_noop(original_block.always)
        noop_block.rescue = self._replace_with_noop(original_block.rescue)
        return noop_block

    def _prepare_and_create_noop_block_from(self, original_block, parent):
        """Create noop block"""
        self._debug('_prepare_and_create_noop_block_from...')
        self.noop_task = self._create_noop_task()
        return self._create_noop_block_from(original_block, parent)

    def _process_host_tasks(self, host, task):
        """Process host task and execute"""
        self._debug('process_host_tasks...')
        results = []

        if self._tqm._terminated:
            raise TripleoLinearTerminated()
        run_once = False

        action = self._get_action(task)

        # Skip already executed roles
        if task._role and task._role.has_run(host):
            if (task._role._metadata is None or task._role._metadata
                    and not task._role._metadata.allow_duplicates):
                raise TripleoLinearNoHostTask()

        # todo handle steps like in linear
        # build get_vars call params
        vars_params = {'play': self._iterator._play,
                       'host': host,
                       'task': task}
        # if we have >= 2.9 we can use the hosts cache
        if self._has_hosts_cache:
            vars_params['_hosts'] = self._hosts_cache
        if self._has_hosts_cache_all:
            vars_params['_hosts_all'] = self._hosts_cache_all

        task_vars = self._variable_manager.get_vars(**vars_params)

        self.add_tqm_variables(task_vars, play=self._iterator._play)
        templar = Templar(loader=self._loader, variables=task_vars)

        run_once = (templar.template(task.run_once) or action
                    and getattr(action, 'BYPASS_HOST_LOOP', False))

        if task.action == 'meta':
            results.extend(self._execute_meta(task,
                                              self._play_context,
                                              self._iterator,
                                              host))
            if (task.args.get('_raw_params', None) not in ('noop',
                                                           'reset_connection',
                                                           'end_host')):
                run_once = True
            if (self._get_task_errors_fatal(task, templar)
                    or run_once and not task.ignore_errors):
                self._any_errors_fatal = True
        else:
            self._send_task_callback(task, templar)
            self._blocked_hosts[host.get_name()] = True
            self._queue_task(host, task, task_vars, self._play_context)
            del task_vars

        if run_once:
            raise TripleoLinearRunOnce()

        max_passes = max(1, int(len(self._tqm._workers) * 0.1))
        results.extend(self._process_pending_results(
            self._iterator, max_passes=max_passes))
        return results

    def _process_failures(self):
        """Handle failures"""
        self._debug('_process_failures...')
        non_fail_states = frozenset([IteratingStates.RESCUE,
                                     IteratingStates.ALWAYS])
        result = self._tqm.RUN_OK
        for host in self._hosts_left:
            (s, _) = self._iterator.get_next_task_for_host(host, peek=True)
            s = self._iterator.get_active_state(s)
            if ((s.run_state not in non_fail_states)
                    or (s.run_state == IteratingStates.RESCUE
                        and s.fail_state & FailedStates.RESCUE != 0)):
                self._tqm._failed_hosts[host.name] = True
                result |= self._tqm.RUN_FAILED_BREAK_PLAY
        return result

    def process_work(self):
        """Run pending tasks"""
        self._debug('process_work...')
        self._callback_sent = False
        result = self._tqm.RUN_OK

        host_tasks = self._get_next_tasks(self._hosts_left)
        self._strat_results = []
        results = []
        for (host, task) in host_tasks:
            if not task:
                continue
            try:
                self._has_work = True
                results.extend(self._process_host_tasks(host, task))
            except TripleoLinearNoHostTask:
                continue
            except (TripleoLinearTerminated, TripleoLinearRunOnce):
                break
        if self._pending_results > 0:
            results.extend(self._wait_on_pending_results(
                self._iterator))

        self._strat_results.extend(results)
        self.update_active_connections(results)

        return result

    def run(self, iterator, play_context):
        """Run our straregy"""
        self._debug('run...')
        self._iterator = iterator
        self._play_context = play_context
        self._has_work = True

        result = self._tqm.RUN_OK

        # check for < 2.9 and set vars so we know if we can use hosts cache
        if getattr(self, '_set_hosts_cache', False):
            self._set_hosts_cache(self._iterator._play)
            self._has_hosts_cache = True
        if getattr(self, '_set_hosts_cache_all', False):
            self._has_hosts_cache_all = True

        while self._has_work and not self._tqm._terminated:
            self._has_work = False
            self._print('play: {}'.format(iterator._play))
            try:
                self._hosts_left = self.get_hosts_left(self._iterator)
                result = self.process_work()

                # NOTE(mwhahaha): process_includes returns a status however
                # we will pick up on these failures further down because
                # failed_hosts will be set. We don't need the status
                # in this strategy so we just ignore it.
                self.process_includes(self._strat_results, noop=True)

                failed_hosts = []
                unreachable_hosts = []
                fail_lookup = self._get_current_failures()
                for res in self._strat_results:
                    if ((res.is_failed() or res._task.action == 'meta')
                            and self._iterator.is_failed(res._host)):
                        failed_hosts.append(res._host)
                    elif res.is_unreachable():
                        unreachable_hosts.append(res._host)

                errored = False
                for host in set(failed_hosts + unreachable_hosts):
                    errored = self._check_fail_percent(host, fail_lookup)
                    if errored:
                        break
                if (errored and self._any_errors_fatal
                        and (len(failed_hosts) > 0
                             or len(unreachable_hosts) > 0)):
                    result = self._process_failures()

                failed_hosts = len(self._tqm._failed_hosts)
                hosts_left = len(self._hosts_left)
                if (result != self._tqm.RUN_OK
                        and (failed_hosts >= hosts_left)):
                    self._tqm.send_callback(
                        'v2_playbook_on_no_hosts_remaining')
                    return result
            except (IOError, EOFError) as e:
                display.warning("Exception while in task loop: {}".format(e))
                return self._tqm.RUN_UNKNOWN_ERROR

            self._debug('sleeping... {}'.format(
                C.DEFAULT_INTERNAL_POLL_INTERVAL)
            )
            time.sleep(C.DEFAULT_INTERNAL_POLL_INTERVAL)

        return super(StrategyModule, self).run(iterator, play_context, result)
