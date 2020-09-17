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

import yaml

try:
    from ansible.module_utils import tripleo_common_utils as tc
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import tripleo_common_utils as tc
from tripleo_ansible.ansible_plugins.modules import tripleo_get_host_cpus as derive_params
from tripleo_ansible.tests import base as tests_base


class TestTripleoGetHostCpus(tests_base.TestCase):
    """Test the _get_host_cpus_list of the OvS DPDK module"""

    def test_run_valid_inspect_data(self):
        inspect_data = {
            "numa_topology": {
                "cpus": [{"cpu": 21, "numa_node": 1,
                          "thread_siblings": [38, 82]},
                         {"cpu": 27, "numa_node": 0,
                          "thread_siblings": [20, 64]},
                         {"cpu": 3, "numa_node": 1,
                          "thread_siblings": [25, 69]},
                         {"cpu": 20, "numa_node": 0,
                          "thread_siblings": [15, 59]}]
                }
            }
        expected_result = "15,59,25,69"

        result = derive_params._get_host_cpus_list(inspect_data)
        self.assertEqual(result, expected_result)

    def test_run_invalid_inspect_data(self):
        inspect_data = {"numa_topology": {"cpus": []}}

        self.assertRaises(tc.DeriveParamsError,
                          derive_params._get_host_cpus_list,
                          inspect_data)
