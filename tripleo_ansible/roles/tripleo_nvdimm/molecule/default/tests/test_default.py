# Copyright 2020 Red Hat, Inc.
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


import os
import json
import pytest
import testinfra.utils.ansible_runner


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_ndctl_is_installed(host):
    ndctl = host.package("ndctl")
    assert ndctl.is_installed


def test_namespace_is_created(host):
    if not host.check_output('lsmod | grep libnvdimm | cut -d " " -f 1'):
        pytest.skip("Skipping because this needs NVDIMM hardware")
    pmem_ns = os.environ['TRIPLEO_NVDIMM_PMEM_NAMESPACES']
    ndctl_list_output = host.check_output('ndctl list')
    namespaces = {ns.get('name') for ns in json.loads(ndctl_list_output)}
    wanted_ns = [ns_name.split(':')[1] for ns_name in pmem_ns.split(',')]
    for ns in wanted_ns:
        assert ns in namespaces
