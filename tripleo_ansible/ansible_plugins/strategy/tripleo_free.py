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
from ansible.errors import AnsibleError
from ansible.module_utils._text import to_text
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
    strategy: tripleo_free
    short_description: TripleO specific free strategy
    description:
        - Based on the 'free' strategy from Ansible
        - Logic broken up to allow for future improvements/extending
        - Will fail playbook if any hosts have a failure during the
          execution and any_errors_fatal is true (free does not do this).
        - Should be backwards compatible for Ansible 2.8
    version_added: "2.9"
    author: Alex Schultz <aschultz@redhat.com>
'''

display = Display()


class TripleoFreeBreak(Exception):
    """Exception used to break loops"""
    pass


class TripleoFreeContinue(Exception):
    """Exception used to continue loops"""
    pass


class StrategyModule(BASE.TripleoBase):

    # this strategy handles throttling
    ALLOW_BASE_THROTTLING = False

    def __init__(self, *args, **kwargs):
        super(StrategyModule, self).__init__(*args, **kwargs)
        self._last_host = 0
        self._workers_free = 0
        self._run_once_tasks = set()

    def _filter_notified_hosts(self, notified_hosts):
        """Filter notified hosts"""
        return [host for host in notified_hosts
                if host in self._flushed_hosts and self._flushed_hosts[host]]

    def _increment_last_host(self):
        """Increment last host pointer

        If the last host pointer exceeds the number of hosts, we set it back to
        zero so we can start checking again with the first host
        """
        self._debug('_increment_last_host')
        self._last_host += 1
        self._debug('last_host is {}'.format(self._last_host))
        if self._last_host > len(self._hosts_left) - 1:
            self._debug('resetting last host')
            self._last_host = 0

    def _check_throttle(self, throttle, task):
        """Check if we should throttle"""
        if throttle > 0:
            same_task = 0
            for worker in self._workers:
                if (worker and worker.is_alive()
                        and worker._task._uuid == task._uuid):
                    same_task += 1
            if same_task >= throttle:
                return True
        return False

    def _check_failures(self, results):
        """Check results for failures

        If any errors are fatal, kill the playbook at the end of
        execution. All non-failed hosts will continue to run the
        playbook but it won't move on to the next playbook. This
        function returns True if there were failures and False if
        there are no failures.
        """
        fail_lookup = self._get_current_failures()
        if self._any_errors_fatal:
            for res in results:
                if ((res.is_failed() or res._task.action == 'meta')
                        and self._iterator.is_failed(res._host)
                        and self._check_fail_percent(res._host, fail_lookup)):
                    return True
        return False

    def _send_task_callback(self, task, templar):
        """Send task start callback"""
        self._debug('_send_task_callback...')
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

    def _advance_host(self, host, task):
        """Advance the host's task as necessary"""
        self._debug('_advance_host {}'.format(host))
        host_name = host.get_name()

        # build get_vars call params
        vars_params = {'play': self._iterator._play,
                       'host': host,
                       'task': task}
        # If we have >= 2.9 we can use the hosts cache
        if self._has_hosts_cache:
            vars_params['_hosts'] = self._hosts_cache
        if self._has_hosts_cache_all:
            vars_params['_hosts_all'] = self._hosts_cache_all

        task_vars = self._variable_manager.get_vars(**vars_params)
        self.add_tqm_variables(task_vars, play=self._iterator._play)
        templar = Templar(loader=self._loader, variables=task_vars)

        # if task has a throttle attribute, check throttle e.g. ansible > 2.9
        throttle = getattr(task, 'throttle', None)
        if throttle is not None:
            try:
                throttle = int(templar.template(throttle))
            except Exception as e:
                raise AnsibleError("Failed to throttle: {}".format(e),
                                   obj=task._df,
                                   orig_exc=e)
            if self._check_throttle(throttle, task):
                raise TripleoFreeBreak()

        # _blocked_hosts is used in the base strategy to keep track of hosts in
        # that have tasks in queue
        self._blocked_hosts[host_name] = True

        # Refetch the task without peek
        (_, task) = self._iterator.get_next_task_for_host(host)
        action = self._get_action(task)

        try:
            task.name = to_text(templar.template(task.name,
                                                 fail_on_undefined=False),
                                nonstring='empty')
        except Exception:
            display.warning('templating of task name failed', host=host_name)

        # run once doesn't work with free because we run all of them
        run_once = (templar.template(task.run_once) or action
                    and getattr(action, 'BYPASS_HOST_LOOP', False))

        if run_once:
            if action and getattr(action, 'BYPASS_HOST_LOOP', False):
                raise AnsibleError('Cannot bypass host loop with ansible_free strategy')
            else:
                display.warning("Using run_once with the tripleo_free strategy is not currently supported. "
                                "This task will still be executed for every host in the inventory list.")

        # handle role deduplication logic
        if task._role and task._role.has_run(host):
            if (task._role._metadata is None or task._role._metadata
                    and not task._role._metadata.allow_duplicates):
                del self._blocked_hosts[host_name]
                raise TripleoFreeContinue()

        if task.action == 'meta':
            self._execute_meta(task, self._play_context, self._iterator,
                               target_host=host)
            self._blocked_hosts[host_name] = False
        else:
            if not self._step or self._take_step(task, host_name):
                if self._get_task_errors_fatal(task, templar):
                    display.warning('any_errors_fatal only stops any future '
                                    'tasks running on the host that fails '
                                    'with the tripleo_free strategy.')
                    self._any_errors_fatal = True
                self._send_task_callback(task, templar)
                self._queue_task(host, task, task_vars, self._play_context)
                self._workers_free -= 1
                del task_vars
        return True

    def process_work(self):
        """Run pending tasks"""
        self._debug('process_work....')
        result = self._tqm.RUN_OK
        start_host = self._last_host
        self._strat_results = []
        while True:
            self._debug('process_work loop')
            host = self._hosts_left[self._last_host]
            host_name = host.get_name()

            self._increment_last_host()

            (s, t) = self._iterator.get_next_task_for_host(host, peek=True)
            self._print("host: {}, task: {}".format(host, t))

            if host_name not in self._tqm._unreachable_hosts and t:
                self._debug('{} has work to do, has_work = True'.format(
                    host_name))
                self._has_work = True
                if not self._blocked_hosts.get(host_name, False):
                    try:
                        self._advance_host(host, t)
                    except TripleoFreeBreak:
                        break
                    except TripleoFreeContinue:
                        continue
                else:
                    self._print('{} still blocked'.format(host_name))
            else:
                self._debug('{} is unreachable or no task'.format(host_name))

            # handle host pinned by going back to the start and waiting
            # for the next free host
            if (self._host_pinned and self._workers_free == 0
                    and self._has_work):
                self._last_host = start_host

            if self._last_host == start_host:
                self._debug('We hit the start host, break our loop')
                break

        self._debug('pending results....')
        results = self._process_pending_results(self._iterator)
        self._debug('results: {}'.format(results))
        self._strat_results.extend(results)

        if self._check_failures(results):
            # NOTE(mwhahaha): this is the bit of code that the upstream free
            # does not do
            result |= self._tqm.RUN_FAILED_BREAK_PLAY

        self._workers_free += len(results)
        self._debug('update connections....')
        self.update_active_connections(results)

        return result

    def run(self, iterator, play_context):
        """Run out strategy"""
        self._iterator = iterator
        self._play_context = play_context
        self._has_work = True
        self._workers_free = len(self._workers)

        result = self._tqm.RUN_OK

        # check for < 2.9 and set vars so we know if we can use hosts cache
        if getattr(self, '_set_hosts_cache', False):
            self._set_hosts_cache(self._iterator._play)
            self._has_hosts_cache = True
        if getattr(self, '_set_hosts_cache_all', False):
            self._has_hosts_cache_all = True

        # while we still have tasks and ansible is still running
        while self._has_work and not self._tqm._terminated:
            self._has_work = False
            self._debug('play: {}'.format(self._iterator._play))
            try:
                # get the hosts with tasks
                self._hosts_left = self.get_hosts_left(self._iterator)
                if len(self._hosts_left) == 0:
                    self._tqm.send_callback(
                        'v2_playbook_on_no_hosts_remaining')
                    # check if we previously had an error...
                    if result == self._tqm.RUN_OK:
                        # by setting this to false, the parent run function
                        # will determine if the run was ok based on a check
                        # of the unreachable/failed hosts.
                        result = False
                    break
                # do work
                result |= self.process_work()
                # handle includes
                include_result = self.process_includes(self._strat_results)
                if self._any_errors_fatal and not include_result:
                    # NOTE(mwhahaha): This bit of code fails the playbook if
                    # an include fails. Upstream free does not have this today
                    display.error('An include failure occurred, we will not '
                                  'continue to process after this play '
                                  'completes.')
                    result |= self._tqm.RUN_FAILED_BREAK_PLAY
            except (IOError, EOFError) as e:
                display.error("Exception while running task loop: "
                              "{}".format(e))
                return self._tqm.RUN_UNKNOWN_ERROR

            self._debug('sleeping... {}'.format(
                C.DEFAULT_INTERNAL_POLL_INTERVAL)
            )
            time.sleep(C.DEFAULT_INTERNAL_POLL_INTERVAL)

        # wait for any pending results
        _ = self._wait_on_pending_results(iterator)

        # call parent run to handle status
        return super(StrategyModule, self).run(self._iterator,
                                               self._play_context,
                                               result)
