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

from ansible import constants as C
from ansible.plugins.callback.default import CallbackModule as BASE


class CallbackModule(BASE):
    def set_options(self, task_keys=None, var_options=None, direct=None):
        super(CallbackModule, self).set_options(task_keys=task_keys,
                                                var_options=var_options,
                                                direct=direct)

    def v2_runner_retry(self, result):
        task_name = result.task_name or result._task
        retry_count = result._result['retries'] - result._result['attempts']
        if (getattr(result, '_task', False)
                and (getattr(result._task, 'action', False)
                     in ['async_status'])):
            state = "WAITING FOR COMPLETION"
        else:
            state = "RETRYING"
        color = C.COLOR_DEBUG
        msg = "%s: %s (%d retries left)." % (state, task_name, retry_count)
        if self._run_is_verbose(result, verbosity=2):
            msg += "Result was: %s" % self._dump_results(result._result)
        self._display.display(msg, color=color)
