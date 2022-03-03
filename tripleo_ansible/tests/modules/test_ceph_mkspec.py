# Copyright 2021 Red Hat, Inc.
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
"""Test the methods of the ceph_mkspec module"""


from tripleo_ansible.ansible_plugins.modules import ceph_mkspec
try:
    from ansible.module_utils.ca_common import generate_ceph_cmd
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils.ca_common import generate_ceph_cmd

try:
    from ansible.module_utils import ceph_spec
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import ceph_spec

from tripleo_ansible.tests import base as tests_base


class TestCephMKSpec(tests_base.TestCase):
    '''
    Test the methods of the ceph_spec_bootstrap module
    '''

    def test_generate_orch_cli(self):
        '''
        Test the cmd generation run against the ceph cluster when apply: true
        is passed to the module.
        This command is supposed to use the orchestrator and apply the spec
        rendered in a given input_path
        '''

        input_path = "/tmp/specfile"
        cluster = "ceph"
        container_image = "quay.ceph.io/ceph-ci/daemon:latest"
        args = ['apply', '--in-file', input_path]

        expected_cli_cmd = generate_ceph_cmd(sub_cmd=['orch'], args=args,
                                             spec_path=input_path, cluster=cluster,
                                             container_image=container_image)

        gen_cli_cmd = ceph_mkspec.generate_orch_cli(cluster, input_path, container_image)
        self.assertEqual(expected_cli_cmd, gen_cli_cmd)
