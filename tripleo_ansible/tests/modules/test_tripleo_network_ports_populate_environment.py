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
    tripleo_network_ports_populate_environment as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs


class TestTripleoNetworkPortsPopulateEnvironment(tests_base.TestCase):

    def test_update_environment(self):
        env = {
            'parameter_defaults': {
                'FooParam': 'foo',
                'BarParam': 'bar'},
            'resource_registry': {
                'OS::Some::Existing::Resource': '/foo/bar/some_resource.yaml'}
        }
        node_port_map = {
            'role-a-0': {'foo': {'ip_address': '1.1.1.1'},
                         'bar': {'ip_address': '1.1.2.1'},
                         'baz': {'ip_address': '1.1.3.1'}},
            'role-b-0': {'foo': {'ip_address': '1.1.1.2'},
                         'bar': {'ip_address': '1.1.2.2'}},
        }
        role_net_map = {
            'RoleA': ['ctlplane', 'foo', 'bar', 'baz'],
            'RoleB': ['ctlplane', 'foo', 'bar']
        }
        net_name_map = {'foo': 'Foo', 'bar': 'Bar', 'baz': 'Baz'}
        templates = '/foo/tht_root'
        plugin.update_environment(env, node_port_map, role_net_map,
                                  net_name_map, templates)
        self.assertEqual(
            {'FooParam': 'foo',
             'BarParam': 'bar',
             'NodePortMap': {
                 'role-a-0': {'bar': {'ip_address': '1.1.2.1'},
                              'baz': {'ip_address': '1.1.3.1'},
                              'foo': {'ip_address': '1.1.1.1'}},
                 'role-b-0': {'bar': {'ip_address': '1.1.2.2'},
                              'foo': {'ip_address': '1.1.1.2'}},
             }}, env['parameter_defaults'])
        self.assertEqual(
            {'OS::Some::Existing::Resource': '/foo/bar/some_resource.yaml',
             'OS::TripleO::RoleA::Ports::BarPort':
                 '/foo/tht_root/network/ports/deployed_bar.yaml',
             'OS::TripleO::RoleA::Ports::BazPort':
                 '/foo/tht_root/network/ports/deployed_baz.yaml',
             'OS::TripleO::RoleA::Ports::FooPort':
                 '/foo/tht_root/network/ports/deployed_foo.yaml',
             'OS::TripleO::RoleB::Ports::BarPort':
                 '/foo/tht_root/network/ports/deployed_bar.yaml',
             'OS::TripleO::RoleB::Ports::FooPort':
                 '/foo/tht_root/network/ports/deployed_foo.yaml'},
            env['resource_registry'])

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_get_net_name_map(self, mock_conn):
        fake_networks = [
            stubs.FakeNeutronNetwork(id='bar', name='bar',
                                     tags=['tripleo_network_name=UPPERNAME']),
            stubs.FakeNeutronNetwork(id='baz', name='baz',
                                     tags=['tripleo_network_name=UPPERNAME']),
            stubs.FakeNeutronNetwork(id='foo', name='foo',
                                     tags=['tripleo_network_name=UPPERNAME']),
            ]
        mock_conn.network.find_network.side_effect = fake_networks
        role_net_map = {
            'RoleA': [plugin.CTLPLANE_NETWORK, 'foo', 'bar', 'baz'],
            'RoleB': [plugin.CTLPLANE_NETWORK, 'foo', 'bar']
        }
        # NOTE(hjensas): Different tripleo_network_name in stubs would require
        # set to list conversion and sorting.
        self.assertEqual({plugin.CTLPLANE_NETWORK: plugin.CTLPLANE_NETWORK,
                          'foo': 'UPPERNAME',
                          'bar': 'UPPERNAME',
                          'baz': 'UPPERNAME'},
                         plugin.get_net_name_map(mock_conn, role_net_map))
