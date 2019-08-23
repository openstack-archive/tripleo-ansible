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


import configparser
import os

import testinfra.utils.ansible_runner


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_isolated_cores(host):
    assert host.file('/etc/tuned/cpu-partitioning-variables.conf').contains('^isolated_cores=1$')


def test_cpu_affinity(host):
    out = host.check_output('nproc --all')
    cpus = ''
    for i in range(int(out)):
        if i == 1:
            continue
        if cpus:
            cpus += ' '
        cpus += str(i)
    assert host.file('/etc/systemd/system.conf').contains('^CPUAffinity=' + cpus + '$')
