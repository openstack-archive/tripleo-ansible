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

import mock
import openstack

from tripleo_ansible.ansible_plugins.modules import (
    tripleo_composable_network as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs


class TestTripleoComposableNetwork(tests_base.TestCase):

    def test_build_network_tag_field(self):
        idx = 3
        net_data = {'name': 'foo',
                    'service_net_map_replace': 'replacement',
                    'vip': True}
        expected = ['tripleo_network_name=foo',
                    'tripleo_net_idx=3',
                    'tripleo_service_net_map_replace=replacement',
                    'tripleo_vip=true']
        result = plugin.build_network_tag_field(net_data, idx)
        self.assertEqual(expected, result)

        idx = 1
        net_data = {'name': 'foo'}
        expected = ['tripleo_network_name=foo',
                    'tripleo_net_idx=1']
        result = plugin.build_network_tag_field(net_data, idx)
        self.assertEqual(expected, result)

    def test_build_subnet_tag_field(self):
        # Default VLAN id 1
        subnet_data = {}
        expected = ["tripleo_vlan_id=1"]
        result = plugin.build_subnet_tag_field(subnet_data)
        self.assertEqual(expected, result)

        subnet_data = {'vlan': 100}
        expected = ["tripleo_vlan_id=100"]
        result = plugin.build_subnet_tag_field(subnet_data)
        self.assertEqual(expected, result)

    def test_create_net_spec(self):
        idx = 3
        net_data = {'name': 'NetName'}
        overcloud_domain_name = 'example.com.'
        expected = {
            'admin_state_up': plugin.DEFAULT_ADMIN_STATE,
            'dns_domain': '.'.join(['netname', overcloud_domain_name]),
            'mtu': plugin.DEFAULT_MTU,
            'name': 'netname',
            'shared': plugin.DEFAULT_SHARED,
            'provider:physical_network': 'netname',
            'provider:network_type': plugin.DEFAULT_NETWORK_TYPE,
            'tags': ['tripleo_network_name=NetName',
                     'tripleo_net_idx=3'],
        }

        result = plugin.create_net_spec(net_data, overcloud_domain_name, idx)
        self.assertEqual(expected, result)

    def test_validate_network_update(self):
        net_spec = {
            'admin_state_up': True,
            'dns_domain': 'netname.localdomain',
            'mtu': 1450,
            'name': 'new_name',
            'shared': True,
            'provider:physical_network': 'NEWNAME',
            'provider:network_type': 'vlan',
            'provider:segmentation_id': 101
        }
        fake_network = stubs.FakeNeutronNetwork(**{
            'is_admin_state_up': False,
            'mtu': 1500,
            'is_shared': False,
            'provider:network_type': 'flat',
            'provider:physical_network': 'netname',
            'provider:segmentation_id': 100,
            'dns_domain': 'netname.localdomain',
            'name': 'netname'})
        module = mock.Mock()
        module.fail_json = mock.Mock()
        result = plugin.validate_network_update(module, fake_network, net_spec)
        module.fail_json.assert_has_calls([
            mock.call(msg=('Cannot update provider:network_type in existing '
                           'network')),
            mock.call(msg=('Cannot update provider:physical_network in '
                           'existing network'))
        ])
        expected = {'mtu': 1450,
                    'shared': True,
                    'admin_state_up': True,
                    'name': 'new_name',
                    'provider:segmentation_id': 101}
        self.assertEqual(expected, result)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_create_network(self, mock_conn):
        mock_module = mock.Mock()
        net_spec = {
            'admin_state_up': plugin.DEFAULT_ADMIN_STATE,
            'dns_domain': '.'.join(['netname', plugin.DEFAULT_DOMAIN]),
            'mtu': plugin.DEFAULT_MTU,
            'name': 'netname',
            'shared': plugin.DEFAULT_SHARED,
            'provider:physical_network': 'netname',
            'provider:network_type': plugin.DEFAULT_NETWORK_TYPE,
            'tags': ['tripleo_foo=bar'],
        }
        fake_network = stubs.FakeNeutronNetwork(
            id='foo',
            name='netname',
            is_shared=False,
            dns_domain='.'.join(['netname', plugin.DEFAULT_DOMAIN]),
            mtu=plugin.DEFAULT_MTU,
            is_admin_state_up=plugin.DEFAULT_ADMIN_STATE,
            physical_network='netname',
            network_type=plugin.DEFAULT_NETWORK_TYPE,
            tags=[],
        )
        mock_conn.network.find_network.return_value = None
        mock_conn.network.create_network.return_value = fake_network
        changed, network = plugin.create_or_update_network(
            mock_conn, mock_module, net_spec)
        mock_conn.network.create_network.assert_called_once_with(**net_spec)
        mock_conn.network.set_tags.assert_called_once_with(
            network, ['tripleo_foo=bar'])
        self.assertEqual(True, changed)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_update_network(self, mock_conn):
        mock_module = mock.Mock()
        net_spec = {
            'admin_state_up': plugin.DEFAULT_ADMIN_STATE,
            'dns_domain': '.'.join(['netname', plugin.DEFAULT_DOMAIN]),
            'mtu': plugin.DEFAULT_MTU,
            'name': 'new_name',
            'shared': plugin.DEFAULT_SHARED,
            'provider:physical_network': 'netname',
            'provider:network_type': plugin.DEFAULT_NETWORK_TYPE,
            'tags': ['tripleo_foo=bar'],
        }
        fake_network = stubs.FakeNeutronNetwork(
            id='foo',
            name='netname',
            is_shared=False,
            dns_domain='.'.join(['netname', plugin.DEFAULT_DOMAIN]),
            mtu=plugin.DEFAULT_MTU,
            is_admin_state_up=plugin.DEFAULT_ADMIN_STATE,
            physical_network='netname',
            network_type=plugin.DEFAULT_NETWORK_TYPE,
            tags=[],
        )
        mock_conn.network.find_network.return_value = fake_network
        changed, network = plugin.create_or_update_network(
            mock_conn, mock_module, net_spec)
        mock_conn.network.update_network.assert_called_once_with(
            'foo', **{'name': 'new_name'})
        mock_conn.network.set_tags.assert_called_once_with(
            network, ['tripleo_foo=bar'])
        self.assertEqual(True, changed)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_update_network_no_change(self, mock_conn):
        mock_module = mock.Mock()
        net_spec = {
            'admin_state_up': plugin.DEFAULT_ADMIN_STATE,
            'dns_domain': '.'.join(['netname', plugin.DEFAULT_DOMAIN]),
            'mtu': plugin.DEFAULT_MTU,
            'name': 'netname',
            'shared': plugin.DEFAULT_SHARED,
            'provider:physical_network': 'netname',
            'provider:network_type': plugin.DEFAULT_NETWORK_TYPE,
            'tags': ['tripleo_foo=bar'],
        }
        fake_network = stubs.FakeNeutronNetwork(
            id='foo',
            name='netname',
            is_shared=False,
            dns_domain='.'.join(['netname', plugin.DEFAULT_DOMAIN]),
            mtu=plugin.DEFAULT_MTU,
            is_admin_state_up=plugin.DEFAULT_ADMIN_STATE,
            physical_network='netname',
            network_type=plugin.DEFAULT_NETWORK_TYPE,
            tags=['tripleo_foo=bar'],
        )
        mock_conn.network.find_network.return_value = fake_network
        changed, network = plugin.create_or_update_network(
            mock_conn, mock_module, net_spec)
        mock_conn.network.create_network.assert_not_called()
        mock_conn.network.update_network.assert_not_called()
        mock_conn.network.set_tags.assert_not_called()
        self.assertEqual(False, changed)

    def test_create_segment_spec(self):
        net_id = 'net_id'
        net_name = 'net_name'
        subnet_name = 'subnet_name'
        expected = {'network_id': 'net_id', 'name': 'net_name_subnet_name',
                    'physical_network': 'net_name_subnet_name',
                    'network_type': plugin.DEFAULT_NETWORK_TYPE}
        result = plugin.create_segment_spec(net_id, net_name, subnet_name)
        self.assertEqual(expected, result)

    def test_validate_segment_update(self):
        segmnet_spec = {
            'network_id': 'new_net_id',
            'physical_network': 'new_physical_network',
            'name': 'new_name',
            'network_type': 'vlan',
        }
        fake_segment = stubs.FakeNeutronSegment(
            name='net_name_subnet_name',
            network_id='net_id',
            network_type=plugin.DEFAULT_NETWORK_TYPE,
            physical_network='net_name_subnet_name'
        )

        module = mock.Mock()
        module.fail_json = mock.Mock()
        result = plugin.validate_segment_update(
            module, fake_segment, segmnet_spec)
        module.fail_json.assert_has_calls([
            mock.call(msg='Cannot update network_id in existing segment'),
            mock.call(msg='Cannot update network_type in existing segment'),
            mock.call(msg='Cannot update physical_network in existing segment')
        ])
        expected = {'name': 'new_name'}
        self.assertEqual(expected, result)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_create_segment(self, mock_conn):
        mock_module = mock.Mock()
        segment_spec = {'network_id': 'net_id', 'name': 'net_name_subnet_name',
                        'physical_network': 'net_name_subnet_name',
                        'network_type': plugin.DEFAULT_NETWORK_TYPE}
        mock_conn.network.find_segment.return_value = None
        changed, segment = plugin.create_or_update_segment(
            mock_conn, mock_module, segment_spec)
        mock_conn.network.create_segment.assert_called_once_with(
            **segment_spec)
        self.assertEqual(True, changed)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_update_segment(self, mock_conn):
        mock_module = mock.Mock()
        segment_spec = {'network_id': 'net_id',
                        'physical_network': 'net_name_subnet_name',
                        'name': 'NEW_NAME',
                        'network_type': plugin.DEFAULT_NETWORK_TYPE}
        fake_segment = stubs.FakeNeutronSegment(
            id='foo', name='net_name_subnet_name', network_id='net_id',
            network_type=plugin.DEFAULT_NETWORK_TYPE,
            physical_network='net_name_subnet_name')
        mock_conn.network.find_segment.return_value = fake_segment
        changed, segment = plugin.create_or_update_segment(
            mock_conn, mock_module, segment_spec, segment_id='foo')
        mock_conn.network.find_segment.assert_called_once_with('foo')
        mock_conn.network.update_segment.assert_called_once_with(
            fake_segment.id, **{'name': 'NEW_NAME'})
        self.assertEqual(True, changed)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_update_segment_no_change(self, mock_conn):
        mock_module = mock.Mock()
        segment_spec = {'network_id': 'net_id',
                        'physical_network': 'net_name_subnet_name',
                        'name': 'net_name_subnet_name',
                        'network_type': plugin.DEFAULT_NETWORK_TYPE}
        fake_segment = stubs.FakeNeutronSegment(
            id='foo', name='net_name_subnet_name', network_id='net_id',
            network_type=plugin.DEFAULT_NETWORK_TYPE,
            physical_network='net_name_subnet_name')
        mock_conn.network.find_segment.return_value = fake_segment
        changed, segment = plugin.create_or_update_segment(
            mock_conn, mock_module, segment_spec)
        mock_conn.network.find_segment.assert_called_once_with(
            'net_name_subnet_name', network_id='net_id')
        mock_conn.network.create_segment.assert_not_called()
        mock_conn.network.update_segment.assert_not_called()
        self.assertEqual(False, changed)

    def test_create_subnet_spec_ipv4(self):
        net_id = 'net_id'
        name = 'subnet0'
        subnet_data = {
            'ip_subnet': '192.168.24.0/24',
            'gateway_ip': '192.168.24.1',
            'allocation_pools': [
                {'start': '192.168.24.100', 'end': '192.168.24.200'}
            ],
            'routes': [
                {'destination': '192.168.25.0/24', 'nexthop': '192.168.24.1'}
            ],
            'vlan': 100,
        }
        expected = {
            'ip_version': 4,
            'name': name,
            'network_id': net_id,
            'enable_dhcp': False,
            'gateway_ip': '192.168.24.1',
            'cidr': '192.168.24.0/24',
            'allocation_pools': [
                {'start': '192.168.24.100', 'end': '192.168.24.200'}
            ],
            'host_routes': [
                {'destination': '192.168.25.0/24', 'nexthop': '192.168.24.1'}
            ],
            'tags': ['tripleo_vlan_id=100'],
        }
        subnet_v4_spec, subnet_v6_spec = plugin.create_subnet_spec(
            net_id, name, subnet_data)
        self.assertEqual(expected, subnet_v4_spec)
        self.assertEqual(None, subnet_v6_spec)

    def test_create_subnet_spec_ipv6(self):
        net_id = 'net_id'
        name = 'subnet0'
        subnet_data = {
            'ipv6_subnet': '2001:db8:a::/64',
            'gateway_ipv6': '2001:db8:a::1',
            'vlan': 100,
        }
        expected = {
            'ip_version': 6,
            'name': name,
            'network_id': net_id,
            'enable_dhcp': False,
            'gateway_ip': '2001:db8:a::1',
            'cidr': '2001:db8:a::/64',
            'allocation_pools': [],
            'host_routes': [],
            'tags': ['tripleo_vlan_id=100'],
        }
        subnet_v4_spec, subnet_v6_spec = plugin.create_subnet_spec(
            net_id, name, subnet_data, True)
        self.assertEqual(None, subnet_v4_spec)
        self.assertEqual(expected, subnet_v6_spec)

    def test_create_subnet_spec_both_ipv4_ipv6(self):
        net_id = 'net_id'
        name = 'subnet0'
        subnet_data = {
            'ip_subnet': '192.168.24.0/24',
            'gateway_ip': '192.168.24.1',
            'allocation_pools': [
                {'start': '192.168.24.100', 'end': '192.168.24.200'}],
            'routes': [
                {'destination': '192.168.25.0/24', 'nexthop': '192.168.24.1'}],
            'ipv6_subnet': '2001:db8:a::/64',
            'gateway_ipv6': '2001:db8:a::1',
            'ipv6_allocation_pools': [
                {'start': '2001:db8:a::0010', 'end': '2001:db8:a::fff9'}
            ],
            'routes_ipv6': [
                {'destination': '2001:db8:b::/64', 'nexthop': '2001:db8:a::1'}
            ],
            'vlan': 100,
        }
        expected_ipv4 = {
            'ip_version': 4,
            'name': name,
            'network_id': net_id,
            'enable_dhcp': False,
            'gateway_ip': '192.168.24.1',
            'cidr': '192.168.24.0/24',
            'allocation_pools': [
                {'start': '192.168.24.100', 'end': '192.168.24.200'}
            ],
            'host_routes': [
                {'destination': '192.168.25.0/24', 'nexthop': '192.168.24.1'}
            ],
            'tags': ['tripleo_vlan_id=100'],
        }
        expected_ipv6 = {
            'ip_version': 6,
            'name': name,
            'network_id': net_id,
            'enable_dhcp': False,
            'gateway_ip': '2001:db8:a::1',
            'cidr': '2001:db8:a::/64',
            'allocation_pools': [
                {'start': '2001:db8:a::0010', 'end': '2001:db8:a::fff9'}
            ],
            'host_routes': [
                {'destination': '2001:db8:b::/64', 'nexthop': '2001:db8:a::1'}
            ],
            'tags': ['tripleo_vlan_id=100'],
        }
        subnet_v4_spec, subnet_v6_spec = plugin.create_subnet_spec(
            net_id, name, subnet_data)
        self.assertEqual(expected_ipv4, subnet_v4_spec)
        self.assertEqual(None, subnet_v6_spec)
        subnet_v4_spec, subnet_v6_spec = plugin.create_subnet_spec(
            net_id, name, subnet_data, True)
        self.assertEqual(None, subnet_v4_spec)
        self.assertEqual(expected_ipv6, subnet_v6_spec)

    def test_validate_subnet_update(self):
        module = mock.Mock()
        module.fail = mock.Mock()
        subnet_spec = {
            'ip_version': 6,
            'network_id': 'new_net_id',
            'cidr': '192.168.24.0/25',
            'segment_id': 'new_segment_id',
            'name': 'new_name',
            'enable_dhcp': True,
            'ipv6_address_mode': 'slaac',
            'ipv6_ra_mode': 'slaac',
            'gateway_ip': '192.168.24.254',
            'allocation_pools': [{'start': '192.168.24.100', 'end': '200'}],
            'host_routes': [
                {'destination': '192.168.25.0/24', 'nexthop': '192.168.24.254'}
            ],
        }
        fake_subnet = stubs.FakeNeutronSubnet(
            id='foo',
            name='subnet01',
            cidr='192.168.24.0/24',
            gateway_ip='192.168.24.1',
            allocation_pools=[{'start': '192.168.24.50', 'end': '99'}],
            host_routes={'destination': '192.168.25.0/24',
                         'nexthop': '192.168.24.1'},
            ip_version=4,
            network_id='net_id',
            segment_id='segment_id',
            is_dhcp_enabled=False,

        )
        result = plugin.validate_subnet_update(
            module, fake_subnet, subnet_spec)
        module.fail_json.assert_has_calls([
            mock.call(msg='Cannot update ip_version in existing subnet'),
            mock.call(msg='Cannot update network_id in existing subnet'),
            mock.call(msg='Cannot update cidr in existing subnet'),
            mock.call(
                msg='Cannot update segment_id in existing subnet, Current '
                    'segment_id: {} Update segment_id: {}'.format(
                    'segment_id', 'new_segment_id')
            ),
        ])
        expected_spec = {
            'name': 'new_name',
            'enable_dhcp': True,
            'ipv6_address_mode': 'slaac',
            'ipv6_ra_mode': 'slaac',
            'gateway_ip': '192.168.24.254',
            'allocation_pools': [{'start': '192.168.24.100', 'end': '200'}],
            'host_routes': [
                {'destination': '192.168.25.0/24', 'nexthop': '192.168.24.254'}
            ],
        }
        self.assertEqual(expected_spec, result)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_create_subnet(self, mock_conn):
        mock_module = mock.Mock()
        subnet_spec = {
            'ip_version': 4,
            'name': 'subnet_name',
            'network_id': 'net_id',
            'enable_dhcp': False,
            'gateway_ip': '192.168.24.1',
            'cidr': '192.168.24.0/24',
            'allocation_pools': [
                {'start': '192.168.24.100', 'end': '192.168.24.200'}
            ],
            'host_routes': [
                {'destination': '192.168.25.0/24', 'nexthop': '192.168.24.1'}
            ],
            'tags': ['tripleo_vlan_id=100'],
        }
        mock_conn.network.find_subnet.return_value = None
        changed = plugin.create_or_update_subnet(mock_conn, mock_module,
                                                 subnet_spec)
        mock_conn.network.create_subnet.assert_called_once_with(**subnet_spec)
        mock_conn.network.set_tags.assert_called_once_with(
            mock.ANY, ['tripleo_vlan_id=100'])
        self.assertEqual(True, changed)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_update_subnet(self, mock_conn):
        mock_module = mock.Mock()
        subnet_spec = {
            'ip_version': 4,
            'name': 'subnet_name',
            'network_id': 'net_id',
            'enable_dhcp': False,
            'gateway_ip': '192.168.24.1',
            'cidr': '192.168.24.0/24',
            'allocation_pools': [
                {'start': '192.168.24.100', 'end': '192.168.24.200'}
            ],
            'host_routes': [
                {'destination': '192.168.25.0/24', 'nexthop': '192.168.24.1'}
            ],
            'tags': ['tripleo_vlan_id=100'],
            'segment_id': 'segment_id',
        }
        fake_subnet = stubs.FakeNeutronSubnet(
            id='foo',
            name='subnet_name',
            network_id='net_id',
            is_dhcp_enabled=False,
            gateway_ip='192.168.24.254',
            cidr='192.168.24.0/24',
            allocation_pools=[
                {'start': '192.168.24.100', 'end': '192.168.24.200'}],
            host_routes=[
                {'destination': '192.168.25.0/24', 'nexthop': '192.168.24.254'}
            ],
            tags=['tripleo_vlan_id=100'],
            segment_id='segment_id'
        )
        mock_conn.network.find_subnet.return_value = fake_subnet
        changed = plugin.create_or_update_subnet(mock_conn, mock_module,
                                                 subnet_spec)
        mock_conn.network.find_subnet.ssert_called_once_with(
            'subnet_name', network_id='net_id')
        mock_conn.network.create_subnet.assert_not_called()
        mock_conn.network.update_subnet.assert_called_once_with(
            'foo', **{'gateway_ip': '192.168.24.1',
                      'host_routes': [{'destination': '192.168.25.0/24',
                                       'nexthop': '192.168.24.1'}]}
        )
        self.assertTrue(changed)

    @mock.patch.object(plugin, 'create_segment_spec', autospec=True)
    @mock.patch.object(plugin, 'create_or_update_segment', autospec=True)
    def test_adopt_the_implicit_segment(self, mock_create_or_update_segment,
                                        mock_create_segment_spec):
        fake_network = stubs.FakeNeutronNetwork(id='net_id', name='net_name')
        fake_segments = [
            stubs.FakeNeutronSegment(id='segment_id', name=None,
                                     physical_network='physical_net')]
        fake_subnets = [
            stubs.FakeNeutronSubnet(id='subnet_id', name='subnet_name',
                                    segment_id='segment_id')]

        changed = plugin.adopt_the_implicit_segment(
            mock.ANY, mock.ANY, fake_segments, fake_subnets, fake_network)

        mock_create_segment_spec.assert_called_once_with(
            fake_network.id, fake_network.name, fake_subnets[0].name,
            physical_network=fake_segments[0].physical_network)
        mock_create_or_update_segment.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, segment_id=fake_segments[0].id)
        self.assertTrue(changed)

    def test_implicit_segment_already_adopted(self):
        fake_segments = [
            stubs.FakeNeutronSegment(id='segment_id',
                                     name='net_name_subnet_name',
                                     physical_network='physical_net')]

        changed = plugin.adopt_the_implicit_segment(
            mock.ANY, mock.ANY, fake_segments, mock.ANY, mock.ANY)
        self.assertFalse(changed)

    def test_implicit_segment_unable_to_adopt(self):
        mock_module = mock.Mock()
        mock_module.fail_json = mock.Mock()
        fake_network = stubs.FakeNeutronNetwork(id='net_id', name='net_name')
        fake_segments = [
            stubs.FakeNeutronSegment(id='segment_id_01',
                                     name=None,
                                     network_id='net_id',
                                     physical_network='physical_net_01'),
            stubs.FakeNeutronSegment(id='segment_id_02',
                                     name=None,
                                     network_id='net_id',
                                     physical_network='physical_net_02')
        ]
        fake_subnets = []

        try:
            plugin.adopt_the_implicit_segment(
                mock.Mock(), mock_module, fake_segments, fake_subnets,
                fake_network)
        except AttributeError:
            mock_module.fail_json.assert_called_once_with(
                msg='Multiple segments with no name attribute exist on '
                    'network {}, unable to reliably adopt the implicit '
                    'segment.'.format(fake_network.id))

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_get_overcloud_domain_name(self, mock_conn):
        mock_conn.network.find_network.return_value = stubs.FakeNeutronNetwork(
            dns_domain='ctlplane.example.com.')
        self.assertEqual(
            'example.com.',
            plugin.get_overcloud_domain_name(mock_conn, 'ctlplane'))

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_get_overcloud_domain_name_no_ctlplane_network(self, mock_conn):
        mock_conn.network.find_network.return_value = None
        self.assertEqual(
            plugin.DEFAULT_DOMAIN,
            plugin.get_overcloud_domain_name(mock_conn, 'ctlplane')
        )

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_get_overcloud_domain_name_no_ctlplane_dns_domain(self, mock_conn):
        mock_conn.network.find_network.return_value = stubs.FakeNeutronNetwork(
            dns_domain='')
        self.assertEqual(
            plugin.DEFAULT_DOMAIN,
            plugin.get_overcloud_domain_name(mock_conn, 'ctlplane')
        )
