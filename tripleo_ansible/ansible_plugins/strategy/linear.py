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

import copy
import imp
import os

import ansible.plugins.strategy as strategy
LINEAR = imp.load_source(
    'linear',
    os.path.join(os.path.dirname(strategy.__file__), 'linear.py')
)


class StrategyModule(LINEAR.StrategyModule):
    """Notes about this strategy optimization.

    To improve execution speed, if a task has a conditional attached to
    it, it will be evaluated server side, before queuing.
    """

    def __init__(self, *args, **kwargs):
        self.hostvars = {}
        self.host_role_cache = {}
        super(StrategyModule, self).__init__(*args, **kwargs)

    def _check_when(self, host, task, task_vars):
        """Evaluate if a task is to be executed.

        :param host: object
        :param task: object
        :param task_vars: dict
        :retruns: boolean
        """
        try:
            conditional = task.evaluate_conditional(
                LINEAR.Templar(
                    loader=self._loader,
                    variables=task_vars
                ),
                task_vars
            )
            if not conditional:
                LINEAR.display.verbose(
                    u'Task "{}" has been omitted from the job because the'
                    u' conditional "{}" was evaluated as "{}"'.format(
                        task.name or None,
                        task.when,
                        conditional
                    ),
                    host=host,
                    caplevel=3
                )
                return False
        except Exception:
            return True
        else:
            return True

    def _get_next_task_lockstep(self, hosts, iterator):
        host_tasks = super(StrategyModule, self)._get_next_task_lockstep(
            hosts, iterator)

        # If no tasks were returned at all, just return
        if not host_tasks:
            return host_tasks

        new_host_tasks = []
        role_when_cache = {}

        LINEAR.display.vv("\n")

        for h, t in host_tasks:
            LINEAR.display.vv(
                "skip_once_per_role: "
                "Checking host {} for task {}".format(
                h.name, t and t.name or "None"))
            task_vars = {}
            # task is None, assume all others are as well return the original list
            if t is None:
                LINEAR.display.vv(
                    "  skip_once_per_role: "
                    "task is None, returning host_tasks")
                return host_tasks
            # task is meta, always append it to the new list
            elif t.action == 'meta':
                # Use vvv here as this gets logged a lot
                LINEAR.display.vvv(
                    "  skip_once_per_role: "
                    "task is meta, appending")
                # We can't just return host_tasks here, as the task list could
                # be a mix of meta (noop) tasks and real tasks, depending on
                # what hosts the task is set to run for. We need to continue
                # checking the rest of the tasks.
                new_host_tasks.append((h, t))
                continue
            # task has no when argument, append it to the new list
            elif not t.when:
                LINEAR.display.vv(
                    "  skip_once_per_role: "
                    "task has no when, appending")
                new_host_tasks.append((h, t))
                continue
            # task has a when argument, but also a register argument, append it
            # to the new list
            elif t.when and t.register:
                LINEAR.display.vv(
                    "  skip_once_per_role: "
                    "task has when and register, appending")
                new_host_tasks.append((h, t))
                continue

            # Check if this host's role is already in the cache
            role = self.host_role_cache.get(h.name, '')

            # Check if the host belongs to an inventory group that has the
            # same name as one of the roles we have already seen.
            # If so, assume that is the host's role, and add it to the
            # cache.
            if not role:
                group_names = [g.name for g in h.groups]
                for r in set(self.host_role_cache.values()):
                    if r in group_names:
                        role = r
                        self.host_role_cache[h.name] = role
                        break

            # Still no role was found, attempt to look it up using
            # hostvars.
            if not role:
                if not self.hostvars:
                    if not task_vars:
                        task_vars = self._variable_manager.get_vars(play=iterator._play, host=h, task=t)
                    self.hostvars = task_vars['hostvars']
                role = self.hostvars[h.name].get('tripleo_role_name', '')
                self.host_role_cache[h.name] = role

            LINEAR.display.vv(
                "  skip_once_per_role: "
                "host {} has role {}".format(h.name, role))
            # role was found, it's in role_when_cache, and the value is True,
            # append it to the new list.
            if role and role in role_when_cache:
                if role_when_cache[role]:
                    LINEAR.display.vv(
                        "  skip_once_per_role: "
                        "task when is True from cache, "
                        "appending")
                    new_host_tasks.append((h, t))
                else:
                    LINEAR.display.vv(
                        "  skip_once_per_role: "
                        "task when is False from cache, "
                        "skipping")
            # role is not in the role_when_cache, check the when statement, add
            # the result to the cache, and if True, append the task to the new list
            elif role:
                if not task_vars:
                    task_vars = self._variable_manager.get_vars(play=iterator._play, host=h, task=t)
                if self._check_when(h, t, task_vars):
                    LINEAR.display.vv(
                        "  skip_once_per_role: "
                        "task when evaluated to True, "
                        "appending")
                    new_host_tasks.append((h, t))
                    role_when_cache[role] = True
                else:
                    LINEAR.display.vv(
                        "  skip_once_per_role: "
                        "task when evaluated to False, "
                        "skipping")
                    role_when_cache[role] = False
            # role was never found, just append the task to the new list
            else:
                LINEAR.display.vv(
                    "  skip_once_per_role: "
                    "host {} role not found, "
                    "appending".format(h.name))
                new_host_tasks.append((h, t))

        # can't return an empty list of tasks, or ansible assumes the PLAY is
        # done. As all tasks may have been removed, we need to add at least one
        # back if the new list is empty.
        if not new_host_tasks:
            LINEAR.display.vv(
                "  skip_once_per_role: "
                "empty host_tasks, "
                "appending last seen task")
            new_host_tasks.append((h, t))

        return new_host_tasks
