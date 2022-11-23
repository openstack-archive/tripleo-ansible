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

import mock
import openstack

try:
    from ansible.module_utils import network_data_v2 as n_utils
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import network_data_v2 as n_utils  # noqa
from tripleo_ansible.ansible_plugins.modules import (
    tripleo_overcloud_network_extract as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs


class TestTripleoOvercloudNetworkExtract(tests_base.TestCase):

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_is_vip_network_true(self, conn_mock):
        net_name = 'external'
        net_id = '132f871f-eaec-4fed-9475-0d54465e0f00'
        fake_network = stubs.FakeNeutronNetwork(id=net_id,
                                                name=net_name,
                                                tags=['tripleo_vip=True'])
        fake_port = stubs.FakeNeutronPort(
            name='{}{}'.format(net_name, "IT_DOES_NOT_MATTER"),
            fixed_ips=[{'ip_address': '10.10.10.10', 'subnet_id': 'foo'}]
        )

        conn_mock.network.get_network.return_value = fake_network
        conn_mock.network.ports.return_value = (x for x in [fake_port])

        result = plugin.is_vip_network(conn_mock, net_id)
        self.assertEqual(True, result)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_is_vip_network_false(self, conn_mock):
        net_name = 'external'
        net_id = '132f871f-eaec-4fed-9475-0d54465e0f00'
        fake_network = stubs.FakeNeutronNetwork(id=net_id, name=net_name)

        conn_mock.network.get_network.return_value = fake_network
        conn_mock.network.ports.return_value = (x for x in [])

        result = plugin.is_vip_network(conn_mock, net_id)
        self.assertEqual(False, result)

    @mock.patch.object(plugin, 'is_vip_network', autospec=True,
                       return_value=False)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_get_network_info(self, conn_mock, is_vip_net_mock):
        fake_network = stubs.FakeNeutronNetwork(
            id='132f871f-eaec-4fed-9475-0d54465e0f00',
            name='public',
            dns_domain='public.localdomain.',
            mtu=1500,
            is_shared=False,
            is_admin_state_up=False,
            tags=['tripleo_net_idx=3',
                  'tripleo_service_net_map_replace=external']
        )
        conn_mock.network.get_network.return_value = fake_network
        expected = (3, {'name_lower': 'public',
                        'dns_domain': 'public.localdomain.',
                        'service_net_map_replace': 'external'})
        result = plugin.get_network_info(
            conn_mock, '132f871f-eaec-4fed-9475-0d54465e0f00')
        self.assertEqual(expected, result)

    @mock.patch.object(plugin, 'is_vip_network', autospec=True,
                       return_value=False)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_dns_not_set_get_network_info(self, conn_mock, is_vip_net_mock):
        fake_network = stubs.FakeNeutronNetwork(
            id='132f871f-eaec-4fed-9475-0d54465e0f00',
            name='public',
            dns_domain=None,
            mtu=1500,
            is_shared=False,
            is_admin_state_up=False,
            tags=['tripleo_net_idx=3',
                  'tripleo_service_net_map_replace=external']
        )
        conn_mock.network.get_network.return_value = fake_network
        expected = (3, {'name_lower': 'public',
                        'service_net_map_replace': 'external'})
        result = plugin.get_network_info(
            conn_mock, '132f871f-eaec-4fed-9475-0d54465e0f00')
        self.assertEqual(expected, result)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_get_subnet_info_ipv4(self, conn_mock):
        fake_subnet = stubs.FakeNeutronSubnet(
            name='public_subnet',
            is_dhcp_enabled=False,
            tags=['tripleo_vlan_id=100'],
            ip_version=4,
            cidr='10.0.0.0/24',
            allocation_pools=[{'start': '10.0.0.10', 'end': '10.0.0.150'}],
            gateway_ip='10.0.0.1',
            host_routes=[{'destination': '172.17.1.0/24',
                          'nexthop': '10.0.0.1'}],
        )
        fake_segment = stubs.FakeNeutronSegment(
            name='public_subnet',
            network_type='flat',
            physical_network='public_subnet'
        )
        conn_mock.network.get_subnet.return_value = fake_subnet
        conn_mock.network.get_segment.return_value = fake_segment
        expected = {
            'vlan': 100,
            'ip_subnet': '10.0.0.0/24',
            'allocation_pools': [{'start': '10.0.0.10', 'end': '10.0.0.150'}],
            'gateway_ip': '10.0.0.1',
            'routes': [{'destination': '172.17.1.0/24',
                        'nexthop': '10.0.0.1'}],
            'physical_network': 'public_subnet',
        }
        name, subnet = plugin.get_subnet_info(conn_mock, mock.Mock())
        self.assertEqual(name, 'public_subnet')
        self.assertEqual(expected, subnet)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_get_subnet_info_ipv4_no_gateway_ip(self, conn_mock):
        fake_subnet = stubs.FakeNeutronSubnet(
            name='public_subnet',
            is_dhcp_enabled=False,
            tags=['tripleo_vlan_id=100'],
            ip_version=4,
            cidr='10.0.0.0/24',
            allocation_pools=[{'start': '10.0.0.10', 'end': '10.0.0.150'}],
            gateway_ip=None,
            host_routes=[{'destination': '172.17.1.0/24',
                          'nexthop': '10.0.0.1'}],
        )
        fake_segment = stubs.FakeNeutronSegment(
            name='public_subnet',
            network_type='flat',
            physical_network='public_subnet'
        )
        conn_mock.network.get_subnet.return_value = fake_subnet
        conn_mock.network.get_segment.return_value = fake_segment
        expected = {
            'vlan': 100,
            'ip_subnet': '10.0.0.0/24',
            'allocation_pools': [{'start': '10.0.0.10', 'end': '10.0.0.150'}],
            'routes': [{'destination': '172.17.1.0/24',
                        'nexthop': '10.0.0.1'}],
            'physical_network': 'public_subnet',
        }
        name, subnet = plugin.get_subnet_info(conn_mock, mock.Mock())
        self.assertEqual(name, 'public_subnet')
        self.assertEqual(expected, subnet)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_get_subnet_info_ipv6(self, conn_mock):
        fake_subnet = stubs.FakeNeutronSubnet(
            name='public_subnet',
            is_dhcp_enabled=False,
            tags=['tripleo_vlan_id=200'],
            ip_version=6,
            cidr='2001:db8:a::/64',
            allocation_pools=[{'start': '2001:db8:a::0010',
                               'end': '2001:db8:a::fff9'}],
            gateway_ip='2001:db8:a::1',
            host_routes=[{'destination': '2001:db8:b::/64',
                          'nexthop': '2001:db8:a::1'}],
            ipv6_address_mode=None,
            ipv6_ra_mode=None,
        )
        fake_segment = stubs.FakeNeutronSegment(
            name='public_subnet',
            network_type='flat',
            physical_network='public_subnet'
        )
        conn_mock.network.get_subnet.return_value = fake_subnet
        conn_mock.network.get_segment.return_value = fake_segment
        expected = {
            'vlan': 200,
            'ipv6_subnet': '2001:db8:a::/64',
            'ipv6_allocation_pools': [{'start': '2001:db8:a::0010',
                                       'end': '2001:db8:a::fff9'}],
            'gateway_ipv6': '2001:db8:a::1',
            'routes_ipv6': [{'destination': '2001:db8:b::/64',
                             'nexthop': '2001:db8:a::1'}],
            'physical_network': 'public_subnet',
        }
        name, subnet = plugin.get_subnet_info(conn_mock, mock.Mock())
        self.assertEqual(name, 'public_subnet')
        self.assertEqual(expected, subnet)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_get_subnet_info_ipv6_no_gateway_ip(self, conn_mock):
        fake_subnet = stubs.FakeNeutronSubnet(
            name='public_subnet',
            is_dhcp_enabled=False,
            tags=['tripleo_vlan_id=200'],
            ip_version=6,
            cidr='2001:db8:a::/64',
            allocation_pools=[{'start': '2001:db8:a::0010',
                               'end': '2001:db8:a::fff9'}],
            gateway_ip=None,
            host_routes=[{'destination': '2001:db8:b::/64',
                          'nexthop': '2001:db8:a::1'}],
            ipv6_address_mode=None,
            ipv6_ra_mode=None,
        )
        fake_segment = stubs.FakeNeutronSegment(
            name='public_subnet',
            network_type='flat',
            physical_network='public_subnet'
        )
        conn_mock.network.get_subnet.return_value = fake_subnet
        conn_mock.network.get_segment.return_value = fake_segment
        expected = {
            'vlan': 200,
            'ipv6_subnet': '2001:db8:a::/64',
            'ipv6_allocation_pools': [{'start': '2001:db8:a::0010',
                                       'end': '2001:db8:a::fff9'}],
            'routes_ipv6': [{'destination': '2001:db8:b::/64',
                             'nexthop': '2001:db8:a::1'}],
            'physical_network': 'public_subnet',
        }
        name, subnet = plugin.get_subnet_info(conn_mock, mock.Mock())
        self.assertEqual(name, 'public_subnet')
        self.assertEqual(expected, subnet)

    @mock.patch.object(plugin, 'get_subnet_info', auto_spec=True)
    @mock.patch.object(plugin, 'get_network_info', auto_spec=True)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_parse_net_resources(self, conn_mock, mock_get_network,
                                 mock_get_subnet):
        net_resources = {
            'StorageNetwork': {
                'StorageNetwork': {'physical_resource_id': 'fake-id',
                                   'resource_type': n_utils.TYPE_NET},
                'StorageSubnet': {'physical_resource_id': 'fake-id',
                                  'resource_type': n_utils.TYPE_SUBNET},
                'StorageSubnet_leaf1': {'physical_resource_id': 'fake-id',
                                        'resource_type': n_utils.TYPE_SUBNET}
            }
        }

        fake_network = {
            'name_lower': 'storage',
            'dns_domain': 'storage.localdomain.',
            'mtu': 1500,
            'shared': False,
            'admin_state_up': False,
            'vip': False,
        }
        fake_subnet_storage = {
            'enable_dhcp': False,
            'vlan': 100,
            'ip_subnet': '10.0.0.0/24',
            'allocation_pools': [{'start': '10.0.0.10', 'end': '10.0.0.150'}],
            'gateway_ip': '10.0.0.1',
            'routes': [{'destination': '10.1.0.0/24', 'nexthop': '10.0.0.1'}],
            'network_type': 'flat',
            'physical_network': 'storage',
        }
        fake_subnet_storage_leaf1 = {
            'enable_dhcp': False,
            'vlan': 101,
            'ip_subnet': '10.1.0.0/24',
            'allocation_pools': [{'start': '10.1.0.10', 'end': '10.1.0.150'}],
            'gateway_ip': '10.1.0.1',
            'routes': [{'destination': '10.0.0.0/24', 'nexthop': '10.1.0.1'}],
            'network_type': 'flat',
            'physical_network': 'leaf1',
        }

        mock_get_network.return_value = (0, fake_network)
        mock_get_subnet.side_effect = [
            ('storage', fake_subnet_storage),
            ('leaf1', fake_subnet_storage_leaf1)]

        expected = [{'name': 'Storage',
                     'mtu': 1500,
                     'name_lower': 'storage',
                     'dns_domain': 'storage.localdomain.',
                     'shared': False,
                     'admin_state_up': False,
                     'vip': False,
                     'subnets': {
                         'storage': fake_subnet_storage,
                         'leaf1': fake_subnet_storage_leaf1}
                     }]
        result = plugin.parse_net_resources(conn_mock, net_resources)
        self.assertEqual(expected, result)
