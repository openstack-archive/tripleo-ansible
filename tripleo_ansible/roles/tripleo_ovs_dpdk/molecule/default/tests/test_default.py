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


def get_config(host):
    stdout = host.check_output('ovs-vsctl get open_vswitch . other_config')
    content = '[default]\n' + stdout.replace('{', '').replace('}', '').replace(', ', '\n')
    print(content)
    cfg = configparser.RawConfigParser()
    cfg.read_string(content)
    print(dict(cfg['default']))
    return dict(cfg['default'])


def test_positive_dpdk_extra(host):
    other_config = get_config(host)
    dpdk_extra = other_config['dpdk-extra'].replace('"', '')
    assert dpdk_extra == " -n 4"


def test_positive_pmd(host):
    other_config = get_config(host)
    val = other_config['pmd-cpu-mask'].replace('"', '')
    assert val == "e002"


def test_positive_socket_mem(host):
    other_config = get_config(host)
    assert 'dpdk-socket-mem' not in other_config
    assert 'dpdk-socket-limit' not in other_config


def test_positive_lcore(host):
    other_config = get_config(host)
    assert 'dpdk-lcore-mask' not in other_config


def test_positive_validator_threads(host):
    other_config = get_config(host)
    assert 'n-revalidator-threads' not in other_config


def test_positive_handler_threads(host):
    other_config = get_config(host)
    assert 'n-handler-threads' not in other_config


def test_positive_emc_prob(host):
    other_config = get_config(host)
    assert 'emc-insert-inv-prob' not in other_config


def test_positive_enable_tso(host):
    other_config = get_config(host)
    assert 'userspace-tso-enable' not in other_config


def test_positive_pmd_load_threshold(host):
    other_config = get_config(host)
    assert 'pmd-auto-lb-load-threshold' not in other_config


def test_positive_pmd_improvement_threshold(host):
    other_config = get_config(host)
    assert 'pmd-auto-lb-improvement-threshold' not in other_config


def test_positive_pmd_rebal_interval(host):
    other_config = get_config(host)
    assert 'pmd-auto-lb-rebal-interval' not in other_config
