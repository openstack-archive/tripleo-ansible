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
    tripleo_overcloud_network_vip_provision as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs


BY_NAME_MAP = {
            'network1': {
                'id': 'network1_id',
                'subnets': {
                    'subnet1': 'subnet1_id',
                    'subnet2': 'subnet2_id'
                }
            },
            'network2': {
                'id': 'network2_id',
                'subnets': {
                    'subnet3': 'subnet3_id',
                    'subnet4': 'subnet4_id'
                }
            }
        }
BY_ID_MAP = {
            'network1_id': 'network1',
            'network2_id': 'network2',
        }
NET_MAPS = {'by_name': BY_NAME_MAP, 'by_id': BY_ID_MAP}


@mock.patch.object(openstack.connection, 'Connection', autospec=True)
class TestTripleoOvercloudVipProvision(tests_base.TestCase):

    def setUp(self):
        super(TestTripleoOvercloudVipProvision, self).setUp()

        # Helper function to convert array to generator
        self.a2g = lambda x: (n for n in x)

    def test_validate_vip_nets_in_net_map(self, mock_conn):
        vip_data = [{'name': 'foo', 'network': 'bar', 'subnet': 'bar_subnet'}]

        msg = 'Network {} for Virtual IP not found.'.format(
            vip_data[0]['network'])
        self.assertRaisesRegex(Exception, msg,
                               plugin.validate_vip_nets_in_net_map,
                               vip_data, NET_MAPS)
        vip_data = [{'name': 'foo', 'network': 'network1', 'subnet': 'ERR'}]
        msg = 'Subnet {} for Virtual IP not found on network {}.'.format(
            vip_data[0]['subnet'], vip_data[0]['network'])
        self.assertRaisesRegex(Exception, msg,
                               plugin.validate_vip_nets_in_net_map,
                               vip_data, NET_MAPS)

    def test_create_port_def(self, mock_conn):
        vip_spec = {'name': 'network1_virtual_ip',
                    'network': 'network1',
                    'subnet': 'subnet2',
                    'dns_name': 'overcloud'}
        self.assertEqual({'dns_name': 'overcloud',
                          'fixed_ips': [{'subnet_id': 'subnet2_id'}],
                          'name': 'network1_virtual_ip',
                          'network_id': 'network1_id'},
                         plugin.create_port_def(vip_spec, NET_MAPS))
        vip_spec = {'name': 'network1_virtual_ip',
                    'network': 'network1',
                    'ip_address': '1.2.3.4',
                    'dns_name': 'overcloud'}
        self.assertEqual({'dns_name': 'overcloud',
                          'fixed_ips': [{'ip_address': '1.2.3.4'}],
                          'name': 'network1_virtual_ip',
                          'network_id': 'network1_id'},
                         plugin.create_port_def(vip_spec, NET_MAPS))

    def test_create_port_def_minimal_input(self, mock_conn):
        vip_spec = {'network': 'network1'}
        net_maps = copy.deepcopy(NET_MAPS)
        del net_maps['by_name']['network1']['subnets']['subnet2']
        self.assertEqual({'dns_name': 'overcloud',
                          'name': 'network1_virtual_ip',
                          'fixed_ips': [{'subnet_id': 'subnet1_id'}],
                          'network_id': 'network1_id'},
                         plugin.create_port_def(vip_spec, net_maps))

    def test_create_port_def_minimal_input_raises(self, mock_conn):
        vip_spec = {'network': 'network1'}
        msg = (
            'Network {} has multiple subnets, please add a subnet or an '
            'ip_address for the vip on this network.'.format(
                vip_spec['network']))
        self.assertRaisesRegex(Exception, msg,
                               plugin.create_port_def, vip_spec, NET_MAPS)

    def test_provision_vip_port(self, mock_conn):
        vip_spec = {'name': 'network1_virtual_ip',
                    'network': 'network1',
                    'ip_address': '1.2.3.4',
                    'dns_name': 'overcloud'}
        mock_conn.network.ports.return_value = self.a2g([])
        managed_ports = list()
        plugin.provision_vip_port(mock_conn, 'stack', NET_MAPS, vip_spec,
                                  managed_ports)
        mock_conn.network.create_port.assert_called_with(
            dns_name='overcloud',
            fixed_ips=[{'ip_address': '1.2.3.4'}],
            name='network1_virtual_ip',
            network_id='network1_id')
        mock_conn.network.set_tags.assert_called_once()

    def test_provision_vip_port_update_no_change(self, mock_conn):
        vip_spec = {'name': 'network1_virtual_ip',
                    'network': 'network1',
                    'ip_address': '1.2.3.4',
                    'dns_name': 'overcloud'}
        fake_port = stubs.FakeNeutronPort(
            id='port_id',
            name='network1_virtual_ip',
            network_id='network1_id',
            fixed_ips=[{'ip_address': '1.2.3.4'}],
            dns_name='overcloud',
            tags=['tripleo_stack_name=stack', 'tripleo_vip_net=network1']
        )
        mock_conn.network.ports.return_value = self.a2g([fake_port])
        managed_ports = list()
        plugin.provision_vip_port(mock_conn, 'stack', NET_MAPS, vip_spec,
                                  managed_ports)
        self.assertEqual([fake_port.id], managed_ports)
        mock_conn.network.create_port.assert_not_called()
        mock_conn.network.update_port.assert_not_called()
        mock_conn.network.set_tags.assert_not_called()

    def test_provision_vip_port_update_need_update(self, mock_conn):
        vip_spec = {'name': 'network1_virtual_ip',
                    'network': 'network1',
                    'ip_address': '11.22.33.44',
                    'dns_name': 'overcloud'}
        fake_port = stubs.FakeNeutronPort(
            id='port_id',
            name='network1_virtual_ip',
            network_id='network1_id',
            fixed_ips=[{'ip_address': '1.2.3.4'}],
            dns_name='overcloud',
            tags=['tripleo_stack_name=stack', 'tripleo_vip_net=network1']
        )
        port_def = {'dns_name': 'overcloud',
                    'fixed_ips': [{'ip_address': '11.22.33.44'}],
                    'name': 'network1_virtual_ip'}
        mock_conn.network.ports.return_value = self.a2g([fake_port])
        managed_ports = list()
        plugin.provision_vip_port(mock_conn, 'stack', NET_MAPS, vip_spec,
                                  managed_ports)
        self.assertEqual([fake_port.id], managed_ports)
        mock_conn.network.create_port.assert_not_called()
        mock_conn.network.update_port.assert_called_with(fake_port.id,
                                                         **port_def)
        mock_conn.network.set_tags.assert_not_called()

    def test_remove_obsolete_ports_deletes_port(self, mock_conn):
        fake_port = stubs.FakeNeutronPort(
            id='port_id',
            name='network1_virtual_ip',
            network_id='network1_id',
            fixed_ips=[{'ip_address': '1.2.3.4'}],
            dns_name='overcloud',
            tags=['tripleo_stack_name=stack', 'tripleo_vip_net=network1']
        )
        mock_conn.network.ports.return_value = self.a2g([fake_port])
        plugin.remove_obsolete_ports(mock_conn, 'stack', [])
        mock_conn.network.delete_port.assert_called_once_with(fake_port.id)

    def test_remove_obsolete_ports_does_not_delete_managed(self, mock_conn):
        fake_port = stubs.FakeNeutronPort(
            id='port_id',
            name='network1_virtual_ip',
            network_id='network1_id',
            fixed_ips=[{'ip_address': '1.2.3.4'}],
            dns_name='overcloud',
            tags=['tripleo_stack_name=stack', 'tripleo_vip_net=network1']
        )
        mock_conn.network.ports.return_value = self.a2g([fake_port])
        plugin.remove_obsolete_ports(mock_conn, 'stack', [fake_port.id])
        mock_conn.network.delete_port.assert_not_called()
