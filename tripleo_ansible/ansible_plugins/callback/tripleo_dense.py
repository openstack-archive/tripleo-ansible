__metaclass__ = type

import uuid

from ansible import constants as C
from ansible.playbook.task_include import TaskInclude
from ansible.plugins.callback.default import CallbackModule as DefaultCallback
from datetime import datetime


DOCUMENTATION = """
    name: tripleo_dense
    type: stdout
    short_description: default TripleO screen output
    version_added: historical
    description:
      - This is the default output callback for TripleO.
    extends_documentation_fragment:
      - default_callback
    requirements:
      - set as stdout in configuration
"""


class CallbackModule(DefaultCallback):
    def get_options(self, option_string):
        pass

    def _output(self, msg, color=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        if isinstance(msg, list):
            output = ' | '.join([timestamp] + msg)
        else:
            output = timestamp + ' | ' + msg
        self._display.display(output, color=color)

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

    def _get_task_name(self, item=None):
        name = ''
        if item and getattr(item, 'name', False):
            # item is a task
            name = item.name
        elif item and getattr(item, 'task_name', False):
            name = item.task_name
        elif item and getattr(item, '_task', False):
            name = item._task.name
        return name

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

    def _get_state(self, state):
        return '{:>10}'.format(state)

    # TODO(mwhahaha): can this work for fatal/skipped/etc?
    def _get_item_line(self, result, item=False):
        line = [
            self._get_uuid(result)
        ]
        host_str = self._get_host(result=result)

        if (getattr(result, '_result', False)
                and result._result.get('changed', False)):
            line.append(self._get_state('CHANGED')),
            line.append(self._get_task_name(result))
            line.append(host_str)
            color = C.COLOR_CHANGED
        else:
            if not self.get_option('display_ok_hosts'):
                return (None, None)
            line.append(self._get_state('OK'))
            line.append(self._get_task_name(result))
            line.append(host_str)
            color = C.COLOR_OK
        if item:
            item_result = self._get_item_label(result._result)
            # don't display if None
            if item_result:
                line.append('item=%s' % item_result)
        return (line, color)

    def _handle_warnings(self, result):
        if not C.ACTION_WARNINGS:
            return
        if result.get('warnings', False):
            line = [
                self._get_uuid(result),
                self._get_state('WARNING')
            ]
            color = C.COLOR_WARN
            for warn in result['warnings']:
                msg = line + [warn]
                self._output(msg, color)
            del result['warnings']
        if result.get('deprecations', False):
            line = [
                self._get_uuid(result),
                self._get_state('DEPRECATED')
            ]
            color = C.COLOR_DEPRECATE
            # TODO(mwhahaha): handle deps correctly as they are a dict
            for dep in result['deprecations']:
                msg = line + [dep['msg']]
                self._output(msg, color)
            del result['deprecations']

    def _task_line(self, task, state, color=None):
        if not task.name:
            return
        line = [
            self._get_uuid(task),
            self._get_state(state),
            self._get_task_name(task)
        ]
        self._output(line, color)

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._task_line(task, 'TASK')

    def v2_playbook_on_handler_task_start(self, task):
        self._task_line(task, 'HANDLER')

    def v2_playbook_on_cleanup_task_start(self, task):
        self._task_line(task, 'CLEANUP')

    # TODO(mwhahaha): Push fix into default for broken version of this
    # function because get_option doesn't work when k is not in _plugin_options
    def v2_runner_on_start(self, host, task):
        if ('show_per_host_start' in self._plugin_options
                and self.get_options('show_per_host_start')):
            color = C.COLOR_HIGHLIGHT
            line = [
                self._get_uuid(task),
                self._get_state('START'),
                self._get_task_name(task=task),
                host.name
            ]
            self._output(line, color)

    def v2_runner_item_on_ok(self, result):
        if isinstance(result._task, TaskInclude):
            return
        (line, color) = self._get_item_line(result, item=True)
        if not line:
            return
        self._handle_warnings(result._result)
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            if self._run_is_verbose(result):
                line.append('result=%s' % self._dump_results(result._result))
            self._output(line, color)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._clean_results(result._result, result._task.action)
        # TODO(mwhahaha): implement this one
        self._handle_exception(result._result)
        self._handle_warnings(result._result)
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            if ignore_errors:
                status = 'IGNORED'
                color = C.COLOR_SKIP
            else:
                status = 'FATAL'
                color = C.COLOR_ERROR

            line = [
                self._get_uuid(result),
                self._get_state(status),
                self._get_task_name(result),
                self._get_host(result=result)
            ]
            item_result = self._get_item_label(result._result)
            # don't display if None
            if item_result:
                line.append('item=%s' % item_result)
            line.append('error=%s' % self._dump_results(result._result))
            self._output(line, color)

    def v2_runner_item_on_failed(self, result):
        line = [
            self._get_uuid(result),
            self._get_state('FATAL'),
            self._get_task_name(result),
            self._get_host(result=result)
        ]
        color = C.COLOR_ERROR
        item_result = self._get_item_label(result._result)
        # don't display if None
        if item_result:
            line.append('item=%s' % item_result)
        line.append('error=%s' % self._dump_results(result._result))
        self._output(line, color)

    def v2_runner_on_ok(self, result):
        if isinstance(result._task, TaskInclude):
            return
        (line, color) = self._get_item_line(result)
        if not line:
            return
        self._handle_warnings(result._result)
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            if self._run_is_verbose(result):
                line.append('result=%s' % self._dump_results(result._result))
            self._output(line, color)

    def v2_runner_item_on_skipped(self, result):
        if not C.DISPLAY_SKIPPED_HOSTS:
            return
        self._clean_results(result._result, result._task.action)
        line = [
            self._get_uuid(result),
            self._get_state('SKIPPED'),
            self._get_task_name(result),
            self._get_host(result=result)
        ]
        color = C.COLOR_SKIP
        item_result = self._get_item_label(result._result)
        # don't display if None
        if item_result:
            line.append('item=%s' % item_result)
        if self._run_is_verbose(result):
            line.append('result=%s' % self._dump_results(result._result))
        self._output(line, color)

    def v2_runner_on_skipped(self, result):
        # TODO(mwhahaha): this is broken?
        # if self.display_skipped_hosts:
        self._clean_results(result._result, result._task.action)
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            line = [
                self._get_uuid(result),
                self._get_state('SKIPPED'),
                self._get_task_name(result),
                self._get_host(result=result)
            ]
            color = C.COLOR_SKIP
            item_result = self._get_item_label(result._result)
            # don't display if None
            if item_result:
                line.append('item=%s' % item_result)
            self._output(line, color)

    def v2_runner_on_unreachable(self, result):
        line = [
            self._get_uuid(result),
            self._get_state('UNREACHABLE'),
            self._get_task_name(result),
            self._get_host(result=result)
        ]
        item_result = self._get_item_label(result._result)
        # don't display if None
        if item_result:
            line.append('item=%s' % item_result)
        self._output(line, C.COLOR_UNREACHABLE)

    def v2_playbook_on_include(self, included_file):
        color = C.COLOR_SKIP
        # included files don't have tasks so lets generate one for the file
        # for consistency. Should this be optional?
        file_id = str(uuid.uuid4())
        for host in included_file._hosts:
            line = [
                file_id,
                self._get_state('INCLUDED'),
                included_file._filename,
                host.name
            ]
            self._output(line, color)

    def v2_runner_retry(self, result):
        retry_count = result._result['retries'] - result._result['attempts']
        # NOTE(mwhahaha): action is async_status we know we're waiting vs a
        # failure that is being retried. We can adjust state & color.
        # We use getattr because ansible will stop using this if we try and
        # access an undefined thing, so let's be careful.
        if (getattr(result, '_task', False)
                and (getattr(result._task, 'action', False)
                     in ['async_status'])):
            state = 'WAITING'
        else:
            state = 'RETRY'
        color = C.COLOR_DEBUG
        host_str = self._get_host(result=result)
        line = [
            self._get_uuid(result),
            self._get_state(state),
            self._get_task_name(result),
            host_str,
            '%d retries left' % retry_count
        ]
        if self._run_is_verbose(result, verbosity=2):
            line.append("result=%s" % self._dump_results(result._result))
        self._output(line, color)
