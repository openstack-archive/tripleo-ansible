# Copyright 2021 Red Hat, Inc.
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
    tripleo_overcloud_network_vip_populate_environment as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs

BY_NAME_MAP = {
    'ctlplane': {
        'id': 'ctlplane_id',
        'subnets': {
            'ctlplane-subnet': 'ctlplane_subnet_id'
        }
    },
    'internal_api': {
        'id': 'internal_api_id',
        'subnets': {
            'internal_api_subnet': 'internal_api_subnet_id',
        }
    },
    'storage_mgmt': {
        'id': 'storage_mgmt_id',
        'subnets': {
            'storage_mgmt_subnet': 'storage_mgmt_subnet_id',
        }
    },
    'external': {
        'id': 'external_id',
        'subnets': {
            'external_subnet': 'external_subnet_id',
        }
    },
}

NET_MAPS = {'by_name': BY_NAME_MAP}

fake_internal_api = stubs.FakeNeutronNetwork(
    id='internal_api_id', name='internal_api',
    dns_domain='internalapi.localdomain.',
    tags=['tripleo_network_name=InternalApi', 'tripleo_stack_name=stack'])
fake_storage_mgmt = stubs.FakeNeutronNetwork(
    id='storage_mgmt_id', name='storage_mgmt',
    dns_domain='storagemgmt.localdomain.',
    tags=['tripleo_network_name=StorageMgmt', 'tripleo_stack_name=stack'])
fake_external = stubs.FakeNeutronNetwork(
    id='external_id', name='external',
    dns_domain='external.localdomain.',
    tags=['tripleo_network_name=External', 'tripleo_stack_name=stack'])
fake_ctlplane = stubs.FakeNeutronNetwork(
    id='ctlplane_id', name='ctlplane', dns_domain='ctlplane.localdomain.',
    tags=['foo', 'bar'])
fake_ctlplane_subnet = stubs.FakeNeutronSubnet(
    id='ctlplane_subnet_id', name='ctlplane-subnet', cidr='192.168.24.0/24',
    ip_version=4)
fake_internal_api_subnet = stubs.FakeNeutronSubnet(
    id='internal_api_subnet_id', name='internal_api_subnet',
    cidr='10.0.1.0/24')
fake_storage_mgmt_subnet = stubs.FakeNeutronSubnet(
    id='storage_mgmt_subnet_id', name='storage_mgmt_subnet',
    cidr='10.0.3.0/24')
fake_external_subnet = stubs.FakeNeutronSubnet(
    id='external_subnet_id', name='external_subnet', cidr='10.0.5.0/24')

fake_ctlplane_port = stubs.FakeNeutronPort(
    name='control_virtual_ip',
    id='ctlplane_port_id',
    dns_name='overcloud',
    fixed_ips=[{'ip_address': '192.168.24.1',
                'subnet_id': 'ctlplane_subnet_id'}],
    tags=['tripleo_stack_name=stack', 'tripleo_vip_net=ctlplane']
)
fake_internal_api_port = stubs.FakeNeutronPort(
    id='internal_api_port_id',
    dns_name='overcloud',
    fixed_ips=[{'ip_address': '10.0.1.1',
                'subnet_id': 'internal_api_subnet_id'}],
    tags=['tripleo_stack_name=stack', 'tripleo_vip_net=internal_api']
)
fake_storage_mgmt_port = stubs.FakeNeutronPort(
    id='storage_mgmt_port_id',
    dns_name='overcloud',
    fixed_ips=[{'ip_address': '10.0.3.1',
                'subnet_id': 'storage_mgmt_subnet_id'}],
    tags=['tripleo_stack_name=stack', 'tripleo_vip_net=storage_mgmt']
)
fake_external_port = stubs.FakeNeutronPort(
    id='external_port_id',
    dns_name='overcloud',
    fixed_ips=[{'ip_address': '10.0.5.1',
                'subnet_id': 'external_subnet_id'}],
    tags=['tripleo_stack_name=stack', 'tripleo_vip_net=External']
)


@mock.patch.object(openstack.connection, 'Connection', autospec=True)
class TestTripleoOvercloudVipProvision(tests_base.TestCase):

    def setUp(self):
        super(TestTripleoOvercloudVipProvision, self).setUp()

        # Helper function to convert array to generator
        self.a2g = lambda x: (n for n in x)

    def test_get_net_name_map(self, mock_conn):
        mock_conn.network.networks.return_value = self.a2g(
            [fake_ctlplane, fake_internal_api, fake_storage_mgmt,
             fake_external])
        self.assertEqual({'ctlplane': 'ControlPlane',
                          'external': 'External',
                          'internal_api': 'InternalApi',
                          'storage_mgmt': 'StorageMgmt'},
                         plugin.get_net_name_map(mock_conn))

    def test_populate_net_vip_env(self, mock_conn):
        mock_conn.network.networks.return_value = self.a2g(
            [fake_ctlplane, fake_internal_api, fake_storage_mgmt,
             fake_external])
        mock_conn.network.ports.side_effect = [
            self.a2g([fake_ctlplane_port]),
            self.a2g([fake_internal_api_port]),
            self.a2g([fake_storage_mgmt_port]),
            self.a2g([fake_external_port])
        ]
        mock_conn.network.get_network.return_value = fake_ctlplane
        mock_conn.network.get_subnet.side_effect = [fake_ctlplane_subnet,
                                                    fake_internal_api_subnet,
                                                    fake_storage_mgmt_subnet,
                                                    fake_external_subnet]
        vip_data = [
            {'name': 'control_virtual_ip', 'network': 'ctlplane'},
            {'name': 'internal_api_virtual_ip', 'network': 'internal_api'},
            {'name': 'storage_mgmt_virtual_ip', 'network': 'storage_mgmt'},
            {'name': 'external_virtual_ip', 'network': 'external'}]
        env = {}
        templates = '/foo/tht_root'
        plugin.populate_net_vip_env(mock_conn, 'stack', NET_MAPS, vip_data,
                                    env, templates)
        self.assertEqual({
            'ControlPlaneVipData': {
                'name': 'control_virtual_ip',
                'fixed_ips': [{'ip_address': '192.168.24.1'}],
                'network': {'tags': ['foo', 'bar']},
                'subnets': [{'ip_version': 4}]},
            'VipPortMap': {
                'external': {'ip_address': '10.0.5.1',
                             'ip_address_uri': '10.0.5.1',
                             'ip_subnet': '10.0.5.1/24'},
                'internal_api': {'ip_address': '10.0.1.1',
                                 'ip_address_uri': '10.0.1.1',
                                 'ip_subnet': '10.0.1.1/24'},
                'storage_mgmt': {'ip_address': '10.0.3.1',
                                 'ip_address_uri': '10.0.3.1',
                                 'ip_subnet': '10.0.3.1/24'}}},
            env['parameter_defaults'])
        self.assertEqual({
            'OS::TripleO::Network::Ports::ControlPlaneVipPort':
                '/foo/tht_root/network/ports/deployed_vip_ctlplane.yaml',
            'OS::TripleO::Network::Ports::ExternalVipPort':
                '/foo/tht_root/network/ports/deployed_vip_external.yaml',
            'OS::TripleO::Network::Ports::InternalApiVipPort':
                '/foo/tht_root/network/ports/deployed_vip_internal_api.yaml',
            'OS::TripleO::Network::Ports::StorageMgmtVipPort':
                '/foo/tht_root/network/ports/deployed_vip_storage_mgmt.yaml'},
            env['resource_registry'])
