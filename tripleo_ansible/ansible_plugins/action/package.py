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


import imp
import os

import ansible.plugins.action as action


DOCUMENTATION = """
---
module: package
author:
    - Kevin Carter (@cloudnull)
version_added: '2.8'
short_description: Tripleo action plugin to evaluate package installations
notes: []
description:
  - This is an action plugin shim that will intercept the use of
    the standard package module. The intention of this shim is to ensure the
    package module respects the option `tripleo_enable_package_install`
    which is used to control the installation of packages through a
    deployment.

    This plugin will do nothing if `tripleo_enable_package_install`
    is unset thereby allowing ansible to function normally. When the global
    option is present the plugin will evaluate its truthiness and react
    accordingly.

    * False - No action taken, task will be marked as skipped.

    * True - Package installation happens normally.

    If this module encounters an error while processesing the module will
    proceed as if the option `tripleo_enable_package_install` is unset which
    ensures ansible tasks are handled correctly no matter the context in
    which they are executed.

    Anytime this module results in a "skip" a message will be made available
    which indicates why it was skipped. Messages will only be visualized
    when debug mode has been enabled or through registering a variable and
    using it a task which can print messages; e.g. `debug` or `fail`.
options:
  tripleo_enable_package_install:
    description:
      - Boolean option to enable or disable package installations. This option
        can be passed in as a task var, groupvar, or hostvar. This option is
        **NOT** a module argument.
    required: True
    default: True
"""


EXAMPLES = """
# Run package install
- name: Run Package Installation
  package:
    name: mypackage
    state: present
  vars:
    tripleo_enable_package_install: true
"""


# NOTE(cloudnull): imp is being used because core action plugins are not
#                  importable in py27. Once we get to the point where we
#                  no longer support py27 these lines should be converted
#                  to a straight python import.
#
#                  >>> from ansible.plugins.action import package
#
PKG = imp.load_source(
    'package',
    os.path.join(
        os.path.dirname(
            action.__file__
        ),
        'package.py'
    )
)


def _bool_set(bool_opt):
    """Check if option is a bool and return its type.

    returns: `bool` || `None`
    """
    true_opts = ('true', 'yes', '1')
    false_opts = ('false', 'no', '0')
    if bool_opt is None:
        return None
    elif bool_opt is True:
        return True
    elif bool_opt is False:
        return False
    else:
        bool_opt = str(bool_opt).lower()
        if bool_opt in (true_opts + false_opts):
            if bool_opt in true_opts:
                return True
            else:
                return False
        else:
            return None


class ActionModule(PKG.ActionModule):
    def run(self, tmp=None, task_vars=None):
        """Shim for tripleo package operations.

        This shim will intercept the package module and if the hostvar
        `tripleo_enable_package_install` is set to false all package
        operations will be no-op. If this option is set to true, then the
        normal package module will be executed.

        * This shim allows for the package module to be used with and without
          delegation.
        * In the event of ANY exception the module will hand off back to the
          normal package module.
        """
        try:
            if self._task.delegate_to:
                tripleo_pkg = self._templar.template(
                    "{{ hostvars['%s']['tripleo_enable_package_install'] }}"
                    % self._task.delegate_to
                )
            else:
                tripleo_pkg = self._templar.template(
                    "{{ tripleo_enable_package_install }}"
                )
        except Exception:  # If any exception run the normal pkg module
            tripleo_pkg = None
        else:
            tripleo_pkg = _bool_set(bool_opt=tripleo_pkg)
        finally:
            if (tripleo_pkg is not None) and (tripleo_pkg is False):
                return {
                    'failed': False,
                    'skipped': True,
                    'msg': 'package installations are currently disabled,'
                           ' via "tripleo_enable_package_install" being'
                           ' set to "{}". please check the deployment'
                           ' settings.'.format(tripleo_pkg),
                    'bool_param': tripleo_pkg
                }
            else:
                return super(ActionModule, self).run(tmp, task_vars)
