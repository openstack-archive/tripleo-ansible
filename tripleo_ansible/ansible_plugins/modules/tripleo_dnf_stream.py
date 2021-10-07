# Copyright 2021 Red Hat, Inc.
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


DOCUMENTATION = '''
---
module: tripleo_dnf_stream
short_description: Enable or disable a set of DNF stream modules if available.
description:
    - "Enables or disables one or more I(dnf) module streams. If no stream is being
      specified, the default stream will be enabled/disabled."
options:
  name:
    description:
      - "A module name to enable or disable, like C(container-tools:3.0).
        If no stream or profile is specified then the defaults will be enabled
        To handle multiple I(dnf) modules this parameter can accept a comma
        separated string or a list of module names with their streams.
        Passing the profile in this parameter won't have any impact as the
        module only enables or disables the stream, it doesn't install/uninstall
        packages."
    required: true
    type: list
    elements: str
  state:
    description:
      - "Whether to enable or disable a module. After the task is executed only
        the module will change, there is no packages synchronization performed.
        To do so, please check the I(dnf) Ansible module."
    default: 'enabled'
    required: false
    type: str
    choices: ['enabled', 'disabled']

author:
    - Jose Luis Franco Arza (@jfrancoa)
'''

EXAMPLES = '''
- hosts: dbservers
  tasks:
    - name: Enable container-tools:3.0 stream module
      tripleo_dnf_stream:
        name: container-tools:3.0
        state: enabled
    - name: Disable container-tools:3.0 stream module
      tripleo_dnf_stream:
        name: container-tools:3.0
        state: disabled
    - name: Enable nginx, php:7.4 and python36:36
      tripleo_dnf_stream:
        name:
          - nginx
          - php:7.4
          - python36:3.6
    - name: Update packages
      dnf:
        name: *
        state: latest
'''

import sys

try:
    import dnf
    import dnf.cli
    import dnf.const
    import dnf.exceptions
    import dnf.subject
    import dnf.util
    HAS_DNF = True
except ImportError:
    HAS_DNF = False

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

from yaml import safe_load as yaml_safe_load


class DnfModule():
    """
    DNF Ansible module back-end implementation
    """

    def __init__(self, module):
        self.module = module

        self.name = self.module.params['name']
        self.state = self.module.params['state']

        self._ensure_dnf()

        try:
            dnf.base.WITH_MODULES
        except AttributeError:
            self.module.fail_json(
                msg="DNF modules are not supported.",
                results=[],
            )

    def _ensure_dnf(self):
        if not HAS_DNF:
            self.module.fail_json(
                msg="Could not import the dnf python module using {0} ({1}). "
                    "Please install `python3-dnf` package or ensure you have specified the "
                    "correct ansible_python_interpreter.".format(sys.executable, sys.version.replace('\n', '')),
                results=[],
            )

    def _base(self):
        """Return a fully configured dnf Base object."""
        base = dnf.Base()
        base.read_all_repos()
        base.fill_sack()
        try:
            # this method has been supported in dnf-4.2.17-6 or later
            # https://bugzilla.redhat.com/show_bug.cgi?id=1788212
            base.setup_loggers()
        except AttributeError:
            pass
        try:
            base.init_plugins()
            base.pre_configure_plugins()
        except AttributeError:
            pass  # older versions of dnf didn't require this and don't have these methods
        try:
            base.configure_plugins()
        except AttributeError:
            pass  # older versions of dnf didn't require this and don't have these methods

        return base

    def _is_module_available(self, module_spec):
        module_spec = module_spec.strip()
        module_list, nsv = self.module_base._get_modules(module_spec)

        if nsv:
            return True, nsv
        else:
            return False, None

    def _is_module_enabled(self, module_nsv):
        enabled_streams = self.base._moduleContainer.getEnabledStream(module_nsv.name)

        if enabled_streams:
            if module_nsv.stream:
                if module_nsv.stream in enabled_streams:
                    return True     # The provided stream was found
                else:
                    return False    # The provided stream was not found
            else:
                return True         # No stream provided, but module found

    def ensure(self):
        response = {
            'msg': "",
            'changed': False,
            'results': [],
            'rc': 0
        }

        # Accumulate failures.  Package management modules install what they can
        # and fail with a message about what they can't.
        failure_response = {
            'msg': "",
            'failures': [],
            'results': [],
            'rc': 1
        }

        if self.state == 'enabled':
            for module in self.name:
                try:
                    module_found, nsv = self._is_module_available(module)
                    if module_found:
                        if self._is_module_enabled(nsv):
                            response['results'].append("Module {0} already enabled.".format(module))
                        self.module_base.enable([module])
                    else:
                        failure_response['failures'].append("Module {0} is not available in the system.".format(module))
                except dnf.exceptions.MarkingErrors as e:
                    failure_response['failures'].append(' '.join((module, to_native(e))))

        else:
            # state = 'disabled'
            for module in self.name:
                try:
                    module_found, nsv = self._is_module_available(module)
                    if module_found:
                        if not self._is_module_enabled(nsv):
                            response['results'].append("Module {0} already disabled.".format(module))
                        self.module_base.disable([module])
                        self.module_base.reset([module])
                    else:
                        # If the module is not available move on
                        response['results'].append("Module {0} is not available in the system".format(module))
                except dnf.exceptions.MarkingErrors as e:
                    failure_response['failures'].append(' '.join((module, to_native(e))))

        try:
            if failure_response['failures']:
                failure_response['msg'] = 'Failed to manage some of the specified modules'
                self.module.fail_json(**failure_response)

            # Perform the transaction if no failures found
            self.base.do_transaction()
            self.module.exit_json(**response)
        except dnf.exceptions.Error as e:
            failure_response['msg'] = "Unknown Error occured: {0}".format(to_native(e))
            self.module.fail_json(**failure_response)

        response['changed'] = True

    def run(self):
        """The main function."""

        # Note: base takes a long time to run so we want to check for failure
        # before running it.
        if not dnf.util.am_i_root():
            self.module.fail_json(
                msg="This command has to be run under the root user.",
                results=[],
            )

        self.base = self._base()

        self.module_base = dnf.module.module_base.ModuleBase(self.base)

        self.ensure()


def main():

    module = AnsibleModule(
        argument_spec=yaml_safe_load(DOCUMENTATION)['options'],
        supports_check_mode=False,
    )

    module_implementation = DnfModule(module)
    try:
        module_implementation.run()
    except dnf.exceptions.RepoError as de:
        module.fail_json(
            msg="Failed to synchronize repodata: {0}".format(to_native(de)),
            rc=1,
            results=[],
            changed=False
        )

if __name__ == '__main__':
    main()
