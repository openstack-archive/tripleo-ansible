# Copyright 2021 Red Hat, Inc.  All Rights Reserved.
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

from tripleo_ansible.ansible_plugins.modules import tripleo_findif_for_ip as fip
from tripleo_ansible.tests import base as tests_base

from unittest import mock

test_output = """
UNKNOWN        127.0.0.1/8 ::1/128
ens4             UP fe80::5054:ff:fe54:eb48/64
ovs-system       DOWN
br-ex            UNKNOWN        192.168.24.23/24 192.168.24.10/32 192.168.24.13/32 192.168.24.16/32 fe80::5054:ff:fe54:eb48/64
br-int           DOWN
br-tun           DOWN
vxlan_sys_4789   UNKNOWN fe80::90dc:e2ff:fedd:10a8/64
"""


class TestFindIfForIp(tests_base.TestCase):

    def test_find_ipv6_interface(self):
        module = mock.MagicMock()
        module.run_command = mock.MagicMock()
        module.run_command.return_value = (0, test_output, '')
        self.assertEqual(fip.find_interface(module, 'fe80::5054:ff:fe54:eb48')['interface'],
                         'ens4')

    def test_find_ipv4_interface(self):
        module = mock.MagicMock()
        module.run_command = mock.MagicMock()
        module.run_command.return_value = (0, test_output, '')
        self.assertEqual(fip.find_interface(module, '192.168.24.23')['interface'],
                         'br-ex')

    def test_find_ipv4_interface_noresult(self):
        module = mock.MagicMock()
        module.run_command = mock.MagicMock()
        module.run_command.return_value = (0, test_output, '')
        self.assertEqual(fip.find_interface(module, '192.168.24.99')['interface'],
                         '')

    @mock.patch('subprocess.check_output')
    def test_find_ipv6_interface_noresult(self, mock_checkoutput):
        module = mock.MagicMock()
        module.run_command = mock.MagicMock()
        module.run_command.return_value = (0, test_output, '')
        self.assertEqual(fip.find_interface(module, 'fe80::5054:ff:fe54:eb47')['interface'],
                         '')
