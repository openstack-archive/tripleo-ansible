# Copyright (c) 2021 OpenStack Foundation
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
    tripleo_service_vip as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs


class TestTripleoServiceVip(tests_base.TestCase):

    def setUp(self):
        super(TestTripleoServiceVip, self).setUp()

        # Helper function to convert array to generator
        self.a2g = lambda x: (n for n in x)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_create_port(self, mock_conn):
        fixed_ips = [{'subnet': 'test'}]
        fake_net = stubs.FakeNeutronNetwork(
            name='test',
            id='net_id'
        )
        fake_subnet = stubs.FakeNeutronSubnet(
            name='test',
            id='subnet_id'
        )
        fake_port = stubs.FakeNeutronPort(
            name='test_virtual_ip',
            id='port_id',
            fixed_ips=[{'ip_address': '10.0.0.10', 'subnet_id': 'subnet_id'}],
            tags=[]
        )
        mock_conn.network.find_subnet.return_value = fake_subnet
        mock_conn.network.ports.return_value = self.a2g([])
        mock_conn.network.create_port.return_value = fake_port
        plugin.create_or_update_port(mock_conn, fake_net, stack='test',
                                     service='test', fixed_ips=fixed_ips)
        mock_conn.network.create_port.assert_called_once_with(
            name='test_virtual_ip', network_id='net_id',
            fixed_ips=[{'subnet_id': 'subnet_id'}])
        mock_conn.network.update_port.assert_not_called()
        mock_conn.network.set_tags.assert_called_once_with(
            fake_port, [mock.ANY, mock.ANY])

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_update_port(self, mock_conn):
        fixed_ips = [{'subnet': 'test'}]
        fake_net = stubs.FakeNeutronNetwork(
            name='test',
            id='net_id'
        )
        fake_subnet = stubs.FakeNeutronSubnet(
            name='test',
            id='subnet_id'
        )
        fake_port = stubs.FakeNeutronPort(
            name='test_virtual_ip',
            id='port_id',
            fixed_ips=[{'ip_address': '10.0.0.10', 'subnet_id': 'subnet_id'}],
            tags=[]
        )
        mock_conn.network.find_subnet.return_value = fake_subnet
        mock_conn.network.ports.return_value = self.a2g([fake_port])
        mock_conn.network.update_port.return_value = fake_port
        plugin.create_or_update_port(mock_conn, fake_net, stack='test',
                                     service='test', fixed_ips=fixed_ips)
        mock_conn.network.create_port.assert_not_called()
        mock_conn.network.update_port.assert_called_once_with(
            fake_port, name='test_virtual_ip', network_id='net_id',
            fixed_ips=[{'subnet_id': 'subnet_id'}])
        mock_conn.network.set_tags.assert_called_once_with(
            fake_port, [mock.ANY, mock.ANY])

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_no_change_no_update(self, mock_conn):
        # TODO
        pass

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_fail_if_no_fixed_ips(self, mock_conn):
        fake_net = stubs.FakeNeutronNetwork(
            name='test',
            id='net_id'
        )
        msg = ('ERROR: No IP allocation definition provided. '
               'Please provide at least one IP allocation '
               'definition using the fixed_ips argument.')
        self.assertRaisesRegex(Exception, msg,
                               plugin.create_or_update_port, mock_conn,
                               fake_net)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_find_ctlplane_vip_found(self, mock_conn):
        tags = ['tripleo_stack_name=overcloud', 'tripleo_vip_net=ctlplane']
        fake_port = stubs.FakeNeutronPort(
            name='test_virtual_ip',
            id='port_id',
            fixed_ips=[{'ip_address': '10.0.0.10', 'subnet_id': 'subnet_id'}],
            tags=['tripleo_stack_name=overcloud',
                  'tripleo_vip_net=ctlplane']
        )
        mock_conn.network.ports.return_value = self.a2g([fake_port])
        port = plugin.find_ctlplane_vip(mock_conn, stack='overcloud',
                                        service='test')
        mock_conn.network.ports.assert_called_once_with(tags=tags)
        self.assertEqual(fake_port, port)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_find_ctlplane_vip_not_found(self, mock_conn):
        stack = 'overcloud'
        service = 'test'
        msg = ('Virtual IP address on the ctlplane network for stack '
               '{} not found. Service {} is mapped to the ctlplane '
               'network and thus require a virtual IP address to be '
               'present on the ctlplane network.'.format(stack, service))
        mock_conn.network.ports.return_value = self.a2g([])
        self.assertRaisesRegex(Exception, msg,
                               plugin.find_ctlplane_vip, mock_conn,
                               stack=stack, service=service)
        tags = ['tripleo_stack_name={}'.format(stack),
                'tripleo_vip_net=ctlplane']
        mock_conn.network.ports.assert_called_once_with(tags=tags)

    @mock.patch.object(plugin, 'write_vars_file', autospec=True)
    @mock.patch.object(plugin, 'use_neutron', autospec=True)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    @mock.patch.object(plugin, '_openstack_cloud_from_module', autospec=True)
    def test_create_service_vip(self, mock_ocfm, mock_conn, mock_use_neutron,
                                mock_write_file):
        expected = "{'service': '10.0.0.10'}"
        module = mock.Mock()
        fixed_ips = [{'ip_address': '10.0.0.10', 'subnet_id': 'subnet_id'}]
        mock_ocfm.return_value = None, mock_conn
        mock_port = mock.Mock()
        mock_use_neutron.return_value = mock_port
        payload = plugin.create_service_vip(module, 'overcloud', 'service', 'network',
                                            fixed_ips, '/tmp/dir')

        payload.return_value = "{'service': '10.0.0.10'}"
        mock_use_neutron.assert_called_with(mock_conn, 'overcloud', 'service',
                                            'network', fixed_ips)
        mock_write_file.assert_called_with(mock_port, 'service', '/tmp/dir', None)

        self.assertEqual(expected, payload.return_value)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    @mock.patch.object(plugin, '_openstack_cloud_from_module', autospec=True)
    def test_delete_service_vip(self, mock_ocfm, mock_conn):
        module = mock.Mock()
        mock_ocfm.return_value = None, mock_conn
        mock_port1 = mock.Mock(id=123,
                               tags=['tripleo_stack_name=overcloud',
                                     'tripleo_service_vip=ovn_dbs'])
        mock_port2 = mock.Mock(id=456, tags=[])
        mock_conn.network.ports.return_value = [mock_port1, mock_port2]
        plugin.delete_service_vip(module, 'overcloud')
        mock_conn.network.delete_port.assert_called_with(123)
        self.assertEqual(1, mock_conn.network.delete_port.call_count)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    @mock.patch.object(plugin, '_openstack_cloud_from_module', autospec=True)
    def test_delete_service_vip_with_service(self, mock_ocfm, mock_conn):
        module = mock.Mock()
        mock_ocfm.return_value = None, mock_conn
        mock_port = mock.Mock(id=123,
                              tags=['tripleo_stack_name=overcloud',
                                    'tripleo_service_vip=redis'])
        mock_conn.network.ports.return_value = [mock_port]
        plugin.delete_service_vip(module, 'overcloud', 'redis')
        mock_conn.network.delete_port.assert_called_with(123)

    @mock.patch.object(plugin, 'write_vars_file', autospec=True)
    @mock.patch.object(plugin, 'use_fake', autospec=True)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    @mock.patch.object(plugin, '_openstack_cloud_from_module', autospec=True)
    def test_create_no_neutron_service_vip(self, mock_ocfm, mock_conn,
                                           mock_use_fake, mock_write_file):
        module = mock.Mock()
        fixed_ips = [{'ip_address': '10.0.0.10', 'subnet_id': 'subnet_id',
                      'use_neutron': False}]
        mock_ocfm.return_value = None, mock_conn
        mock_port = mock.Mock()
        mock_use_fake.return_value = mock_port
        plugin.create_service_vip(module, 'overcloud', 'service', 'network',
                                  fixed_ips, '/tmp/dir')
        mock_use_fake.assert_called_with('service', fixed_ips)
        mock_write_file.assert_called_with(mock_port, 'service', '/tmp/dir', None)
