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
import metalsmith
import mock
import openstack

from tripleo_ansible.ansible_plugins.modules import (
    tripleo_overcloud_network_ports as plugin)
from tripleo_ansible.tests import base as tests_base
from tripleo_ansible.tests import stubs

FAKE_INSTANCE = {
    'hostname': 'instance0',
    'network_config': {
      'default_route_network': ['ctlplane'],
    },
    'networks': [
        {'network': 'ctlplane', 'vif': True},
        {'network': 'foo', 'subnet': 'foo_subnet'},
        {'network': 'bar', 'subnet': 'bar_subnet'},
    ],
}

FAKE_NET_NAME_MAP = {
    'ctlplane': {
        'id': 'ctlplane_id',
        'name_upper': 'ctlplane',
        'subnets': {
            'ctlplane-subnet': 'ctlplane_subnet_id'
        }
    },
    'foo': {
        'id': 'foo_id',
        'name_upper': 'Foo',
        'subnets': {
            'foo_subnet': 'foo_subnet_id',
        }
    },
    'bar': {
        'id': 'bar_id',
        'name_upper': 'Bar',
        'subnets': {
            'bar_subnet': 'bar_subnet_id',
        }
    },
}

FAKE_NET_ID_MAP = {
    'ctlplane_id': 'ctlplane',
    'foo_id': 'foo',
    'bar_id': 'bar',
}

FAKE_CIDR_PREFIX_MAP = {
    'foo_id': '24',
    'bar_id': '64',
}

FAKE_MAPS = {
    'by_name': FAKE_NET_NAME_MAP,
    'by_id': FAKE_NET_ID_MAP,
    'cidr_prefix_map': FAKE_CIDR_PREFIX_MAP,
}

STACK = 'overcloud'


class TestTripleoOvercloudNetworkPorts(tests_base.TestCase):

    def setUp(self):
        super(TestTripleoOvercloudNetworkPorts, self).setUp()

        # Helper function to convert array to generator
        self.a2g = lambda x: (n for n in x)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_delete_ports(self, mock_conn):
        port1 = stubs.FakeNeutronPort(id='port1_id')
        port2 = stubs.FakeNeutronPort(id='port2_id')
        plugin.delete_ports(mock_conn, [port1, port2])
        mock_conn.network.delete_port.assert_has_calls([mock.call('port1_id'),
                                                        mock.call('port2_id')])

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_pre_provisioned_ports(self, mock_conn):
        result = {'changed': False}
        inst_ports = []
        tags = set(['tripleo_stack_name=overcloud',
                    'tripleo_ironic_uuid=ironic_uuid'])
        fake_instance = copy.deepcopy(FAKE_INSTANCE)
        fake_instance['networks'] = [{'network': 'foo', 'port': 'some_port'}]
        some_port = stubs.FakeNeutronPort(name='some_port',
                                          id='some_port_id',
                                          tags=[])
        mock_conn.network.find_port.return_value = some_port
        plugin.pre_provisioned_ports(result, mock_conn, FAKE_MAPS,
                                     fake_instance, inst_ports, tags)
        mock_conn.network.find_port.assert_called_with(
            'some_port', network_id=FAKE_NET_NAME_MAP['foo']['id'])

        mock_conn.network.set_tags.assert_called_with(some_port, mock.ANY)
        set_tags_args = mock_conn.network.set_tags.call_args.args
        self.assertTrue(tags == set(set_tags_args[1]))

        self.assertEqual([some_port], inst_ports)
        self.assertTrue(result['changed'])

    def test_generate_port_defs_create(self):
        inst_ports = []
        create_port_defs, update_port_defs = plugin.generate_port_defs(
            FAKE_MAPS, FAKE_INSTANCE, inst_ports)
        self.assertEqual([
            {'name': 'instance0_Foo',
             'dns_name': 'instance0',
             'network_id': 'foo_id',
             'fixed_ips': [{'subnet_id': 'foo_subnet_id'}]},
            {'name': 'instance0_Bar',
             'dns_name': 'instance0',
             'network_id': 'bar_id',
             'fixed_ips': [{'subnet_id': 'bar_subnet_id'}]},
        ], create_port_defs)
        self.assertEqual([], update_port_defs)

    def test_generate_port_defs_update(self):
        port_foo = stubs.FakeNeutronPort(
            name='instance0_Foo', network_id='foo_id',
            fixed_ips=[{'subnet_id': 'foo_subnet_id'}])
        port_bar = stubs.FakeNeutronPort(
            name='instance0_Bar', network_id='bar_id',
            fixed_ips=[{'subnet_id': 'bar_subnet_id'}])
        inst_ports = [port_foo, port_bar]
        create_port_defs, update_port_defs = plugin.generate_port_defs(
            FAKE_MAPS, FAKE_INSTANCE, inst_ports)
        self.assertEqual([], create_port_defs)
        self.assertEqual([
            {'name': 'instance0_Foo',
             'dns_name': 'instance0',
             'network_id': 'foo_id',
             'fixed_ips': [{'subnet_id': 'foo_subnet_id'}]},
            {'name': 'instance0_Bar',
             'dns_name': 'instance0',
             'network_id': 'bar_id',
             'fixed_ips': [{'subnet_id': 'bar_subnet_id'}]}
        ], update_port_defs)

    def test_generate_port_defs_create_and_update(self):
        port_foo = stubs.FakeNeutronPort(
            name='instance0_Foo', network_id='foo_id',
            fixed_ips=[{'subnet_id': 'foo_subnet_id'}])
        inst_ports = [port_foo]
        create_port_defs, update_port_defs = plugin.generate_port_defs(
            FAKE_MAPS, FAKE_INSTANCE, inst_ports)
        self.assertEqual([
            {'name': 'instance0_Bar',
             'dns_name': 'instance0',
             'network_id': 'bar_id',
             'fixed_ips': [{'subnet_id': 'bar_subnet_id'}]},
        ], create_port_defs)
        self.assertEqual([
            {'name': 'instance0_Foo',
             'dns_name': 'instance0',
             'network_id': 'foo_id',
             'fixed_ips': [{'subnet_id': 'foo_subnet_id'}]},
        ], update_port_defs)

    def test_generate_port_defs_subnet_not_set(self):
        inst_ports = []
        instance = copy.deepcopy(FAKE_INSTANCE)
        del instance['networks'][1]['subnet']
        del instance['networks'][2]['subnet']
        create_port_defs, update_port_defs = plugin.generate_port_defs(
            FAKE_MAPS, instance, inst_ports)
        self.assertEqual([
            {'name': 'instance0_Foo',
             'dns_name': 'instance0',
             'network_id': 'foo_id',
             'fixed_ips': [{'subnet_id': 'foo_subnet_id'}]},
            {'name': 'instance0_Bar',
             'dns_name': 'instance0',
             'network_id': 'bar_id',
             'fixed_ips': [{'subnet_id': 'bar_subnet_id'}]},
        ], create_port_defs)
        self.assertEqual([], update_port_defs)

    def test_generate_port_defs_multi_subnet_raise_if_subnet_not_set(self):
        inst_ports = []
        instance = copy.deepcopy(FAKE_INSTANCE)
        del instance['networks'][1]['subnet']
        del instance['networks'][2]['subnet']
        maps = copy.deepcopy(FAKE_MAPS)
        maps['by_name']['foo']['subnets'].update(
            {'bas_subnet': 'baz_subnet_id'})
        msg = ('The "subnet" or "fixed_ip" must be set for the instance0 port '
               'on the foo network since there are multiple subnets')
        self.assertRaisesRegex(Exception, msg,
                               plugin.generate_port_defs,
                               maps, instance, inst_ports)

    def test_generate_port_defs_multi_subnet_fixed_ip(self):
        inst_ports = []
        instance = copy.deepcopy(FAKE_INSTANCE)
        del instance['networks'][1]['subnet']
        del instance['networks'][2]['subnet']
        instance['networks'][1]['fixed_ip'] = 'baz_fixed_ip'
        instance['networks'][2]['fixed_ip'] = 'bar_fixed_ip'
        maps = copy.deepcopy(FAKE_MAPS)
        maps['by_name']['foo']['subnets'].update(
            {'bas_subnet': 'baz_subnet_id'})
        create_port_defs, update_port_defs = plugin.generate_port_defs(
            maps, instance, inst_ports)
        self.assertEqual([
            {'name': 'instance0_Foo',
             'dns_name': 'instance0',
             'network_id': 'foo_id',
             'fixed_ips': [{'ip_address': 'baz_fixed_ip'}]},
            {'name': 'instance0_Bar',
             'dns_name': 'instance0',
             'network_id': 'bar_id',
             'fixed_ips': [{'ip_address': 'bar_fixed_ip'}]},
        ], create_port_defs)
        self.assertEqual([], update_port_defs)

    def test_fixed_ips_need_update(self):
        fake_port = stubs.FakeNeutronPort(
            fixed_ips=[{'ip_address': '192.168.24.24', 'subnet_id': 'foo_id'}])

        port_def = {'fixed_ips': [{'ip_address': '192.168.24.24'}]}
        self.assertFalse(plugin.fixed_ips_need_update(port_def, fake_port))

        port_def = {'fixed_ips': [{'subnet_id': 'foo_id'}]}
        self.assertFalse(plugin.fixed_ips_need_update(port_def, fake_port))

        port_def = {'fixed_ips': [{'subnet_id': 'bar_id'}]}
        self.assertTrue(plugin.fixed_ips_need_update(port_def, fake_port))

        port_def = {'fixed_ips': [{'subnet_id': 'foo_id'},
                                  {'ip_address': '192.168.25.24'}]}
        self.assertTrue(plugin.fixed_ips_need_update(port_def, fake_port))

    @mock.patch.object(plugin, 'fixed_ips_need_update', autospec=True)
    def test_port_need_update(self, mock_fixed_ips_need_update):
        port_def = {'name': 'foo', 'network_id': 'foo_id', 'fixed_ips': []}

        mock_fixed_ips_need_update.return_value = True
        self.assertEqual({'fixed_ips': []},
                         plugin.port_need_update(port_def, mock.ANY))

        mock_fixed_ips_need_update.return_value = False
        self.assertEqual({}, plugin.port_need_update(port_def, mock.ANY))

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_create_ports(self, mock_conn):
        result = {'changed': False}
        inst_ports = []
        network_config = {'default_route_network': ['foo']}
        tags = set(['tripleo_stack_name=overcloud',
                    'tripleo_ironic_uuid=ironic_uuid'])
        expected_tags = copy.deepcopy(tags)
        port_foo = stubs.FakeNeutronPort(
            name='instance0_foo', network_id='foo_id',
            fixed_ips=[{'subnet_id': 'foo_subnet_id'}])
        port_bar = stubs.FakeNeutronPort(
            name='instance0_bar', network_id='bar_id',
            fixed_ips=[{'subnet_id': 'bar_subnet_id'}])
        create_port_defs = [
            dict(name='instance0_foo', network_id='foo_id',
                 fixed_ips=[{'subnet_id': 'foo_subnet_id'}]),
            dict(name='instance0_bar', network_id='bar_id',
                 fixed_ips=[{'subnet_id': 'bar_subnet_id'}]),
        ]
        mock_conn.network.create_ports.return_value = self.a2g(
            [port_foo, port_bar])
        plugin.create_ports(result, mock_conn, create_port_defs, inst_ports,
                            tags, FAKE_MAPS, network_config)
        mock_conn.network.create_ports.assert_has_calls([
            mock.call([
                {'name': 'instance0_foo',
                 'network_id': 'foo_id',
                 'fixed_ips': [{'subnet_id': 'foo_subnet_id'}]},
                {'name': 'instance0_bar',
                 'network_id': 'bar_id',
                 'fixed_ips': [{'subnet_id': 'bar_subnet_id'}]}
            ])
        ])
        mock_conn.network.set_tags.assert_has_calls([
            mock.call(port_foo, mock.ANY),
            mock.call(port_bar, mock.ANY)
        ])
        set_tag_args = mock_conn.network.set_tags.call_args_list
        self.assertEqual(set(set_tag_args[1][0][1]), expected_tags)
        # Default route tag only on the 'foo' network port
        expected_tags.update({'tripleo_default_route=true'})
        self.assertEqual(set(set_tag_args[0][0][1]), expected_tags)

        self.assertEqual([port_foo, port_bar], inst_ports)
        self.assertTrue(result['changed'])

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test_update_ports(self, mock_conn):
        result = {'changed': False}
        network_config = {'default_route_network': ['foo']}
        tags = set(['tripleo_hostname=instance0',
                    'tripleo_stack_name=overcloud',
                    'tripleo_ironic_uuid=ironic_uuid'])
        expected_tags = copy.deepcopy(tags)
        port_foo = stubs.FakeNeutronPort(
            id='port_foo_id', name='instance0_foo', network_id='foo_id',
            fixed_ips=[{'subnet_id': 'NEED_UPDATE'}], tags=[])
        port_bar = stubs.FakeNeutronPort(
            id='port_bar_id', name='instance0_bar', network_id='bar_id',
            fixed_ips=[{'subnet_id': 'NEED_UPDATE'}], tags=[])
        inst_ports = [port_foo, port_bar]
        update_port_defs = [
            dict(name='instance0_foo', network_id='foo_id',
                 fixed_ips=[{'subnet_id': 'foo_subnet_id'}]),
            dict(name='instance0_bar', network_id='bar_id',
                 fixed_ips=[{'subnet_id': 'bar_subnet_id'}]),
        ]
        plugin.update_ports(result, mock_conn, update_port_defs, inst_ports,
                            tags, FAKE_MAPS, network_config)
        mock_conn.network.update_port.assert_has_calls(
            [mock.call('port_foo_id',
                       {'fixed_ips': [{'subnet_id': 'foo_subnet_id'}]}),
             mock.call('port_bar_id',
                       {'fixed_ips': [{'subnet_id': 'bar_subnet_id'}]})])
        mock_conn.network.set_tags.assert_has_calls([
            mock.call(port_foo, mock.ANY),
            mock.call(port_bar, mock.ANY)
        ])
        set_tag_args = mock_conn.network.set_tags.call_args_list
        self.assertEqual(set(set_tag_args[1][0][1]), expected_tags)
        # Default route tag only on the 'foo' network port
        expected_tags.update({'tripleo_default_route=true'})
        self.assertEqual(set(set_tag_args[0][0][1]), expected_tags)

        self.assertTrue(result['changed'])

    @mock.patch.object(plugin, 'update_ports', autospec=True)
    @mock.patch.object(plugin, 'create_ports', autospec=True)
    @mock.patch.object(plugin, 'pre_provisioned_ports', autospec=True)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test__provision_ports_create(self, mock_conn, mock_pre_provisioned,
                                     mock_create_ports, mock_update_ports):
        create_port_defs = [
            dict(name='instance0_Foo',
                 dns_name='instance0',
                 network_id='foo_id',
                 fixed_ips=[{'subnet_id': 'foo_subnet_id'}]),
            dict(name='instance0_Bar',
                 dns_name='instance0',
                 network_id='bar_id',
                 fixed_ips=[{'subnet_id': 'bar_subnet_id'}]),
        ]
        mock_conn.network.ports.return_value = self.a2g([])
        expected_tags = {'tripleo_ironic_uuid=ironic_uuid',
                         'tripleo_role=role',
                         'tripleo_stack_name=overcloud'}
        network_config = FAKE_INSTANCE['network_config']
        plugin._provision_ports({}, mock_conn, STACK, FAKE_INSTANCE,
                                FAKE_MAPS, {}, 'ironic_uuid', 'role')
        mock_pre_provisioned.assert_called_with(mock.ANY, mock_conn, FAKE_MAPS,
                                                FAKE_INSTANCE, mock.ANY,
                                                expected_tags)
        mock_create_ports.assert_called_with(mock.ANY, mock_conn,
                                             create_port_defs,
                                             mock.ANY, expected_tags,
                                             FAKE_MAPS, network_config)
        mock_update_ports.assert_not_called()

    @mock.patch.object(plugin, 'update_ports', autospec=True)
    @mock.patch.object(plugin, 'create_ports', autospec=True)
    @mock.patch.object(plugin, 'pre_provisioned_ports', autospec=True)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test__provision_ports_update(self, mock_conn, mock_pre_provisioned,
                                     mock_create_ports, mock_update_ports):
        port_foo = stubs.FakeNeutronPort(
            name='instance0_Foo',
            dns_name='instance0',
            network_id='foo_id',
            fixed_ips=[{'subnet_id': 'foo_subnet_id'}],
            tags=[])
        port_bar = stubs.FakeNeutronPort(
            name='instance0_Bar',
            dns_name='instance0',
            network_id='bar_id',
            fixed_ips=[{'subnet_id': 'bar_subnet_id'}],
            tags=[])
        update_port_defs = [
            dict(name='instance0_Foo',
                 dns_name='instance0',
                 network_id='foo_id',
                 fixed_ips=[{'subnet_id': 'foo_subnet_id'}]),
            dict(name='instance0_Bar',
                 dns_name='instance0',
                 network_id='bar_id',
                 fixed_ips=[{'subnet_id': 'bar_subnet_id'}]),
        ]
        expected_tags = {'tripleo_ironic_uuid=ironic_uuid',
                         'tripleo_role=role',
                         'tripleo_stack_name=overcloud'}
        network_config = FAKE_INSTANCE['network_config']
        mock_conn.network.ports.return_value = self.a2g([port_foo, port_bar])
        plugin._provision_ports({}, mock_conn, STACK, FAKE_INSTANCE,
                                FAKE_MAPS, {}, 'ironic_uuid', 'role')
        mock_pre_provisioned.assert_called_with(mock.ANY, mock_conn,
                                                FAKE_MAPS, FAKE_INSTANCE,
                                                mock.ANY, expected_tags)
        mock_create_ports.assert_not_called()
        mock_update_ports.assert_called_with(mock.ANY, mock_conn,
                                             update_port_defs,
                                             [port_foo, port_bar],
                                             expected_tags, FAKE_MAPS,
                                             network_config)

    @mock.patch.object(plugin, 'update_ports', autospec=True)
    @mock.patch.object(plugin, 'create_ports', autospec=True)
    @mock.patch.object(plugin, 'pre_provisioned_ports', autospec=True)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test__provision_ports_create_and_update(self, mock_conn,
                                                mock_pre_provisioned,
                                                mock_create_ports,
                                                mock_update_ports):
        port_foo = stubs.FakeNeutronPort(
            name='instance0_Foo',
            dns_name='instance0',
            network_id='foo_id',
            fixed_ips=[{'subnet_id': 'foo_subnet_id'}],
            tags=[])
        create_port_defs = [
            dict(name='instance0_Bar',
                 dns_name='instance0',
                 network_id='bar_id',
                 fixed_ips=[{'subnet_id': 'bar_subnet_id'}]),
        ]
        update_port_defs = [
            dict(name='instance0_Foo',
                 dns_name='instance0',
                 network_id='foo_id',
                 fixed_ips=[{'subnet_id': 'foo_subnet_id'}]),
        ]
        mock_conn.network.ports.return_value = self.a2g([port_foo])
        expected_tags = {'tripleo_ironic_uuid=ironic_uuid',
                         'tripleo_role=role',
                         'tripleo_stack_name=overcloud'}
        network_config = FAKE_INSTANCE['network_config']
        plugin._provision_ports({}, mock_conn, STACK, FAKE_INSTANCE,
                                FAKE_MAPS, {}, 'ironic_uuid', 'role')
        mock_pre_provisioned.assert_called_with(mock.ANY, mock_conn,
                                                FAKE_MAPS, FAKE_INSTANCE,
                                                mock.ANY, expected_tags)
        mock_create_ports.assert_called_with(mock.ANY, mock_conn,
                                             create_port_defs, mock.ANY,
                                             expected_tags, FAKE_MAPS,
                                             network_config)
        mock_update_ports.assert_called_with(mock.ANY, mock_conn,
                                             update_port_defs, [port_foo],
                                             expected_tags, FAKE_MAPS,
                                             network_config)

    @mock.patch.object(plugin, 'delete_ports', autospec=True)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    def test__unprovision_ports(self, mock_conn, mock_delete_ports):
        result = {'changed': False, 'instance_port_map': {}}
        port_foo = stubs.FakeNeutronPort(
            name='instance_foo',
            dns_name='instance0',
            network_id='foo_id',
            fixed_ips=[{'subnet_id': 'foo_subnet_id'}])
        port_bar = stubs.FakeNeutronPort(
            name='instance_bar',
            dns_name='instance0',
            network_id='bar_id',
            fixed_ips=[{'subnet_id': 'bar_subnet_id'}])
        mock_conn.network.ports.return_value = self.a2g([port_foo, port_bar])
        plugin._unprovision_ports(result, mock_conn, STACK, FAKE_INSTANCE,
                                  None)
        mock_delete_ports.assert_called_with(mock_conn, [port_foo, port_bar])
        self.assertTrue(result['changed'])

    def test_generate_node_port_map(self):
        result = dict(node_port_map=dict())
        ports_by_node = dict(
            node01=[
                stubs.FakeNeutronPort(
                    network_id='foo_id',
                    fixed_ips=[{'ip_address': '192.168.24.1',
                                'subnet_id': 'foo_id'}]),
                stubs.FakeNeutronPort(
                    network_id='bar_id',
                    fixed_ips=[{'ip_address': '2001:DB8:1::1',
                                'subnet_id': 'bar_id'}])],
            node02=[
                stubs.FakeNeutronPort(
                    network_id='foo_id',
                    fixed_ips=[{'ip_address': '192.168.24.1',
                                'subnet_id': 'foo_id'}]),
                stubs.FakeNeutronPort(
                    network_id='bar_id',
                    fixed_ips=[{'ip_address': '2001:DB8:1::2',
                                'subnet_id': 'bar_id'}])]
        )
        plugin.generate_node_port_map(result, FAKE_MAPS, ports_by_node)
        self.assertEqual(
            {'node01': {'bar': {'ip_address': '2001:DB8:1::1',
                                'ip_address_uri': '[2001:DB8:1::1]',
                                'ip_subnet': '2001:DB8:1::1/64'},
                        'foo': {'ip_address': '192.168.24.1',
                                'ip_address_uri': '192.168.24.1',
                                'ip_subnet': '192.168.24.1/24'}},
             'node02': {'bar': {'ip_address': '2001:DB8:1::2',
                                'ip_address_uri': '[2001:DB8:1::2]',
                                'ip_subnet': '2001:DB8:1::2/64'},
                        'foo': {'ip_address': '192.168.24.1',
                                'ip_address_uri': '192.168.24.1',
                                'ip_subnet': '192.168.24.1/24'}}},
            result['node_port_map'])

    def test_validate_instance_nets_in_net_map(self):
        instances = [copy.deepcopy(FAKE_INSTANCE)]
        instances[0]['networks'].append({'network': 'missing_net',
                                         'subnet': 'missing_subnet'},)
        msg = 'Network missing_net for instance {} not found.'.format(
            FAKE_INSTANCE['hostname'])
        self.assertRaisesRegex(Exception, msg,
                               plugin.validate_instance_nets_in_net_map,
                               instances, FAKE_MAPS)

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    @mock.patch.object(metalsmith, 'Provisioner', autospec=True)
    def test__tag_metalsmith_instance_ports(self, mock_provisioner, mock_conn):
        result = {'changed': False}
        tags = {'tripleo_stack_name={}'.format(STACK),
                'tripleo_ironic_uuid=ironic_uuid',
                'tripleo_role=role',
                'tripleo_ironic_vif_port=true'}
        expected_tags = copy.deepcopy(tags)
        expected_tags.update({'tripleo_default_route=true'})
        fake_nic = stubs.FakeNeutronPort(name='hostname-ctlplane',
                                         network_id='ctlplane_id',
                                         id='port_uuid',
                                         tags=[])
        fake_instance = mock.Mock()
        fake_instance.nics.return_value = [fake_nic]
        mock_provisioner.show_instance.return_value = fake_instance
        network_config = FAKE_INSTANCE['network_config']
        default_route_network = network_config['default_route_network']
        plugin._tag_metalsmith_instance_ports(result, mock_conn,
                                              mock_provisioner, 'ironic_uuid',
                                              'hostname', tags,
                                              default_route_network, FAKE_MAPS)
        mock_conn.network.set_tags.assert_called_with(fake_nic, mock.ANY)
        set_tags_args = mock_conn.network.set_tags.call_args.args
        self.assertEqual(set(expected_tags), set(set_tags_args[1]))

        self.assertTrue(result['changed'])

    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    @mock.patch.object(metalsmith, 'Provisioner', autospec=True)
    def test__tag_metalsmith_instance_ports_tags_already_set(
            self, mock_provisioner, mock_conn):
        result = {'changed': False}
        tags = {'tripleo_stack_name={}'.format(STACK),
                'tripleo_ironic_uuid=ironic_uuid',
                'tripleo_role=role',
                'tripleo_ironic_vif_port=true'}
        fake_nic = stubs.FakeNeutronPort(
            name='hostname-ctlplane', dns_name='hostname', id='port_uuid',
            network_id='ctlplane_id',
            tags=['tripleo_stack_name={}'.format(STACK),
                  'tripleo_ironic_uuid=ironic_uuid',
                  'tripleo_role=role',
                  'tripleo_ironic_vif_port=true',
                  'tripleo_default_route=true'])
        fake_instance = mock.Mock()
        fake_instance.nics.return_value = [fake_nic]
        mock_provisioner.show_instance.return_value = fake_instance
        network_config = FAKE_INSTANCE['network_config']
        default_route_network = network_config['default_route_network']
        plugin._tag_metalsmith_instance_ports(
            result, mock_conn, mock_provisioner, 'ironic_uuid', 'hostname',
            tags, default_route_network, FAKE_MAPS)
        mock_conn.network.set_tags.assert_not_called()

        self.assertFalse(result['changed'])

    @mock.patch.object(plugin, '_tag_metalsmith_instance_ports', autospec=True)
    @mock.patch.object(openstack.connection, 'Connection', autospec=True)
    @mock.patch.object(metalsmith, 'Provisioner', autospec=True)
    def test_tag_metalsmith_managed_ports(self, mock_provisioner, mock_conn,
                                          mock_tag_msmith_ports):
        result = {'changed': False, 'instance_port_map': {}}
        mock_conn.config = mock.Mock()
        concurrency = 1
        uuid_by_hostname = {FAKE_INSTANCE['hostname']: 'fake_uuid'}
        hostname_role_map = {FAKE_INSTANCE['hostname']: 'fake_role'}
        instances_by_hostname = {FAKE_INSTANCE['hostname']: FAKE_INSTANCE}
        plugin.tag_metalsmith_managed_ports(result, mock_conn, concurrency,
                                            STACK, uuid_by_hostname,
                                            hostname_role_map,
                                            instances_by_hostname, FAKE_MAPS)
        expected_tags = {'tripleo_role=fake_role',
                         'tripleo_ironic_vif_port=true',
                         'tripleo_stack_name=overcloud',
                         'tripleo_ironic_uuid=fake_uuid'}
        mock_tag_msmith_ports.assert_called_with(
            result, mock_conn, mock.ANY, 'fake_uuid',
            FAKE_INSTANCE['hostname'], expected_tags,
            FAKE_INSTANCE['network_config']['default_route_network'],
            FAKE_MAPS)
