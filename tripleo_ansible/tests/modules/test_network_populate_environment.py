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

from tripleo_ansible.ansible_plugins.modules import (
    tripleo_network_populate_environment as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs


class TestNetworkPopulateEnvironment(tests_base.TestCase):

    def test_get_net_ip_version(self):
        net_data = {}
        subnets = [stubs.FakeNeutronSubnet(ip_version=4),
                   stubs.FakeNeutronSubnet(ip_version=4)]
        self.assertEqual(4, plugin.get_net_ip_version(subnets, net_data))
        subnets = [stubs.FakeNeutronSubnet(ip_version=6),
                   stubs.FakeNeutronSubnet(ip_version=6)]
        self.assertEqual(6, plugin.get_net_ip_version(subnets, net_data))
        subnets = [stubs.FakeNeutronSubnet(ip_version=4),
                   stubs.FakeNeutronSubnet(ip_version=6)]
        self.assertEqual(4, plugin.get_net_ip_version(subnets, net_data))
        net_data = {'ipv6': True}
        self.assertEqual(6, plugin.get_net_ip_version(subnets, net_data))

    def test_get_net_cidrs(self):
        subnets = [
            stubs.FakeNeutronSubnet(cidr='192.168.24.0/24', ip_version=4),
            stubs.FakeNeutronSubnet(cidr='192.168.25.0/24', ip_version=4),
            stubs.FakeNeutronSubnet(cidr='2001:db8:a::/64', ip_version=6),
            stubs.FakeNeutronSubnet(cidr='2001:db8:b::/64', ip_version=6)]
        self.assertEqual(['192.168.24.0/24', '192.168.25.0/24'],
                         plugin.get_net_cidrs(subnets, 4))
        self.assertEqual(['2001:db8:a::/64', '2001:db8:b::/64'],
                         plugin.get_net_cidrs(subnets, 6))

    def test_get_network_attrs(self):
        expected = {'name': 'net_name',
                    'mtu': 1500,
                    'dns_domain': 'netname.localdomain.',
                    'tags': ['tripleo_vlan_id=100']}
        fake_network = stubs.FakeNeutronNetwork(
            id='net_id', name='net_name', mtu=1500,
            dns_domain='netname.localdomain.', tags=['tripleo_vlan_id=100'])
        self.assertEqual(expected, plugin.get_network_attrs(fake_network))

    def test_get_subnet_attrs(self):
        fake_subnet = stubs.FakeNeutronSubnet(
            name='subnet_name', cidr='192.168.24.0/24',
            gateway_ip='192.168.24.1', host_routes=[],
            dns_nameservers=['192.168.24.254', '192.168.24.253'],
            ip_version=4, tags=['tripleo_vlan_id=1'])
        expected = {'name': 'subnet_name',
                    'cidr': '192.168.24.0/24',
                    'gateway_ip': '192.168.24.1',
                    'host_routes': [],
                    'dns_nameservers': ['192.168.24.254', '192.168.24.253'],
                    'ip_version': 4, 'tags': ['tripleo_vlan_id=1']}
        name, attrs = plugin.get_subnet_attrs(fake_subnet)
        self.assertEqual('subnet_name', name)
        self.assertEqual(expected, attrs)

    def test_get_subnets_attrs(self):
        fake_subnets = [
            stubs.FakeNeutronSubnet(
                name='subnet01', cidr='192.168.24.0/24',
                gateway_ip='192.168.24.1',
                host_routes=[{'destination': '192.168.24.0/24',
                              'nexthop': '192.168.25.1'}],
                dns_nameservers=['192.168.24.254', '192.168.24.253'],
                ip_version=4, tags=['tripleo_vlan_id=24']),
            stubs.FakeNeutronSubnet(
                name='subnet02', cidr='192.168.25.0/24',
                gateway_ip='192.168.25.1',
                host_routes=[{'destination': '192.168.24.0/24',
                              'nexthop': '192.168.25.1'}],
                dns_nameservers=['192.168.25.254', '192.168.25.253'],
                ip_version=4, tags=['tripleo_vlan_id=25'])
        ]
        expected = {
            'subnet01': {'name': 'subnet01',
                         'cidr': '192.168.24.0/24',
                         'gateway_ip': '192.168.24.1',
                         'host_routes': [{'destination': '192.168.24.0/24',
                                          'nexthop': '192.168.25.1'}],
                         'dns_nameservers': ['192.168.24.254',
                                             '192.168.24.253'],
                         'ip_version': 4, 'tags': ['tripleo_vlan_id=24']},
            'subnet02': {'name': 'subnet02',
                         'cidr': '192.168.25.0/24',
                         'gateway_ip': '192.168.25.1',
                         'host_routes': [{'destination': '192.168.24.0/24',
                                          'nexthop': '192.168.25.1'}],
                         'dns_nameservers': ['192.168.25.254',
                                             '192.168.25.253'],
                         'ip_version': 4, 'tags': ['tripleo_vlan_id=25']}
        }
        self.assertEqual(expected, plugin.get_subnets_attrs(fake_subnets))

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_set_composable_network_attrs(self, mock_conn):
        module = mock.Mock()
        net_data = {'name': 'NetName'}
        fake_network = stubs.FakeNeutronNetwork(
            id='net_id', name='netname', mtu=1500,
            dns_domain='netname.localdomain.', tags=['tripleo_vlan_id=100'],
            subnet_ids=['subnet01_id', 'subnet02_id'])
        fake_subnets = [
            stubs.FakeNeutronSubnet(
                name='subnet01', cidr='192.168.24.0/24',
                gateway_ip='192.168.24.1',
                host_routes=[{'destination': '192.168.24.0/24',
                              'nexthop': '192.168.25.1'}],
                dns_nameservers=['192.168.24.254', '192.168.24.253'],
                ip_version=4, tags=['tripleo_vlan_id=24']),
            stubs.FakeNeutronSubnet(
                name='subnet02', cidr='192.168.25.0/24',
                gateway_ip='192.168.25.1',
                host_routes=[{'destination': '192.168.24.0/24',
                              'nexthop': '192.168.25.1'}],
                dns_nameservers=['192.168.25.254', '192.168.25.253'],
                ip_version=4, tags=['tripleo_vlan_id=25'])]
        mock_conn.network.find_network.return_value = fake_network
        mock_conn.network.get_subnet.side_effect = fake_subnets
        attrs = dict()
        cidr_map = dict()
        ip_version_map = dict()
        plugin.set_composable_network_attrs(
            module, mock_conn, net_data['name'].lower(), net_data,
            attrs=attrs, cidr_map=cidr_map, ip_version_map=ip_version_map)
        mock_conn.network.find_network.assert_called_with(
            net_data['name'].lower())
        mock_conn.network.get_subnet.assert_has_calls(
            [mock.call('subnet01_id'), mock.call('subnet02_id')])
        self.assertEqual(
            {'network': {'dns_domain': 'netname.localdomain.', 'mtu': 1500,
                         'name': 'netname', 'tags': ['tripleo_vlan_id=100']},
             'subnets': {'subnet01': {'name': 'subnet01',
                                      'cidr': '192.168.24.0/24',
                                      'gateway_ip': '192.168.24.1',
                                      'host_routes': [{
                                          'destination': '192.168.24.0/24',
                                          'nexthop': '192.168.25.1'}],
                                      'dns_nameservers': ['192.168.24.254',
                                                          '192.168.24.253'],
                                      'ip_version': 4,
                                      'tags': ['tripleo_vlan_id=24']},
                         'subnet02': {'name': 'subnet02',
                                      'cidr': '192.168.25.0/24',
                                      'gateway_ip': '192.168.25.1',
                                      'host_routes': [{
                                          'destination': '192.168.24.0/24',
                                          'nexthop': '192.168.25.1'}],
                                      'dns_nameservers': ['192.168.25.254',
                                                          '192.168.25.253'],
                                      'ip_version': 4,
                                      'tags': ['tripleo_vlan_id=25']}}}, attrs)
        self.assertEqual({'netname': 4}, ip_version_map)
        self.assertEqual({'netname': ['192.168.24.0/24', '192.168.25.0/24']},
                         cidr_map)
