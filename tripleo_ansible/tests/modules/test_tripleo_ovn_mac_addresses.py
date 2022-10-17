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

import copy
import mock
import openstack

try:
    from ansible.module_utils import network_data_v2 as n_utils
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import network_data_v2 as n_utils  # noqa
from tripleo_ansible.ansible_plugins.modules import (
    tripleo_ovn_mac_addresses as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs


FAKE_NETWORK = stubs.FakeNeutronNetwork(
    name=plugin.NET_NAME,
    id='fake_ovn_mac_addr_net_id',
    description=plugin.NET_DESCRIPTION
)

FAKE_PORT = stubs.FakeNeutronPort(
    name='server-01_ovn_physnet_network01',
    dns_name='server-01',
    tags=['tripleo_ovn_physnet=network01', 'tripleo_stack_name=stack']
)


@mock.patch.object(openstack.connection, 'Connection', autospec=True)
class TestTripleoOVNMacAddresses(tests_base.TestCase):

    def setUp(self):
        super(TestTripleoOVNMacAddresses, self).setUp()

        # Helper function to convert array to generator
        self.a2g = lambda x: (n for n in x)

    def test_create_ovn_mac_address_network(self, mock_conn):
        result = dict(changed=False)
        mock_conn.network.find_network.return_value = None
        mock_conn.network.create_network.return_value = FAKE_NETWORK

        net_id = plugin.create_ovn_mac_address_network(result, mock_conn)

        mock_conn.network.create_network.assert_called_with(
            name=plugin.NET_NAME,
            description=plugin.NET_DESCRIPTION)
        self.assertTrue(result['changed'])
        self.assertEqual(FAKE_NETWORK.id, net_id)

    def test_create_ovn_mac_address_network_already_exists(self, mock_conn):
        result = dict(changed=False)
        mock_conn.network.find_network.return_value = FAKE_NETWORK

        net_id = plugin.create_ovn_mac_address_network(result, mock_conn)

        mock_conn.network.create_network.assert_not_called()
        self.assertFalse(result['changed'])
        self.assertEqual(FAKE_NETWORK.id, net_id)

    def test_port_exists_port_not_found(self, mock_conn):
        net_id = FAKE_NETWORK.id
        tags = ['tripleo_stack_name=stack']
        name = 'server-01_ovn_physnet_network01'
        mock_conn.network.ports.return_value = self.a2g([])
        self.assertFalse(plugin.port_exists(mock_conn, net_id, tags, name))
        mock_conn.network.ports.assert_called_with(network_id=net_id,
                                                   name=name, tags=tags)

    def test_port_exists_port_found(self, mock_conn):
        net_id = FAKE_NETWORK.id
        tags = ['tripleo_stack_name=stack']
        name = 'server-01_ovn_physnet_network01'
        mock_conn.network.ports.return_value = self.a2g([FAKE_PORT])
        self.assertTrue(plugin.port_exists(mock_conn, net_id, tags, name))
        mock_conn.network.ports.assert_called_with(network_id=net_id,
                                                   name=name, tags=tags)

    @mock.patch.object(plugin, 'port_exists', autospec=True)
    def test_create_ovn_mac_address_ports(self, mock_port_exists, mock_conn):
        result = dict(changed=False)
        tags = ['tripleo_stack_name=overcloud']
        physnets = ['net-a', 'net-b']
        server = 'controller-0'
        mock_port_exists.return_value = False
        plugin.create_ovn_mac_address_ports(result, mock_conn,
                                            FAKE_NETWORK.id, tags,
                                            physnets, server)
        mock_conn.network.create_port.assert_has_calls(
            [mock.call(network_id=FAKE_NETWORK.id,
                       name=server + '_ovn_physnet_net-a',
                       dns_name=server),
             mock.call(network_id=FAKE_NETWORK.id,
                       name=server + '_ovn_physnet_net-b',
                       dns_name=server)])
        mock_conn.network.set_tags.assert_has_calls(
            [mock.call(mock.ANY, tags + ['tripleo_ovn_physnet=net-a']),
             mock.call(mock.ANY, tags + ['tripleo_ovn_physnet=net-b'])])

    @mock.patch.object(plugin, 'port_exists', autospec=True)
    def test_create_ovn_mac_address_ports_exists(self, mock_port_exists,
                                                 mock_conn):
        result = dict(changed=False)
        tags = ['tripleo_stack_name=overcloud']
        physnets = ['net-a', 'net-b']
        server = 'controller-0.example.com'
        mock_port_exists.return_value = True
        plugin.create_ovn_mac_address_ports(result, mock_conn,
                                            FAKE_NETWORK.id, tags,
                                            physnets, server)
        mock_conn.network.create_port.assert_not_called()
        mock_conn.network.set_tags.assert_not_called()

    def test_delete_ports_for_removed_nodes(self, mock_conn):
        result = dict(changed=False)
        servers = ['server-01', 'server-a', 'server-b']
        physnets = ['network01', 'net-a', 'net-b']
        mock_conn.network.ports.return_value = self.a2g([FAKE_PORT])
        plugin.remove_obsolete_ports(result, mock_conn, 'net_id',
                                     ['fake_tags'], servers, physnets)
        mock_conn.network.delete_port.assert_not_called()
        self.assertFalse(result['changed'])

        # Verify port is deleted if server was deleted, (scale down)
        mock_conn.reset_mock()
        mock_conn.network.ports.return_value = self.a2g([FAKE_PORT])
        servers = ['server-a', 'server-b']
        plugin.remove_obsolete_ports(result, mock_conn, 'net_id',
                                     ['fake_tags'], servers, physnets)
        mock_conn.network.delete_port.assert_called_with(FAKE_PORT)
        self.assertTrue(result['changed'])

        # Verify port is deleted if physnet no longer in bridge mappings
        mock_conn.reset_mock()
        result = dict(changed=False)
        mock_conn.network.ports.return_value = self.a2g([FAKE_PORT])
        servers = ['server-01', 'server-a', 'server-b']
        physnets = ['net-a', 'net-b']
        plugin.remove_obsolete_ports(result, mock_conn, 'net_id',
                                     ['fake_tags'], servers, physnets)
        mock_conn.network.delete_port.assert_called_with(FAKE_PORT)
        self.assertTrue(result['changed'])
