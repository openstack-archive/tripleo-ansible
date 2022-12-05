#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
__metaclass__ = type

import glob
import os
import re

from ansible.module_utils._text import to_native
from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: tripleo_ovs_update
author:
  - Sofer Athlan-Guyot <sathlang@redhat.com>
version_added: '2.8'
short_description: Handle special ovs update.
notes: []
description:
  - This module check if ovs need a special treatment during update of the
    package.
options:
  debug:
    description:
      - Whether or not debug is enabled.
    default: False
    required: False
    type: bool
"""

EXAMPLES = """
- name: Special treatment for ovs upgrade.
  tripleo_ovs_upgrade:
"""

RETURN = """
msg:
    description: Descrption of the action taken.
    returned: always
    type: str
changed:
    description: Was the ovs package update or not.
    returned: always
    type: bool
"""


def run_locale_safe(module, *args, **kwargs):
    if isinstance(*args, str):
        cmd = 'env LANG=C.UTF-8' + str(*args)
    else:
        cmd = ['env', 'LANG=C.UTF-8'] + list(*args)
    return module.run_command(cmd, **kwargs)


def pkg_manager(module, downloader=False):
    dnf = module.get_bin_path('dnf')
    if dnf:
        module.debug("Using dnf as package manager")
        if not downloader:
            return dnf
        else:
            return ['dnf', 'download']
    if not downloader:
        return module.get_bin_path('yum')
    else:
        return ['yumdownloader']


def get_current_ovs_pkg_name(module):
    """ Get currently installed ovs pkg name, layered or not."""
    cmd = ['rpm', '-qa']
    _, output, _ = run_locale_safe(module, cmd, check_rc=True)
    ovs_re = re.compile(r"""
    ^(openvswitch[0-9]+\.[0-9]+-[0-9]+\.[0-9]+\.[0-9]+ # layered
    |                                                  # or
    openvswitch(?!-[a-z]+))                            # non-layered
    """, re.X)
    for pkg in output.split("\n"):
        ovs = re.search(ovs_re, pkg)
        if ovs:
            return ovs.group(0)
    return None


# Process rhosp-openvswitch layered package for new version number
# return stuff like ["2.11"] in original module
def get_version(module, pkg, new=True):
    if new:
        cmd = [pkg_manager(module), 'info', '-q', pkg]
    else:
        cmd = ['rpm', '-qi', pkg]
    # This may fail if the package is not around for non-lp product.
    _, output, _ = run_locale_safe(module, cmd, check_rc=False)
    versions = re.findall(r'Version[^:]*:[^0-9]*([0-9.]+)', output)
    found = []
    for version in versions:
        if version:
            # we are only interested in major/minor number here.
            if new:
                # We can have several version here
                found.append(version.split('.')[:2])
            else:
                found = version.split('.')[:2]
    return found


def flatten_version(versions, join_str=''):
    flatten_str = ""
    if not isinstance(versions, list):
        versions = [versions]
    if len(versions) >= 1 and isinstance(versions[0], list):
        for version in versions:
            flatten_str += join_str.join(version)
    else:
        flatten_str += join_str.join(versions)
    return flatten_str


def get_current_ovs_pkg_names(module, pkg):
    cmd = ['rpm', '-qa', pkg]
    _, output, _ = run_locale_safe(module, cmd, check_rc=True)
    # Make sure we remove empty element.
    return [pkg for pkg in output.split("\n") if pkg]


def remove_package_noaction(module, pkgs, excludes=[]):
    cmd = ['rpm', '-e', '--noscripts', '--nopreun',
           '--nopostun', '--notriggers', '--nodeps']
    pkgs_to_remove = []
    for pkg in pkgs:
        for exclude in excludes:
            if not re.match(r'{}'.format(exclude), pkg):
                pkgs_to_remove.append(pkg)
    _, output, _ = run_locale_safe(module, cmd + pkgs_to_remove, check_rc=True)
    return output


def upgrade_pkg(module, pkg):
    cmd = [pkg_manager(module), 'upgrade', '-y', pkg]
    _, output, _ = run_locale_safe(module, cmd, check_rc=True)
    return output


def set_openflow_version_on_bridges(module, bridges=None):
    if bridges is None:
        bridges = ['br-int']
    for bridge in bridges:
        cmd = ['ovs-vsctl', 'set', 'bridge', bridge,
               'protocols=OpenFlow10,OpenFlow13,OpenFlow15']
        rc, out, err = run_locale_safe(module, cmd)
        if rc != 0:
            module.warn('Cannot set new OpenFlow protocols on a bridge: '
                        '%s: %s.' %
                        (bridge, to_native(err)))


def layer_product_upgrade(module, result, ovs_pkg, lp_ovs_current_version):
    """Actually do the layered ovs upgrade with workaround.

    So we have a layered package (rhosp|rdo)-openvswitch. To prevent
    any cut in networking during update/upgrade, we update ovs without
    triggering the scripts in the package that stop the service.

    So first it determines if the package has a upgrade coming and
    then erases it making sure no package script is triggered and
    finally it re-install the new package.

    It also prevents incomptible issues between ovs database schema
    during a rolling update.

    No cut in service at the cost of a needed reboot to get the new
    binaries in place.

    """
    layered_product_name = get_layered_product_name()
    lp_ovs_coming_versions = get_version(module, layered_product_name)
    ovs_current_version = get_version(module, ovs_pkg, new=False)

    pkg_suffix = ''
    if int(ovs_current_version[0]) >= 3 or int(ovs_current_version[1]) >= 10:
        pkg_suffix = '.'.join(ovs_current_version)

    if ovs_pkg == 'openvswitch':
        pkg_base_name = 'openvswitch*'
    else:
        pkg_base_name = 'openvswitch{}*'.format(pkg_suffix)

    if len(lp_ovs_coming_versions) == 0:
        result['msg'] += "Couldn't get the version of rhosp-openvswitch, " + \
            "check dnf info -q rhosp-openvswitch on this host."
        result['failed'] = True
    elif len(ovs_current_version) == 0:
        result['msg'] += "Couldn't get the current version of the ovs-package, " + \
            f"check rpm -qi {ovs_pkg} on this host."
        result['failed'] = True
    elif flatten_version(lp_ovs_coming_versions) \
            != flatten_version(ovs_current_version):
        # NOTE(mjozefcz): Workaround for bz1863024.
        if '2.11' == flatten_version(ovs_current_version, join_str='.'):
            set_openflow_version_on_bridges(module)
        ovs_pkgs = get_current_ovs_pkg_names(module, pkg_base_name)
        remove_package_noaction(module, ovs_pkgs,
                                excludes=['selinux'])
        upgraded = upgrade_pkg(module, layered_product_name)
        result['msg'] += \
            """ Layer product update workaround applied for {} \
Upgraded:'{}'""".format(ovs_pkgs, upgraded)
        result['changed'] = True
    else:
        result['msg'] += " No need to upgrade ovs."


def pkg_has_disruption(module):
    """Check if the current ovs pkg include a disruptive action."""
    awk_cmds = ["awk '/postuninstall/,/*/' | grep -q 'systemctl.*try-restart'",
                "awk '/preun/,/*/' | grep -q 'systemctl.*disable'"]
    rc = 1
    for awk in awk_cmds:
        cmd = "rpm -q --scripts openvswitch | {}".format(awk)
        rc, _, _ = run_locale_safe(module,
                                   cmd, check_rc=False,
                                   use_unsafe_shell=True)
        if rc == 0:
            break
    return rc == 0


def upgrade_non_layered_ovs(module, result):
    tmp_dir = '/root/OVS_UPGRADE'
    cmds = [
        ['rm', '-rf', tmp_dir],
        ['install', '-d', '-o', 'root', '-g', 'root', '-m', '0750', tmp_dir],
        [pkg_manager(module), 'makecache'],
        pkg_manager(module, downloader=True)
        + ['--destdir', tmp_dir, '--resolve', 'openvswitch']]
    for cmd in cmds:
        run_locale_safe(module, cmd, check_rc=True)

    for pkg in glob.glob(tmp_dir + '/*.rpm'):
        cmd = ['rpm', '-U',
               '--replacepkgs',
               '--notriggerun',
               '--nopostun',
               pkg]
        run_locale_safe(module, cmd, check_rc=True)
        result['msg'] += " {} handled".format(pkg)
        result['changed'] = True


def non_layered_ovs_upgrade(module, result):
    if not pkg_has_disruption(module):
        result['msg'] += 'Nothing to be done for non layered ovs upgrade, ' \
            "post-script doesn't have restart."
    else:
        result['msg'] += "OVS upgrade special handling."
        upgrade_non_layered_ovs(module, result)


def get_distro():
    """Get the distro as defined in /etc/os-release[ID]."""
    distro = None
    os_release_file = '/etc/os-release'
    if os.path.isfile(os_release_file):
        with open(os_release_file) as release_file:
            for line in release_file.readlines():
                match = re.match('^ *ID *="?([^"]+)"?$', line)
                if match:
                    distro = match.group(1)
                    break
    return distro


def get_layered_product_name():
    """Get the layer product name version depending on os.

    It's rhosp-openvswitch on redhat, and rdo-openvswitch on centos.

    """
    distro = get_distro()
    if distro is not None and distro == 'centos':
        return 'rdo-openvswitch'
    return 'rhosp-openvswitch'


def main():
    module = AnsibleModule(argument_spec={}, supports_check_mode=False)

    result = dict(
        changed=False,
        msg=''
    )

    layered_product_name = get_layered_product_name()
    ovs_current_pkg = get_current_ovs_pkg_name(module)
    if ovs_current_pkg:
        # We found a ovs package, let's dive in.
        ovs_current_version = get_version(module,
                                          layered_product_name,
                                          new=False)
        if ovs_current_version:
            result['msg'] += "Found a layered product ovs - {} - " \
                .format(layered_product_name)
            layer_product_upgrade(module, result,
                                  ovs_current_pkg, ovs_current_version)
        else:
            result['msg'] += "Found ovs. "
            non_layered_ovs_upgrade(module, result)
    else:
        result['msg'] += "No ovs installed, nothing to do."

    module.exit_json(**result)


if __name__ == '__main__':
    main()
