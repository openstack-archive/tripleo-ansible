# Copyright 2019 Red Hat, Inc.
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


DOCUMENTATION = """
---
module: tripleo_iptables
author:
  - Kevin Carter (@cloudnull) <kecarter@redhat.com>
version_added: '2.8'
short_description: Runs iptables module commands in bulk.
notes: []
description:
  - This module accepts iptables rules in list format and batches their
    creation to speed up the creation of rules at scale.
options:
  tripleo_rules:
    description:
      - List of rules to batch, rules have been constructed using the tripleo
        spec and will be formatted to match the input values of the core
        iptables module.
    required: True
"""

EXAMPLES = """
- name: Run Package Installation
  tripleo_iptables:
    tripleo_rules:
      - '1 rule special':
          dport:
            - 1234
            - 4321
      - '2 rule special also':
          dport:
            - 2345
            - 5432
"""


from ansible.plugins.action import ActionBase
from ansible.plugins.filter import ipaddr
from ansible.utils.display import Display


DISPLAY = Display()
RULE_STATES = {
    'enabled': 'present',
    'present': 'present',
    'absent': 'absent',
    'disabled': 'absent'
}
IPTABLES_BIN = {
    'ipv4': 'iptables',
    'ipv6': 'ip6tables'
}
IPTABLES_CHAIN_CMD = """
if ! {cmd} --list "{chain}"; then
    {cmd} -N "{chain}"
fi
"""
IPTABLES_CHAINS = ('INPUT', 'OUTPUT', 'FORWARD')


class ActionModule(ActionBase):
    """Batch iptables rules for faster rule creation."""

    def _run_module(self, name, args, task_vars):
        """Runs an ansible module and collects return information.

        :returns: boolean
        """

        module_return = self._execute_module(
            module_name=name,
            module_args=args,
            task_vars=task_vars
        )
        changed = module_return.get('changed')
        if changed:
            self.return_data['changed'] = True

        self.return_data['stdout'] = module_return.get('stdout')
        self.return_data['stderr'] = module_return.get('stderr')
        self.return_data['msg'] = module_return.get('msg')
        self.return_data['cmd'] = module_return.get('cmd')
        self.return_data['rc'] = module_return.get('rc', 0)
        fatal = self.return_data['failed'] = module_return.get(
            'failed',
            False
        )
        DISPLAY.vv('Module name: {}'.format(name))
        DISPLAY.vv('Module args: {}'.format(args))
        if fatal:
            DISPLAY.error('Failed, module return: {}'.format(module_return))
            DISPLAY.error('Failed, return data: {}'.format(self.return_data))

        return fatal

    @staticmethod
    def _check_rule_data(rule_data, ipversion):
        """Check the rule data for compatible ip version information.

        This function uses the ansible ipaddr filter to validate IP
        information when a source or destination has been provided.

        :returns: boolean
        """

        kwargs_hash = {
            'ipv6': {
                'version': 6,
                'query': 'ipv6',
                'alias': 'ipv6'
            },
            'ipv4': {
                'version': 4,
                'query': 'ipv4',
                'alias': 'ipv4'
            }
        }

        for arg in ('source', 'destination'):
            ip_data = rule_data.get(arg)
            if ip_data:
                DISPLAY.v(
                    'Checking "{}" against "{}" with ip version "{}"'.format(
                        arg,
                        ip_data,
                        ipversion
                    )
                )
                ip_data_check = ipaddr.ipaddr(
                    value=ip_data,
                    **kwargs_hash[ipversion]
                )
                DISPLAY.vvv('ipaddr filter return "{}"'.format(ip_data_check))
                if not ip_data_check:
                    DISPLAY.v(
                        'Rule has a "{}" but the value "{}" is not applicable'
                        ' to ip version "{}"'.format(
                            arg,
                            ip_data,
                            ipversion

                        )
                    )
                    DISPLAY.vvv('Rule data: "{}"'.format(rule_data))
                    return False
        else:
            return True

    def queue_rules(self):
        """Add chains and rules to the required queues."""

        for item in self._task.args['tripleo_rules']:
            rule_data = dict()
            rule = item['rule']

            ipversions = rule.get('ipversion', ['ipv4', 'ipv6'])
            if not isinstance(ipversions, list):
                ipversions = [ipversions]

            state = rule.get('extras', dict()).get('ensure', 'enabled')
            rule_data['state'] = RULE_STATES[state]

            action = rule_data['action'] = rule.get('action', 'insert')
            if action == 'drop':
                rule_data['action'] = 'insert'
                rule_data['state'] = 'absent'

            rule_data['chain'] = rule.get('chain', 'INPUT')
            rule_data['jump'] = rule.get('jump', 'ACCEPT')
            rule_data['protocol'] = rule.get('proto', 'tcp')
            if 'table' in rule:
                rule_data['table'] = rule['table']

            if 'interface' in rule:
                rule_data['in_interface'] = rule['interface']

            if 'sport' in rule:
                rule_data['source_port'] = rule['sport']

            if 'source' in rule:
                rule_data['source'] = rule['source']

            if rule_data['protocol'] != 'gre':
                rule_data['ctstate'] = rule.get('state', 'NEW')

            if 'limit' in rule:
                rule_data['limit'] = rule['limit']

            if 'limit_burst' in rule:
                rule_data['limit_burst'] = rule['limit_burst']

            if 'destination' in rule:
                rule_data['destination'] = rule['destination']

            for ipversion in ipversions:
                if not self._check_rule_data(rule_data=rule_data,
                                             ipversion=ipversion):
                    continue

                versioned_rule_data = rule_data.copy()
                versioned_rule_data['ip_version'] = ipversion
                if 'rule_name' in item:
                    versioned_rule_data['comment'] = '{} {}'.format(
                        item['rule_name'],
                        ipversion
                    )

                if not versioned_rule_data['chain'] in IPTABLES_CHAINS:
                    chain = versioned_rule_data['chain']
                    DISPLAY.v(
                        'Queueing chain: {}, ip version {}'.format(
                            chain, ipversion
                        )
                    )
                    self.iptables_chains.append(
                        {
                            'ipv': ipversion,
                            'chain': chain,
                            'command': IPTABLES_CHAIN_CMD.format(
                                cmd=IPTABLES_BIN[ipversion],
                                chain=chain
                            )
                        }
                    )

                if 'dport' in rule:
                    dport_rule_data = versioned_rule_data.copy()
                    dports = rule['dport']
                    if not isinstance(dports, list):
                        dports = [dports]

                    for dport in dports:
                        if isinstance(dport, int):
                            dport_rule_data['destination_port'] = dport
                        else:
                            dport = dport.replace('-', ':')
                            dport_rule_data['destination_port'] = dport

                        DISPLAY.v(
                            'Queueing port rule: {},'
                            ' ip version: {},'
                            ' dport: {}'.format(
                                dport_rule_data.get('comment', None),
                                ipversion,
                                dport_rule_data['destination_port']
                            )
                        )
                        self.iptables_rules.append(dport_rule_data.copy())
                else:
                    DISPLAY.v(
                        'Queueing service rule: {},'
                        ' ip version: {}'.format(
                            versioned_rule_data.get('comment', None),
                            ipversion
                        )
                    )
                    self.iptables_rules.append(versioned_rule_data.copy())

    def run(self, tmp=None, task_vars=None):
        """Run the iptables firewall rule batcher.

        When rules are batched, the chains will be created before the rules.
        """

        self.return_data = dict()
        self.iptables_rules = list()
        self.iptables_chains = list()

        self.queue_rules()

        for iptables_chain in self.iptables_chains:
            DISPLAY.v(
                'Managing chain: {} for version {}'.format(
                    iptables_chain['chain'],
                    iptables_chain['ipv']
                )
            )
            return_data = self._low_level_execute_command(
                iptables_chain['command'],
                executable='/bin/bash'
            )
            if return_data['rc'] > 0:
                DISPLAY.error(msg='Failed command: {}'.format(iptables_chain))
                DISPLAY.error(msg='Failed chain data: {}'.format(return_data))
                return return_data

        for iptables_rule in self.iptables_rules:
            DISPLAY.v(
                'Managing rule: {},'
                ' dport: {},'
                ' ip version: {}'.format(
                    iptables_rule.get('comment', 'undefined'),
                    iptables_rule.get('destination_port', 'undefined'),
                    iptables_rule['ip_version'],
                )
            )
            fatal = self._run_module(
                name='iptables',
                args=iptables_rule,
                task_vars=task_vars
            )
            if fatal:
                return self.return_data

        return self.return_data
