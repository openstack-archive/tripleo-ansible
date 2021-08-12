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

import copy
import mock
import yaml

import openstack

from tripleo_ansible.tests import base as tests_base

from tripleo_ansible.ansible_plugins.module_utils import network_data_v2
from tripleo_ansible.tests import stubs


NET_DATA = yaml.safe_load('''
---
name: Storage
name_lower: storage
admin_state_up: false
dns_domain: storage.localdomain.
mtu: 1442
shared: false
service_net_map_replace: storage
ipv6: true
vip: true
subnets:
  subnet01:
    ip_subnet: 172.18.1.0/24
    gateway_ip: 172.18.1.254
    allocation_pools:
      - start: 172.18.1.1
        end: 172.18.1.250
    routes:
      - destination: 172.18.0.0/24
        nexthop: 172.18.1.254
    ipv6_subnet: 2001:db8:a::/64
    gateway_ipv6: 2001:db8:a::1
    ipv6_allocation_pools:
      - start: 2001:db8:a::0010
        end: 2001:db8:a::fff9
    routes_ipv6:
      - destination: 2001:db8:b::/64
        nexthop: 2001:db8:a::1
    ipv6_address_mode: slaac
    ipv6_ra_mode: slaac
    enable_dhcp: false
    physical_network: storage_subnet01
    network_type: flat
    segmentation_id: 21
    vlan: 21
  subnet02:
    ip_subnet: 172.18.0.0/24
    gateway_ip: 172.18.0.254
    allocation_pools:
      - start: 172.18.0.10
        end: 172.18.0.250
    routes:
      - destination: 172.18.1.0/24
        nexthop: 172.18.0.254
    ipv6_subnet: 2001:db8:b::/64
    gateway_ipv6: 2001:db8:b::1
    ipv6_allocation_pools:
      - start: 2001:db8:b::0010
        end: 2001:db8:b::fff9
    routes_ipv6:
      - destination: 2001:db8:a::/64
        nexthop: 2001:db8:b::1
    ipv6_address_mode: slaac
    ipv6_ra_mode: slaac
    enable_dhcp: false
    physical_network: storage_subnet01
    network_type: flat
    segmentation_id: 21
    vlan: 20
''')

IPV4_SUBNET_KEYS = {'ip_subnet', 'allocation_pools', 'routes', 'gateway_ip'}
IPV6_SUBNET_KEYS = {'ipv6_subnet', 'ipv6_allocation_pools', 'routes_ipv6',
                    'gateway_ipv6', 'ipv6_address_mode', 'ipv6_ra_mode'}


class TestNetworkDataV2(tests_base.TestCase):

    def setUp(self):
        super(TestNetworkDataV2, self).setUp()
        # Helper function to convert array to generator
        self.a2g = lambda x: (n for n in x)

    def test_validator_ok(self):
        ipv4_only = copy.deepcopy(NET_DATA)
        ipv6_only = copy.deepcopy(NET_DATA)
        ipv4_only.pop('ipv6')
        for name, subnet in ipv4_only['subnets'].items():
            [subnet.pop(k) for k in IPV6_SUBNET_KEYS]
        for name, subnet in ipv6_only['subnets'].items():
            [subnet.pop(k) for k in IPV4_SUBNET_KEYS]

        error_messages = network_data_v2.validate_json_schema(NET_DATA)
        self.assertEqual([], error_messages)
        error_messages = network_data_v2.validate_json_schema(ipv4_only)
        self.assertEqual([], error_messages)
        error_messages = network_data_v2.validate_json_schema(ipv6_only)
        self.assertEqual([], error_messages)

    def test_validator_fail(self):
        dual = copy.deepcopy(NET_DATA)
        dual.pop('name')  # Required
        dual['mtu'] = 400  # too low
        dual['ipv6'] = 'not_bool'
        dual['vip'] = 'not_bool'
        dual['admin_state_up'] = 'not_bool'
        dual['shared'] = 'not_bool'
        dual['invalid_key'] = 'foo'
        s02 = dual['subnets']['subnet02']
        s02['ip_subnet'] = 'invalid'
        s02['gateway_ip'] = '2001:db8:a::1'  # Wrong ip version
        s02['allocation_pools'][0]['foo'] = 'foo'  # Invalid key
        s02['allocation_pools'][0]['start'] = '2001:db8:a::1'
        s02['routes'][0]['foo'] = 'foo'  # Invalid key
        s02['routes'][0]['nexthop'] = '172222.18.1.254'
        s02['routes'][0]['destination'] = '172.18.0.0/99'  # netmask error
        s02['enable_dhcp'] = 'not_a_bool'
        s02['physical_network'] = dict()  # Invalid, should be string
        s02['network_type'] = 'invalid'
        s02['vlan'] = 'not_an_int'
        s02['ipv6_subnet'] = 'invalid'
        s02['gateway_ipv6'] = '172.18.1.254'  # Wrong ip version
        s02['ipv6_allocation_pools'][0]['v6_invalid_key'] = 'foo'
        s02['ipv6_allocation_pools'][0]['end'] = '172.18.1.20'
        s02['routes_ipv6'][0]['v6_invalid_key'] = 'foo'
        s02['routes_ipv6'][0]['destination'] = '2001:XXX8:X::/64'
        s02['ipv6_address_mode'] = 'invalid'
        s02['ipv6_ra_mode'] = 'invalid'

        ipv4_only = copy.deepcopy(dual)
        ipv6_only = copy.deepcopy(dual)
        for name, subnet in ipv4_only['subnets'].items():
            [subnet.pop(k) for k in IPV6_SUBNET_KEYS]
        for name, subnet in ipv6_only['subnets'].items():
            [subnet.pop(k) for k in IPV4_SUBNET_KEYS]
        ipv4_only['subnets']['subnet01'].pop('ip_subnet')  # Required
        ipv6_only['subnets']['subnet01'].pop('ipv6_subnet')  # Required

        error_messages_dual = network_data_v2.validate_json_schema(dual)
        error_messages_dual = '\n'.join(error_messages_dual)
        error_messages_ipv4 = network_data_v2.validate_json_schema(ipv4_only)
        error_messages_ipv4 = '\n'.join(error_messages_ipv4)
        error_messages_ipv6 = network_data_v2.validate_json_schema(ipv6_only)
        error_messages_ipv6 = '\n'.join(error_messages_ipv6)

        self.assertRegex(error_messages_dual,
                         (r"Failed schema validation at admin_state_up:\n"
                          r"    'not_bool' is not of type 'boolean'\n"))
        self.assertRegex(error_messages_dual,
                         (r"Failed schema validation at mtu:\n"
                          r"    400 is less than the minimum of 1000\n"))
        self.assertRegex(error_messages_dual,
                         (r"Failed schema validation at shared:\n"
                          r"    'not_bool' is not of type 'boolean'\n"))
        self.assertRegex(error_messages_dual,
                         (r"Failed schema validation at ipv6:\n"
                          r"    'not_bool' is not of type 'boolean'\n"))
        self.assertRegex(error_messages_dual,
                         (r"Failed schema validation at vip:\n"
                          r"    'not_bool' is not of type 'boolean'\n"))
        self.assertRegex(error_messages_dual,
                         (r"Failed schema validation at :\n"
                          r".*Additional properties are not allowed "
                          r"\('invalid_key' was unexpected\)\n"))
        self.assertRegex(error_messages_dual,
                         (r"Failed schema validation at :\n"
                          r".*'name' is a required property"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/allocation_pools/items/additionalProperties: "
                          r"Additional properties are not allowed \('foo' was "
                          r"unexpected\)\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/allocation_pools/items/start/ip_address_version: "
                          r"2001:db8:a::1 does not appear to be an IPv4 "
                          r"address\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/enable_dhcp/type: 'not_a_bool' is not of type "
                          r"'boolean'\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/gateway_ip/ip_address_version: 2001:db8:a::1 "
                          r"does not appear to be an IPv4 address\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/gateway_ipv6/ip_address_version: 172.18.1.254 "
                          r"does not appear to be an IPv6 address\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/ip_subnet/ip_subnet_version: invalid does not "
                          r"appear to be an IPv4 subnet\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/ipv6_address_mode/enum: 'invalid' is not one of "
                          r"\['slaac', 'dhcpv6-stateful', 'dhcpv6-stateless'\]"
                          r"\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/ipv6_allocation_pools/items"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \('v6_invalid_key' was unexpected\)"
                          r"\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/ipv6_allocation_pools/items/end"
                          r"/ip_address_version: 172.18.1.20 does not appear "
                          r"to be an IPv6 address\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/ipv6_ra_mode/enum: 'invalid' is not one of "
                          r"\['slaac', 'dhcpv6-stateful', 'dhcpv6-stateless'\]\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/ipv6_subnet/ip_subnet_version: invalid does not "
                          r"appear to be an IPv6 subnet\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/network_type/enum: 'invalid' is not one of "
                          r"\['flat', 'vlan'\]\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/physical_network/type: {} is not of type 'string'"
                          r"\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/routes/items/additionalProperties: Additional "
                          r"properties are not allowed \('foo' was unexpected\)"
                          r"\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/routes/items/destination/ip_subnet_version: "
                          r"172.18.0.0/99 does not appear to be an IPv4 subnet"
                          r"\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/routes/items/nexthop/ip_address_version: "
                          r"172222.18.1.254 does not appear to be an IPv4 "
                          r"address\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/routes_ipv6/items/additionalProperties: "
                          r"Additional properties are not allowed \("
                          r"'v6_invalid_key' was unexpected\)\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/routes_ipv6/items/destination/ip_subnet_version: "
                          r"2001:XXX8:X::/64 does not appear to be an IPv6 "
                          r"subnet\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/dual_subnet"
                          r"/vlan/type: 'not_an_int' is not of type 'integer'"
                          r"\n"))

        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \(.*'routes'.* were unexpected\)\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \(.*'allocation_pools'.* were "
                          r"unexpected\)\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \(.*'ip_subnet'.* were unexpected\)\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \(.*'gateway_ip'.* were unexpected\)"
                          r"\n"))

        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \(.*'routes_ipv6'.* were unexpected\)"
                          r"\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \(.*'ipv6_allocation_pools'.* were "
                          r"unexpected\)\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \(.*'ipv6_subnet'.* were unexpected\)"
                          r"\n"))
        self.assertRegex(error_messages_dual,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \(.*'gateway_ipv6'.* were unexpected\)"
                          r"\n"))

        self.assertRegex(error_messages_ipv4,
                         r"Failed schema validation at subnets/subnet01:\n")
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/required: 'ip_subnet' is a required property\n"))
        self.assertRegex(error_messages_ipv4,
                         r"Failed schema validation at subnets/subnet02:\n")
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/allocation_pools/items/additionalProperties: "
                          r"Additional properties are not allowed \('foo' was "
                          r"unexpected\)\n"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/allocation_pools/items/start/ip_address_version: "
                          r"2001:db8:a::1 does not appear to be an IPv4 "
                          r"address\n"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet/"
                          r"enable_dhcp/type: \'not_a_bool\' is not of type "
                          r"\'boolean\'\n"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/gateway_ip/ip_address_version: 2001:db8:a::1 does "
                          r"not appear to be an IPv4 address\n"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/ip_subnet/ip_subnet_version: invalid does not "
                          r"appear to be an IPv4 subnet\n"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/network_type/enum: 'invalid' is not one of "
                          r"\['flat', 'vlan'\].*"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/physical_network/type: {} is not of type 'string'"
                          r"\n"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/routes/items/additionalProperties: Additional "
                          r"properties are not allowed \('foo' was "
                          r"unexpected\)\n"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/routes/items/destination/ip_subnet_version: "
                          r"172.18.0.0/99 does not appear to be an IPv4 subnet"
                          r"\n"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/routes/items/nexthop/ip_address_version: "
                          r"172222.18.1.254 does not appear to be an IPv4 "
                          r"address\n"))
        self.assertRegex(error_messages_ipv4,
                         (r"- subnets/additionalProperties/oneOf/ipv4_subnet"
                          r"/vlan/type: 'not_an_int' is not of type 'integer'"
                          r"\n"))

        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/enable_dhcp/type: 'not_a_bool' is not of type "
                          r"'boolean'\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/gateway_ipv6/ip_address_version: 172.18.1.254 "
                          r"does not appear to be an IPv6 address\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/ipv6_address_mode/enum: 'invalid' is not one of "
                          r"\['slaac', 'dhcpv6-stateful', 'dhcpv6-stateless'\]"
                          r"\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/ipv6_allocation_pools/items"
                          r"/additionalProperties: Additional properties are "
                          r"not allowed \('v6_invalid_key' was unexpected\)"
                          r"\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/ipv6_allocation_pools/items/end"
                          r"/ip_address_version: 172.18.1.20 does not appear "
                          r"to be an IPv6 address\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/ipv6_subnet/ip_subnet_version: invalid does not "
                          r"appear to be an IPv6 subnet\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/network_type/enum: 'invalid' is not one of "
                          r"\['flat', 'vlan'\]\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/physical_network/type: {} is not of type 'string'"
                          r"\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/routes_ipv6/items/additionalProperties: "
                          r"Additional properties are not allowed "
                          r"\('v6_invalid_key' was unexpected\)\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/routes_ipv6/items/destination/ip_subnet_version: "
                          r"2001:XXX8:X::/64 does not appear to be an IPv6 "
                          r"subnet\n"))
        self.assertRegex(error_messages_ipv6,
                         (r"- subnets/additionalProperties/oneOf/ipv6_subnet"
                          r"/vlan/type: 'not_an_int' is not of type 'integer'"
                          r"\n"))

    def test_tripleo_resource_tags_to_dict(self):
        tags = ['foo=bar', 'baz=qux', 'tripleo_foo=bar', 'tripleo_baz=qux',
                'tripleo_net_idx=3']
        expected = {'tripleo_foo': 'bar', 'tripleo_baz': 'qux',
                    'tripleo_net_idx': 3}
        result = network_data_v2.tags_to_dict(tags)
        self.assertEqual(expected, result)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_create_name_id_maps(self, conn_mock):
        subnet1 = stubs.FakeNeutronSubnet(id='subnet1_id',
                                          name='subnet1',
                                          cidr='192.168.24.0/24')
        subnet2 = stubs.FakeNeutronSubnet(id='subnet2_id',
                                          name='subnet2',
                                          cidr='192.168.25.0/25')
        subnet3 = stubs.FakeNeutronSubnet(id='subnet3_id',
                                          name='subnet3',
                                          cidr='192.168.26.0/26')
        subnet4 = stubs.FakeNeutronSubnet(id='subnet4_id',
                                          name='subnet4',
                                          cidr='192.168.27.0/27')
        network1 = stubs.FakeNeutronNetwork(
            id='network1_id',
            name='network1',
            subnet_ids=['subnet1_id', 'subnet2_id'],
            tags=['tripleo_network_name=Network1']
        )
        network2 = stubs.FakeNeutronNetwork(
            id='network2_id',
            name='network2',
            subnet_ids=['subnet3_id', 'subnet4_id'],
            tags=['tripleo_network_name=Network2']
        )
        conn_mock.network.networks.return_value = self.a2g([network1,
                                                            network2])
        conn_mock.network.subnets.side_effect = [self.a2g([subnet1, subnet2]),
                                                 self.a2g([subnet3, subnet4])]
        net_maps = network_data_v2.create_name_id_maps(conn_mock)
        expected_by_name_map = {
            'network1': {
                'id': 'network1_id',
                'name_upper': 'Network1',
                'subnets': {
                    'subnet1': 'subnet1_id',
                    'subnet2': 'subnet2_id'
                }
            },
            'network2': {
                'id': 'network2_id',
                'name_upper': 'Network2',
                'subnets': {
                    'subnet3': 'subnet3_id',
                    'subnet4': 'subnet4_id'
                }
            }
        }
        expected_by_id_map = {
            'network1_id': 'network1',
            'network2_id': 'network2',
        }
        expected_cidr_prefix_map = {
            'subnet1_id': '24',
            'subnet2_id': '25',
            'subnet3_id': '26',
            'subnet4_id': '27',
        }
        self.assertEqual(expected_by_name_map, net_maps['by_name'])
        self.assertEqual(expected_by_id_map, net_maps['by_id'])
        self.assertEqual(expected_cidr_prefix_map, net_maps['cidr_prefix_map'])
