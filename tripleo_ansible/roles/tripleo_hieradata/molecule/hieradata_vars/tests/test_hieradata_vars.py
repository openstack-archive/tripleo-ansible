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


import os
import json

import testinfra.utils.ansible_runner


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_json_render(host):
    rendered_files = [
      "all_nodes",
      "bootstrap_node",
      "cloud_domain",
      "extraconfig",
      "fqdn",
      "net_ip_map",
      "service_configs",
      "service_names",
      "vip_data",
      "ovn_chassis_mac_map"
    ]

    for f in rendered_files:
        json.loads(
            host.file(
                '/etc/puppet/hieradata/{}.json'.format(f)
            ).content_string
        )
