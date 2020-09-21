# Copyright 2019 Red Hat, Inc.
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

from tripleo_ansible.ansible_plugins.modules import (
    tripleo_os_net_config_mappings)
from tripleo_ansible.tests import base as tests_base
from unittest import mock


@mock.patch('tripleo_ansible.ansible_plugins.modules.'
            'tripleo_os_net_config_mappings._get_interfaces', autospec=True)
@mock.patch('subprocess.Popen', autospec=True)
class TestTripleoOsNetConfigMappings(tests_base.TestCase):

    def test_mac_mappings_match(self, mock_Popen, mock_get_ifaces):
        module = mock.MagicMock()
        module.params = {
            'net_config_data_lookup': {
                'node0': {'nic1': 'aa:bb:cc:dd:ee:ff',
                          'nic2': 'ff:ee:dd:cc:bb:aa'},
                'node1': {'nic1': '0a:0b:0c:0d:0e:0f',
                          'nic2': 'f0:e0:d0:c0:b0:a0'}
            }
        }
        mock_exit = mock.MagicMock()
        module.exit_json = mock_exit
        mock_get_ifaces.side_effect = ['aa:bb:cc:dd:ee:ff', 'ff:ee:dd:cc:bb:aa']
        expected = module.params['net_config_data_lookup']['node0']
        tripleo_os_net_config_mappings.run(module)
        mock_exit.assert_called_once_with(
            changed=True, mapping={'interface_mapping': expected})

    def test_mac_mappings_no_match(self, mock_Popen, mock_get_ifaces):
        module = mock.MagicMock()
        module.params = {
            'net_config_data_lookup': {
                'node0': {'nic1': 'aa:bb:cc:dd:ee:ff',
                          'nic2': 'ff:ee:dd:cc:bb:aa'},
                'node1': {'nic1': '0a:0b:0c:0d:0e:0f',
                          'nic2': 'f0:e0:d0:c0:b0:a0'}
            }
        }
        mock_exit = mock.MagicMock()
        module.exit_json = mock_exit
        mock_get_ifaces.side_effect = ['01:02:03:04:05:06', '10:20:30:40:50:60']
        tripleo_os_net_config_mappings.run(module)
        mock_exit.assert_called_once_with(changed=False, mapping=None)

    def test_dmi_type_string_match(self, mock_Popen, mock_get_ifaces):
        module = mock.MagicMock()
        module.params = {
            'net_config_data_lookup': {
                'node2': {'dmiString': 'foo-dmi-type',
                          'id': 'bar-dmi-id',
                          'nic1': 'em3',
                          'nic2': 'em4'},
                'node3': {'nic1': '0a:0b:0c:0d:0e:0f',
                          'nic2': 'f0:e0:d0:c0:b0:a0'}
            }
        }
        mock_exit = mock.MagicMock()
        module.exit_json = mock_exit
        expected = {'nic1': 'em3',
                    'nic2': 'em4'}
        mock_return = mock.MagicMock()
        mock_return.return_value.communicate.return_value = ('bar-dmi-id', '')
        mock_Popen.side_effect = mock_return
        tripleo_os_net_config_mappings.run(module)
        mock_exit.assert_called_once_with(
            changed=True, mapping={'interface_mapping': expected})
