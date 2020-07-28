__metaclass__ = type

from ansible.plugins.callback import CallbackBase
from datetime import datetime

DOCUMENTATION = '''
    callback: tripleo_states
    type: aggregate
    short_description: adds states information
    version_added: "2.9"
    description:
      - TripleO specific callback useful to print out deployment states.
    requirements:
      - whitelisting in configuration - see examples section below for details.
'''


class CallbackModule(CallbackBase):

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'tripleo_states'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self, display=None):
        super(CallbackModule, self).__init__(display)

    def _output(self, msg, color=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        if isinstance(msg, list):
            output = ' | '.join([timestamp] + msg)
        else:
            output = timestamp + ' | ' + msg
        self._display.display(output, color=color)

    def v2_playbook_on_stats(self, stats):
        nodes_to_redeploy = []

        # Find out which hosts failed to deploy; it would very likely
        # happen when max_fail_percentage was set to a percentage value and the
        # number of hosts which successfully deployed matched the criteria.
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            if t['failures'] or t['unreachable']:
                nodes_to_redeploy.append(h)

        # Only display if there are nodes in error state for now but it might
        # change later if we add more information.
        if len(nodes_to_redeploy) > 0:
            self._output('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
                         ' State Information '
                         '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

            self._output(
                '~~~~~~~~~~~~~~~~~~'
                ' Number of nodes which did not deploy successfully: {} '
                '~~~~~~~~~~~~~~~~~'.format(len(nodes_to_redeploy)))
            nodes_to_redeploy_list = ", ".join(nodes_to_redeploy)
            fail_msg = ' The following node(s) had failures: ' + \
                '{}'.format(nodes_to_redeploy_list)
            self._output(fail_msg, 'red')
            self._output('~' * 89)
