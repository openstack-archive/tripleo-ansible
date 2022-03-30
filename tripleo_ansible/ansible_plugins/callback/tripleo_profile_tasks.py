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
        self.tasks = {}
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

    def _get_uuid(self, item=None):
        uuid = ''

        if item and getattr(item, '_uuid', False):
            # item is a task
            uuid = item._uuid
        elif item and getattr(item, '_task', False):
            # item is a result (may not have a _task tho)
            if getattr(item._task, '_uuid', False):
                uuid = item._task._uuid
        return '{:36}'.format(uuid)

    def _get_host(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        if (getattr(result, '_host', False)
                and getattr(result._host, 'get_name', False)):
            msg = '%s' % result._host.get_name()
        elif (getattr(result, '_host', False)
                and getattr(result._host, 'name', False)):
            msg = '%s' % result._host.name
        else:
            msg = 'UNKNOWN'
        if delegated_vars:
            msg += ' -> %s' % delegated_vars['ansible_host']
        return msg

    def _output(self, msg, color=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        if isinstance(msg, list):
            output = ' | '.join([timestamp] + msg)
        else:
            output = timestamp + ' | ' + msg
        self._display.display(output, color=color)

    def _start_task(self, task, host=None):
        hostname = None
        if host:
            hostname = host.name
        k = (hostname, task._uuid)
        self.stats[k] = {'start': time.time(),
                         'total_time': 0.0}
        self.tasks[task._uuid] = task.get_name()

    def _end_task(self, result):
        uuid = self._get_uuid(result)
        host = self._get_host(result)
        k = (host, uuid)
        # the task never started, insert shrug emoji here.
        if k not in self.stats:
            self._display.vvvv('{} missing from stats'.format(k))
            return
        total_time = time.time() - self.stats[k]['start']
        self.stats[k]['total_time'] = total_time

        line = [
            uuid,
            u'{:>10}'.format('TIMING'),
            self.tasks.get(uuid, ''),
            host,
            str(timedelta(seconds=time.time() - self.start_time)),
            u'{0:.02f}s'.format(total_time)
        ]
        self._output(line, C.COLOR_DEBUG)

    def v2_runner_on_start(self, host, task):
        self._start_task(task, host)

    # task ends
    def v2_playbook_on_failed(self, result, ignore_errors=False):
        self._end_task(result)

    def v2_runner_on_ok(self, result):
        self._end_task(result)

    def v2_runner_item_on_ok(self, result):
        self._end_task(result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._end_task(result)

    def v2_runner_item_on_failed(self, result):
        self._end_task(result)

    def v2_runner_on_skipped(self, result):
        self._end_task(result)

    def v2_runner_on_unreachable(self, result):
        self._end_task(result)

    # playbook finished
    def playbook_on_stats(self, stats):
        self.current = None
        results = self.stats.items()
        # Sort the tasks by the specified sort
        if self.sort_order is not None:
            results = sorted(
                self.stats.items(),
                key=lambda x: x[1]['total_time'],
                reverse=self.sort_order,
            )
        results = results[:self.task_output_limit]

        self._output('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
                     ' Summary Information '
                     '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        self._output(
            '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
            ' Total Tasks: {:<10} '
            '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'.format(len(self.tasks)))

        self._output(
            '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
            ' Elapsed Time: {} '
            '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'.format(
                str(timedelta(seconds=(time.time() - self.start_time)))))

        header = [
            '{:>36}'.format('UUID'),
            '{:>10}'.format('Info'),
            '{:>10}'.format('Host'),
            '{:>11}'.format('Task Name'),
            '{:>10}'.format('Run Time'),
        ]
        self._output(' | '.join(header))

        for (host, uuid), result in results:
            line = [
                uuid,
                u'{:>10}'.format('SUMMARY'),
                u'{:>10}'.format(host),
                self.tasks.get(uuid, ''),
                u'{0:.02f}s'.format(result['total_time'])
            ]
            self._output(' | '.join(line))

        self._output('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
                     ' End Summary Information '
                     '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
