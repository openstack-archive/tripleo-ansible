# Copyright 2021 Red Hat, Inc.
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
#

import mock
import openstack

try:
    from ansible.module_utils import network_data_v2 as n_utils
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import network_data_v2 as n_utils  # noqa
from tripleo_ansible.ansible_plugins.modules import (
    tripleo_overcloud_network_vip_extract as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs


@mock.patch.object(openstack.connection, 'Connection', autospec=True)
class TestTripleoOvercloudVipExtract(tests_base.TestCase):

    def setUp(self):
        super(TestTripleoOvercloudVipExtract, self).setUp()

        # Helper function to convert array to generator
        self.a2g = lambda x: (n for n in x)

    def test_find_net_vips(self, mock_conn):
        fake_net_resources = {
            'StorageNetwork': {
                'InternalApiNetwork': {'physical_resource_id': 'fake-id',
                                       'resource_type': n_utils.TYPE_NET},
                'StorageSubnet': {'physical_resource_id': 'fake-id',
                                  'resource_type': n_utils.TYPE_SUBNET},
                'StorageSubnet_leaf1': {'physical_resource_id': 'fake-id',
                                        'resource_type': n_utils.TYPE_SUBNET}
            }
        }
        fake_network = stubs.FakeNeutronNetwork(
            id='internal_api_id',
            name='internal_api')
        fake_subnet = stubs.FakeNeutronSubnet(
            id='internal_api_subnet_id',
            name='internal_api_subnet')
        fake_vip_port = stubs.FakeNeutronPort(
            id='internal_api_vip_id',
            name='internal_api_virtual_ip',
            fixed_ips=[{'subnet_id': 'internal_api_subnet_id',
                        'ip_address': '1.2.3.4'}],
            dns_name='internalapi.localdomain'
        )
        mock_conn.network.get_network.return_value = fake_network
        mock_conn.network.get_subnet.return_value = fake_subnet
        mock_conn.network.ports.return_value = self.a2g([fake_vip_port])

        vip_data = list()
        plugin.find_net_vips(mock_conn, fake_net_resources, vip_data)
        self.assertEqual([{'name': 'internal_api_virtual_ip',
                           'network': 'internal_api',
                           'subnet': 'internal_api_subnet',
                           'ip_address': '1.2.3.4',
                           'dns_name': 'internalapi.localdomain'}],
                         vip_data)

    def test_find_ctlplane_vip(self, mock_conn):
        fake_network = stubs.FakeNeutronNetwork(
            id='ctlplane_id',
            name='ctlplane')
        fake_subnet = stubs.FakeNeutronSubnet(
            id='ctlplane_subnet_id',
            name='ctlplane-subnet')
        fake_vip_port = stubs.FakeNeutronPort(
            id='ctlplane_vip_id',
            name='control_virtual_ip',
            fixed_ips=[{'subnet_id': 'ctlplane_subnet_id',
                        'ip_address': '4.3.2.1'}],
            dns_name='ctlplane.localdomain'
        )
        mock_conn.network.find_network.return_value = fake_network
        mock_conn.network.get_subnet.return_value = fake_subnet
        mock_conn.network.ports.return_value = self.a2g([fake_vip_port])

        vip_data = list()
        plugin.find_ctlplane_vip(mock_conn, vip_data)
        self.assertEqual([{'name': 'control_virtual_ip',
                           'network': 'ctlplane',
                           'subnet': 'ctlplane-subnet',
                           'ip_address': '4.3.2.1',
                           'dns_name': 'ctlplane.localdomain'}],
                         vip_data)
