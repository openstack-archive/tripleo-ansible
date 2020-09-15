from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import collections
import time

from ansible import constants as C
from ansible.plugins.callback import CallbackBase
from datetime import datetime
from datetime import timedelta

DOCUMENTATION = '''
    callback: tripleo_profile_tasks
    type: aggregate
    short_description: adds time information to tasks
    version_added: "2.9"
    description:
      - Based on upstream profile_tasks but formatted for tripleo_dense
    requirements:
      - whitelisting in configuration - see examples section below for details.
    options:
      output_limit:
        description: Number of tasks to display in the summary
        default: 20
        env:
          - name: PROFILE_TASKS_TASK_OUTPUT_LIMIT
        ini:
          - section: callback_profile_tasks
            key: task_output_limit
      sort_order:
        description: Adjust the sorting output of summary tasks
        choices: ['descending', 'ascending', 'none']
        default: 'descending'
        env:
          - name: PROFILE_TASKS_SORT_ORDER
        ini:
          - section: callback_profile_tasks
            key: sort_order
'''


class CallbackModule(CallbackBase):

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'tripleo_profile_tasks'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        self.stats = collections.OrderedDict()
        self.current = None
        self.sort_order = None
        self.task_output_limit = None
        self.start_time = time.time()
        super(CallbackModule, self).__init__()

    def set_options(self, task_keys=None, var_options=None, direct=None):
        super(CallbackModule, self).set_options(task_keys=task_keys,
                                                var_options=var_options,
                                                direct=direct)

        self.sort_order = self.get_option('sort_order')
        if self.sort_order is not None:
            if self.sort_order == 'ascending':
                self.sort_order = False
            elif self.sort_order == 'descending':
                self.sort_order = True
            elif self.sort_order == 'none':
                self.sort_order = None

        self.task_output_limit = self.get_option('output_limit')
        if self.task_output_limit is not None:
            if self.task_output_limit == 'all':
                self.task_output_limit = None
            else:
                self.task_output_limit = int(self.task_output_limit)

    def _timestamp(self):
        if self.current is None:
            return
        self.stats[self.current]['time'] = (
            time.time() - self.stats[self.current]['time']
        )

    def _output(self, msg, color=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        if isinstance(msg, list):
            output = ' | '.join([timestamp] + msg)
        else:
            output = timestamp + ' | ' + msg
        self._display.display(output, color=color)

    def _output_previous_timings(self, uuid):
        # no previous timing because uuid was null
        if not uuid:
            return
        line = [
            uuid,
            u'{:>10}'.format('TIMING'),
            self.stats[uuid].get('name', 'NONAME'),
            str(timedelta(seconds=(time.time() - self.start_time))),
            u'{0:.02f}s'.format(self.stats[uuid].get('time', '-1'))
        ]
        self._output(line, C.COLOR_DEBUG)

    def _record_task(self, task):
        self._timestamp()
        self._output_previous_timings(self.current)
        self.current = task._uuid
        self.stats[self.current] = {'time': time.time(),
                                    'name': task.get_name()}
        if self._display.verbosity >= 2:
            self.stats[self.current]['path'] = task.get_path()

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._record_task(task)

    def v2_playbook_on_handler_task_start(self, task):
        self._record_task(task)

    def playbook_on_stats(self, stats):
        self._timestamp()
        self.current = None
        results = self.stats.items()
        # Sort the tasks by the specified sort
        if self.sort_order is not None:
            results = sorted(
                self.stats.items(),
                key=lambda x: x[1]['time'],
                reverse=self.sort_order,
            )
        results = results[:self.task_output_limit]

        self._output('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
                     ' Summary Information '
                     '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        self._output(
            '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
            ' Elapsed Time: {} '
            '~~~~~~~~~~~~~~~~~~~~~~~~~~~~'.format(
                str(timedelta(seconds=(time.time() - self.start_time)))))

        header = [
            '{:>36}'.format('UUID'),
            '{:>10}'.format('Info'),
            '{}'.format('Task Name'),
            '{:>10}'.format('Run Time'),
        ]
        self._output(' | '.join(header))

        for uuid, result in results:
            line = [
                uuid,
                u'{:>10}'.format('SUMMARY'),
                result['name'],
                u'{0:.02f}s'.format(result['time'])
            ]
            self._output(' | '.join(line))
