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

import jsonschema
import metalsmith
from unittest import mock
from openstack import exceptions as sdk_exc

from tripleo_ansible.tests import base

from tripleo_ansible.ansible_plugins.module_utils import baremetal_deploy as bd  # noqa


class TestBaremetalDeployUtils(base.TestCase):

    def test_build_hostname_format(self):
        self.assertEqual(
            '%stackname%-controller-%index%',
            bd.build_hostname_format(None, 'Controller')
        )
        self.assertEqual(
            '%stackname%-novacompute-%index%',
            bd.build_hostname_format(None, 'Compute')
        )
        self.assertEqual(
            'server-%index%',
            bd.build_hostname_format('server-%index%', 'Compute')
        )

    def test_build_hostname(self):
        self.assertEqual(
            'overcloud-controller-2',
            bd.build_hostname(
                '%stackname%-controller-%index%', 2, 'overcloud'
            )
        )
        self.assertEqual(
            'server-2',
            bd.build_hostname(
                'server-%index%', 2, 'overcloud'
            )
        )

    def test_merge_networks_defaults(self):
        # Network defined only in role defaults is appended
        defaults = {'networks': [{'network': 'role_net'}]}
        instance = {'networks': [{'network': 'instance_net'}]}
        bd.merge_networks_defaults(defaults, instance)
        self.assertEqual({'networks': [{'network': 'instance_net'},
                                       {'network': 'role_net'}]}, instance)

        # Network defined in both role defaults and instance is not appended
        instance = {'networks': [{'network': 'instance_net'},
                                 {'network': 'role_net'}]}
        bd.merge_networks_defaults(defaults, instance)
        self.assertEqual({'networks': [{'network': 'instance_net'},
                                       {'network': 'role_net'}]}, instance)

        # Network defined in role defaults and in instance with richer data
        # is not appended.
        instance = {'networks': [{'network': 'instance_net'},
                                 {'network': 'role_net', 'port': 'port_uuid'}]}
        bd.merge_networks_defaults(defaults, instance)
        self.assertEqual({'networks': [{'network': 'instance_net'},
                                       {'network': 'role_net',
                                        'port': 'port_uuid'}]}, instance)

        # Network defined in role defaults with richer data compared to the
        # instance is not appended.
        defaults = {'networks': [{'network': 'role_net',
                                  'subnet': 'subnet_name'}]}
        instance = {'networks': [{'network': 'instance_net'},
                                 {'network': 'role_net'}]}
        bd.merge_networks_defaults(defaults, instance)
        self.assertEqual({'networks': [{'network': 'instance_net'},
                                       {'network': 'role_net'}]}, instance)

    def test_merge_network_config_defaults(self):
        # Config defined only in role defaults is appended
        defaults = {'network_config': {'foo': 'bar'}}
        instance = {'network_config': {'bar': 'foo'}}
        bd.merge_network_config_defaults(defaults, instance)
        self.assertEqual({'network_config': {'foo': 'bar', 'bar': 'foo'}},
                         instance)

        # Config defined in both role defaults and instance,
        #   instance value preferred
        instance = {'network_config': {'foo': 'bar', 'bar': 'override'}}
        bd.merge_networks_defaults(defaults, instance)
        self.assertEqual({'network_config': {'foo': 'bar', 'bar': 'override'}},
                         instance)


class TestExpandRoles(base.TestCase):

    default_image = {'href': 'overcloud-full'}
    default_network = [{'network': 'ctlplane', 'vif': True}]

    def test_simple(self):
        roles = [
            {'name': 'Compute'},
            {'name': 'Controller'},
        ]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )

        self.assertEqual(
            [
                {'hostname': 'overcloud-novacompute-0',
                 'image': {'href': 'overcloud-full'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Compute'}}},
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Controller'}}},
            ],
            instances)
        self.assertEqual(
            {
                'ComputeHostnameFormat':
                '%stackname%-novacompute-%index%',
                'ComputeCount': 1,
                'ControllerHostnameFormat':
                '%stackname%-controller-%index%',
                'ControllerCount': 1,
                'HostnameMap': {
                    'overcloud-novacompute-0': 'overcloud-novacompute-0',
                    'overcloud-controller-0': 'overcloud-controller-0'
                }
            },
            environment['parameter_defaults'])
        self.assertEqual({'overcloud-controller-0': 'Controller',
                          'overcloud-novacompute-0': 'Compute'},
                         hostname_role_map)

    def test_default_network(self):
        roles = [
            {'name': 'Compute'},
            {'name': 'Controller'},
        ]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image, self.default_network
        )
        self.assertEqual(
            [
                {'hostname': 'overcloud-novacompute-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'ctlplane', 'vif': True}],
                 'nics': [{'network': 'ctlplane'}],
                 'config_drive': {'meta_data': {'instance-type': 'Compute'}}},
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'ctlplane', 'vif': True}],
                 'nics': [{'network': 'ctlplane'}],
                 'config_drive': {'meta_data': {'instance-type': 'Controller'}}},
            ],
            instances)
        self.assertEqual({'overcloud-controller-0': 'Controller',
                          'overcloud-novacompute-0': 'Compute'},
                         hostname_role_map)

    def test_networks_set_no_default_network(self):
        roles = [
            {'name': 'Compute',
             'defaults': {
                 'networks': [
                     {'network': 'some_net', 'vif': True},
                 ]}
             },
            {'name': 'Controller',
             'defaults': {
                 'networks': [
                     {'network': 'some_net', 'vif': True},
                 ]}
             },
        ]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image, None
        )
        self.assertEqual(
            [
                {'hostname': 'overcloud-novacompute-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'some_net', 'vif': True}],
                 'nics': [{'network': 'some_net'}],
                 'config_drive': {'meta_data': {'instance-type': 'Compute'}}},
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'some_net', 'vif': True}],
                 'nics': [{'network': 'some_net'}],
                 'config_drive': {'meta_data': {'instance-type': 'Controller'}}},
            ],
            instances)
        self.assertEqual({'overcloud-controller-0': 'Controller',
                          'overcloud-novacompute-0': 'Compute'},
                         hostname_role_map)

    def test_networks_set_default_appended(self):
        roles = [
            {'name': 'Compute',
             'defaults': {
                 'networks': [
                     {'network': 'foo', 'subnet': 'foo_subnet'},
                 ]}
             },
            {'name': 'Controller',
             'defaults': {
                 'networks': [
                     {'network': 'foo', 'subnet': 'foo_subnet'},
                 ]}
             },
        ]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image, self.default_network
        )
        self.assertEqual(
            [
                {'hostname': 'overcloud-novacompute-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'foo', 'subnet': 'foo_subnet'},
                              {'network': 'ctlplane', 'vif': True}],
                 'nics': [{'network': 'ctlplane'}],
                 'config_drive': {'meta_data': {'instance-type': 'Compute'}}},
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'foo', 'subnet': 'foo_subnet'},
                              {'network': 'ctlplane', 'vif': True}],
                 'nics': [{'network': 'ctlplane'}],
                 'config_drive': {'meta_data': {'instance-type': 'Controller'}}},
            ],
            instances)
        self.assertEqual({'overcloud-controller-0': 'Controller',
                          'overcloud-novacompute-0': 'Compute'},
                         hostname_role_map)

    def test_networks_vif_set_default_appended(self):
        roles = [
            {'name': 'Compute',
             'defaults': {
                 'networks': [
                     {'network': 'foo', 'subnet': 'foo_subnet', 'vif': True},
                 ]}
             },
            {'name': 'Controller',
             'defaults': {
                 'networks': [
                     {'network': 'foo', 'subnet': 'foo_subnet', 'vif': True},
                 ]}
             },
        ]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image, self.default_network
        )
        self.assertEqual(
            [
                {'hostname': 'overcloud-novacompute-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [
                     {'network': 'foo', 'subnet': 'foo_subnet', 'vif': True},
                     {'network': 'ctlplane', 'vif': True}
                 ],
                 'nics': [{'network': 'foo', 'subnet': 'foo_subnet'},
                          {'network': 'ctlplane'}],
                 'config_drive': {'meta_data': {'instance-type': 'Compute'}}
                 },
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [
                     {'network': 'foo', 'subnet': 'foo_subnet', 'vif': True},
                     {'network': 'ctlplane', 'vif': True}
                 ],
                 'nics': [
                     {'network': 'foo', 'subnet': 'foo_subnet'},
                     {'network': 'ctlplane'}
                 ],
                 'config_drive': {'meta_data': {'instance-type': 'Controller'}},
                },
            ],
            instances)
        self.assertEqual({'overcloud-controller-0': 'Controller',
                          'overcloud-novacompute-0': 'Compute'},
                         hostname_role_map)

    def test_networks_nics_are_mutually_exclusive(self):
        # Neither 'nics' nor 'networks' - OK
        roles = [{'name': 'Compute', 'defaults': {}}]
        bd.expand(roles, 'overcloud', True, self.default_image)
        # 'networks' but not 'nics' - OK
        roles = [{'name': 'Compute', 'defaults': {'networks': []}}]
        bd.expand(roles, 'overcloud', True, self.default_image)
        # 'nics' but not 'networks' - OK
        roles = [{'name': 'Compute', 'defaults': {'nics': []}}]
        bd.expand(roles, 'overcloud', True, self.default_image)
        # 'networks' and 'nics' - mutually exclusive, Raises ValidationError
        roles = [{'name': 'Compute', 'defaults': {'networks': [], 'nics': []}}]
        self.assertRaises(
            jsonschema.exceptions.ValidationError,
            bd.expand, roles, 'overcloud', True, self.default_image)

    def test_image_in_defaults(self):
        roles = [{
            'name': 'Controller',
            'defaults': {
                'image': {
                    'href': 'file:///tmp/foo.qcow2',
                    'checksum': '12345678'
                }
            },
            'count': 3,
            'instances': [{
                'hostname': 'overcloud-controller-0',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'overcloud-controller-1',
            }]
        }]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual(
            [
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Controller'}}},
                {'hostname': 'overcloud-controller-1',
                 'image': {'href': 'file:///tmp/foo.qcow2',
                           'checksum': '12345678'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Controller'}}},
                {'hostname': 'overcloud-controller-2',
                 'image': {'href': 'file:///tmp/foo.qcow2',
                           'checksum': '12345678'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Controller'}}},
            ],
            instances)

    def test_with_parameters(self):
        roles = [{
            'name': 'Compute',
            'count': 2,
            'defaults': {
                'profile': 'compute'
            },
            'hostname_format': 'compute-%index%.example.com'
        }, {
            'name': 'Controller',
            'count': 3,
            'defaults': {
                'profile': 'control'
            },
            'hostname_format': 'controller-%index%.example.com'
        }]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image,
            user_name='heat-admin', ssh_public_keys='aaaa'
        )
        self.assertEqual(
            [
                {'hostname': 'compute-0.example.com',
                 'capabilities': {'profile': 'compute'},
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin',
                 'config_drive': {'meta_data': {
                     'instance-type': 'Compute'}}},
                {'hostname': 'compute-1.example.com',
                 'capabilities': {'profile': 'compute'},
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin',
                 'config_drive': {'meta_data': {
                     'instance-type': 'Compute'}}},
                {'hostname': 'controller-0.example.com',
                 'capabilities': {'profile': 'control'},
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin',
                 'config_drive': {'meta_data': {
                     'instance-type': 'Controller'}}},
                {'hostname': 'controller-1.example.com',
                 'capabilities': {'profile': 'control'},
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin',
                 'config_drive': {'meta_data': {
                     'instance-type': 'Controller'}}},
                {'hostname': 'controller-2.example.com',
                 'capabilities': {'profile': 'control'},
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin',
                 'config_drive': {'meta_data': {
                     'instance-type': 'Controller'}}},
            ],
            instances)
        self.assertEqual(
            {
                'ComputeHostnameFormat':
                'compute-%index%.example.com',
                'ComputeCount': 2,
                'ControllerHostnameFormat':
                'controller-%index%.example.com',
                'ControllerCount': 3,
                'HostnameMap': {
                    'compute-0.example.com': 'compute-0.example.com',
                    'compute-1.example.com': 'compute-1.example.com',
                    'controller-0.example.com': 'controller-0.example.com',
                    'controller-1.example.com': 'controller-1.example.com',
                    'controller-2.example.com': 'controller-2.example.com',
                }
            },
            environment['parameter_defaults'])
        self.assertEqual({'compute-0.example.com': 'Compute',
                          'compute-1.example.com': 'Compute',
                          'controller-0.example.com': 'Controller',
                          'controller-1.example.com': 'Controller',
                          'controller-2.example.com': 'Controller'},
                         hostname_role_map)

    def test_explicit_instances(self):
        roles = [{
            'name': 'Compute',
            'count': 2,
            'defaults': {
                'profile': 'compute'
            },
            'hostname_format': 'compute-%index%.example.com'
        }, {
            'name': 'Controller',
            'count': 2,
            'defaults': {
                'profile': 'control',
                'networks': [
                    {'network': 'foo', 'subnet': 'foo_subnet'},
                ]
            },
            'instances': [{
                'hostname': 'controller-X.example.com',
                'profile': 'control-X',
                'networks': [
                    {'network': 'inst_net', 'fixed_ip': '10.1.1.1'}
                ],
                'config_drive': {
                    'meta_data': {'foo': 'bar'}
                }
            }, {
                'name': 'node-0',
                'traits': ['CUSTOM_FOO'],
                'networks': [{'network': 'some_net', 'subnet': 'leaf-2',
                              'vif': True}],
                'config_drive': {
                    'cloud_config': {'bootcmd': ['echo hi']}
                }
            }]},
        ]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual(
            [
                {'hostname': 'compute-0.example.com',
                 'capabilities': {'profile': 'compute'},
                 'image': {'href': 'overcloud-full'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Compute'}}},
                {'hostname': 'compute-1.example.com',
                 'capabilities': {'profile': 'compute'},
                 'image': {'href': 'overcloud-full'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Compute'}}},
                {'hostname': 'controller-X.example.com',
                 'image': {'href': 'overcloud-full'},
                 'capabilities': {'profile': 'control-X'},
                 'networks': [{'fixed_ip': '10.1.1.1', 'network': 'inst_net'},
                              {'network': 'foo', 'subnet': 'foo_subnet'}],
                 'config_drive': {'meta_data': {
                     'foo': 'bar',
                     'instance-type': 'Controller'}},
                 },
                # Name provides the default for hostname later on.
                {'name': 'node-0',
                 'capabilities': {'profile': 'control'},
                 'hostname': 'node-0',
                 'networks': [
                     {'network': 'some_net', 'subnet': 'leaf-2', 'vif': True},
                     {'network': 'foo', 'subnet': 'foo_subnet'},
                 ],
                 'image': {'href': 'overcloud-full'},
                 'traits': ['CUSTOM_FOO'],
                 'nics': [{'network': 'some_net', 'subnet': 'leaf-2'}],
                 'config_drive': {
                     'cloud_config': {'bootcmd': ['echo hi']},
                     'meta_data': {'instance-type': 'Controller'}
                 }},
            ],
            instances)
        self.assertEqual(
            {
                'ComputeHostnameFormat':
                'compute-%index%.example.com',
                'ComputeCount': 2,
                'ControllerHostnameFormat':
                '%stackname%-controller-%index%',
                'ControllerCount': 2,
                'HostnameMap': {
                    'compute-0.example.com': 'compute-0.example.com',
                    'compute-1.example.com': 'compute-1.example.com',
                    'overcloud-controller-0': 'controller-X.example.com',
                    'overcloud-controller-1': 'node-0',
                }
            },
            environment['parameter_defaults'])
        self.assertEqual({'compute-0.example.com': 'Compute',
                          'compute-1.example.com': 'Compute',
                          'controller-X.example.com': 'Controller',
                          'node-0': 'Controller'},
                         hostname_role_map)

    def test_count_with_instances(self):
        roles = [{
            'name': 'Compute',
            'count': 2,
            'defaults': {
                'profile': 'compute',
            },
            'hostname_format': 'compute-%index%.example.com'
        }, {
            'name': 'Controller',
            'defaults': {
                'profile': 'control',
            },
            'count': 3,
            'instances': [{
                'hostname': 'controller-X.example.com',
                'profile': 'control-X'
            }, {
                'name': 'node-0',
                'traits': ['CUSTOM_FOO'],
                'nics': [{'subnet': 'leaf-2'}]},
            ]},
        ]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'compute-0.example.com',
                'capabilities': {'profile': 'compute'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Compute'}}
            }, {
                'hostname': 'compute-1.example.com',
                'capabilities': {'profile': 'compute'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Compute'}}
            }, {
                'hostname': 'controller-X.example.com',
                'capabilities': {'profile': 'control-X'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'node-0',
                'name': 'node-0',
                'nics': [{'subnet': 'leaf-2'}],
                'capabilities': {'profile': 'control'},
                'traits': ['CUSTOM_FOO'],
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'overcloud-controller-2',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }],
            instances)
        self.assertEqual({
            'ComputeCount': 2,
            'ComputeHostnameFormat':
                'compute-%index%.example.com',
            'ControllerCount': 3,
            'ControllerHostnameFormat':
                '%stackname%-controller-%index%',
            'HostnameMap': {
                'compute-0.example.com': 'compute-0.example.com',
                'compute-1.example.com': 'compute-1.example.com',
                'overcloud-controller-0': 'controller-X.example.com',
                'overcloud-controller-1': 'node-0',
                'overcloud-controller-2': 'overcloud-controller-2'}
            },
            environment['parameter_defaults'])
        self.assertEqual({'compute-0.example.com': 'Compute',
                          'compute-1.example.com': 'Compute',
                          'controller-X.example.com': 'Controller',
                          'node-0': 'Controller',
                          'overcloud-controller-2': 'Controller'},
                         hostname_role_map)

    def test_unprovisioned(self):
        roles = [{
            'name': 'Controller',
            'defaults': {
                'profile': 'control',
            },
            'count': 2,
            'instances': [{
                'hostname': 'overcloud-controller-1',
                'provisioned': False
            }, {
                'hostname': 'overcloud-controller-2',
                'provisioned': False
            }]
        }]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'overcloud-controller-0',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'overcloud-controller-3',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }],
            instances)
        self.assertEqual({
            'ControllerCount': 2,
            'ControllerRemovalPolicies': [
                {'resource_list': [1, 2]}
            ],
            'ControllerHostnameFormat':
                '%stackname%-controller-%index%',
            'HostnameMap': {
                'overcloud-controller-0': 'overcloud-controller-0',
                'overcloud-controller-1': 'overcloud-controller-1',
                'overcloud-controller-2': 'overcloud-controller-2',
                'overcloud-controller-3': 'overcloud-controller-3'}
            },
            environment['parameter_defaults'])
        self.assertEqual({'overcloud-controller-0': 'Controller',
                          'overcloud-controller-3': 'Controller'},
                         hostname_role_map)

        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', False, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'overcloud-controller-1',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'overcloud-controller-2',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }],
            instances)
        self.assertEqual({}, environment)
        self.assertEqual({'overcloud-controller-1': 'Controller',
                          'overcloud-controller-2': 'Controller'},
                         hostname_role_map)

    def test_reprovisioned(self):
        roles = [{
            'name': 'Controller',
            'defaults': {
                'profile': 'control',
            },
            'count': 4,
            'instances': [{
                'hostname': 'overcloud-controller-1',
                'provisioned': False
            }, {
                'hostname': 'overcloud-controller-2',
                'provisioned': False
            }]
        }]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'overcloud-controller-0',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'overcloud-controller-3',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'overcloud-controller-4',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'overcloud-controller-5',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }],
            instances)
        self.assertEqual({
            'ControllerCount': 4,
            'ControllerRemovalPolicies': [
                {'resource_list': [1, 2]}
            ],
            'ControllerHostnameFormat':
                '%stackname%-controller-%index%',
            'HostnameMap': {
                'overcloud-controller-0': 'overcloud-controller-0',
                'overcloud-controller-1': 'overcloud-controller-1',
                'overcloud-controller-2': 'overcloud-controller-2',
                'overcloud-controller-3': 'overcloud-controller-3',
                'overcloud-controller-4': 'overcloud-controller-4',
                'overcloud-controller-5': 'overcloud-controller-5'}
            },
            environment['parameter_defaults'])
        self.assertEqual({'overcloud-controller-0': 'Controller',
                          'overcloud-controller-3': 'Controller',
                          'overcloud-controller-4': 'Controller',
                          'overcloud-controller-5': 'Controller'},
                         hostname_role_map)

        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', False, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'overcloud-controller-1',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'overcloud-controller-2',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }],
            instances)
        self.assertEqual({}, environment)

    def test_unprovisioned_instances(self):
        roles = [{
            'name': 'Controller',
            'defaults': {
                'profile': 'control',
            },
            'count': 2,
            'instances': [{
                'name': 'node-0',
                'hostname': 'controller-0'
            }, {
                'name': 'node-1',
                'hostname': 'controller-1',
                'provisioned': False
            }, {
                'name': 'node-2',
                'hostname': 'controller-2',
                'provisioned': False
            }, {
                'name': 'node-3',
                'hostname': 'controller-3',
                'provisioned': True
            }]
        }]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'controller-0',
                'name': 'node-0',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'controller-3',
                'name': 'node-3',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }],
            instances)
        self.assertEqual({
            'ControllerCount': 2,
            'ControllerRemovalPolicies': [
                {'resource_list': [1, 2]}
            ],
            'ControllerHostnameFormat':
                '%stackname%-controller-%index%',
            'HostnameMap': {
                'overcloud-controller-0': 'controller-0',
                'overcloud-controller-1': 'controller-1',
                'overcloud-controller-2': 'controller-2',
                'overcloud-controller-3': 'controller-3'}
            },
            environment['parameter_defaults'])

        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', False, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'controller-1',
                'name': 'node-1',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'controller-2',
                'name': 'node-2',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }],
            instances)
        self.assertEqual({}, environment)
        self.assertEqual({'controller-1': 'Controller',
                          'controller-2': 'Controller'}, hostname_role_map)

    def test_unprovisioned_no_hostname(self):
        roles = [{
            'name': 'Controller',
            'defaults': {
                'profile': 'control',
            },
            'count': 2,
            'instances': [{
                'name': 'node-0',
            }, {
                'name': 'node-1',
                'provisioned': False
            }, {
                'name': 'node-2',
                'provisioned': False
            }, {
                'name': 'node-3',
                'provisioned': True
            }]
        }]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'node-0',
                'name': 'node-0',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'node-3',
                'name': 'node-3',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }],
            instances)
        self.assertEqual({
            'ControllerCount': 2,
            'ControllerRemovalPolicies': [
                {'resource_list': [1, 2]}
            ],
            'ControllerHostnameFormat':
                '%stackname%-controller-%index%',
            'HostnameMap': {
                'overcloud-controller-0': 'node-0',
                'overcloud-controller-1': 'node-1',
                'overcloud-controller-2': 'node-2',
                'overcloud-controller-3': 'node-3'}
            },
            environment['parameter_defaults'])
        self.assertEqual({'node-0': 'Controller', 'node-3': 'Controller'},
                         hostname_role_map)

        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', False, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'node-1',
                'name': 'node-1',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }, {
                'hostname': 'node-2',
                'name': 'node-2',
                'capabilities': {'profile': 'control'},
                'image': {'href': 'overcloud-full'},
                'config_drive': {'meta_data': {'instance-type': 'Controller'}}
            }],
            instances)
        self.assertEqual({}, environment)
        self.assertEqual({'node-1': 'Controller', 'node-2': 'Controller'},
                         hostname_role_map)

    def test_name_in_defaults(self):
        roles = [{
            'name': 'Compute',
            'count': 2,
            'defaults': {
                'profile': 'compute',
                'name': 'compute-0'
            }
        }]
        exc = self.assertRaises(
            ValueError, bd.expand,
            roles, 'overcloud', True, self.default_image
        )
        self.assertIn('Compute: cannot specify name in defaults',
                      str(exc))

    def test_hostname_in_defaults(self):
        roles = [{
            'name': 'Compute',
            'count': 2,
            'defaults': {
                'profile': 'compute',
                'hostname': 'compute-0'
            }
        }]
        exc = self.assertRaises(
            ValueError, bd.expand,
            roles, 'overcloud', True, self.default_image
        )
        self.assertIn('Compute: cannot specify hostname in defaults',
                      str(exc))

    def test_instances_without_hostname(self):
        roles = [{
            'name': 'Compute',
            'count': 2,
            'defaults': {
                'profile': 'compute'
            },
            'hostname_format': 'compute-%index%.example.com'
        }, {
            'name': 'Controller',
            'count': 2,
            'defaults': {
                'profile': 'control'
            },
            'instances': [{
                'profile': 'control-X'
                # missing hostname here
            }, {
                'name': 'node-0',
                'traits': ['CUSTOM_FOO'],
                'nics': [{'subnet': 'leaf-2'}]},
            ]},
        ]
        instances, environment, role_net_map, hostname_role_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual(
            [
                {'hostname': 'compute-0.example.com',
                 'capabilities': {'profile': 'compute'},
                 'image': {'href': 'overcloud-full'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Compute'}}},
                {'hostname': 'compute-1.example.com',
                 'capabilities': {'profile': 'compute'},
                 'image': {'href': 'overcloud-full'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Compute'}}},
                {'hostname': 'overcloud-controller-0',
                 'capabilities': {'profile': 'control-X'},
                 'image': {'href': 'overcloud-full'},
                 'config_drive': {'meta_data': {
                     'instance-type': 'Controller'}}},
                # Name provides the default for hostname
                {'name': 'node-0', 'capabilities': {'profile': 'control'},
                 'hostname': 'node-0',
                 'image': {'href': 'overcloud-full'},
                 'traits': ['CUSTOM_FOO'], 'nics': [{'subnet': 'leaf-2'}],
                 'config_drive': {'meta_data': {
                     'instance-type': 'Controller'}}},
            ],
            instances)
        self.assertEqual({'compute-0.example.com': 'Compute',
                          'compute-1.example.com': 'Compute',
                          'node-0': 'Controller',
                          'overcloud-controller-0': 'Controller'},
                         hostname_role_map)

    def test_more_instances_than_count(self):
        roles = [{
            'name': 'Compute',
            'count': 3,
            'defaults': {
                'profile': 'compute',
                'name': 'compute-0'
            },
            'instances': [{
                'name': 'node-0'
            }, {
                'name': 'node-1'
            }, {
                'name': 'node-2'
            }, {
                'name': 'node-3'
            }]
        }]
        exc = self.assertRaises(
            ValueError, bd.expand,
            roles, 'overcloud', True, self.default_image
        )
        self.assertIn('Compute: number of instance entries 4 '
                      'cannot be greater than count 3',
                      str(exc))


class TestCheckExistingInstances(base.TestCase):

    def test_success(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        baremetal.nodes.return_value = [mock.MagicMock(
            id='aaaa', instance_info={'display_name': 'host2'})]

        instances = [
            {'hostname': 'host1',
             'image': {'href': 'overcloud-full'}},
            {'hostname': 'host3',
             'image': {'href': 'overcloud-full'}},
            {'hostname': 'host2', 'resource_class': 'compute',
             'capabilities': {'answer': '42'},
             'image': {'href': 'overcloud-full'}}
        ]
        existing = mock.MagicMock(id='aaaa', hostname='host2', allocation=None)
        pr.show_instance.side_effect = [
            sdk_exc.ResourceNotFound(""),
            metalsmith.exceptions.Error(""),
            existing,
        ]
        found, not_found, unmanaged = bd.check_existing(instances, pr,
                                                        baremetal)

        self.assertEqual([existing], found)
        self.assertEqual([{
            'hostname': 'host1',
            'image': {'href': 'overcloud-full'},
        }, {
            'hostname': 'host3',
            'image': {'href': 'overcloud-full'},
        }], not_found)
        pr.show_instance.assert_has_calls([
            mock.call(host) for host in ['host1', 'host3', 'aaaa']
        ])

    def test_match_name_only(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        baremetal.nodes.return_value = [mock.MagicMock(
            id='aaaa', instance_info={})]

        instances = [
            {'hostname': 'host1',
             'image': {'href': 'overcloud-full'}},
            {'hostname': 'host3',
             'image': {'href': 'overcloud-full'}},
            {'hostname': 'host2', 'resource_class': 'compute',
             'capabilities': {'answer': '42'},
             'image': {'href': 'overcloud-full'}}
        ]
        existing = mock.MagicMock(id='aaaa', hostname='host2', allocation=None)
        pr.show_instance.side_effect = [
            sdk_exc.ResourceNotFound(""),
            metalsmith.exceptions.Error(""),
            existing,
        ]
        found, not_found, unmanaged = bd.check_existing(instances, pr,
                                                        baremetal)

        self.assertEqual([existing], found)
        self.assertEqual([{
            'hostname': 'host1',
            'image': {'href': 'overcloud-full'},
        }, {
            'hostname': 'host3',
            'image': {'href': 'overcloud-full'},
        }], not_found)
        pr.show_instance.assert_has_calls([
            mock.call(host) for host in ['host1', 'host3', 'host2']
        ])

    def test_duplicate_display_names(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        baremetal.nodes.return_value = [
            mock.MagicMock(id='aaaa', instance_info={'display_name': 'host1'}),
            mock.MagicMock(id='bbbb', instance_info={'display_name': 'host1'}),
            mock.MagicMock(id='cccc', instance_info={'display_name': 'host1'})
        ]
        instances = [
            {'hostname': 'host1',
             'image': {'href': 'overcloud-full'}},
        ]
        exc = self.assertRaises(
            bd.BaremetalDeployException, bd.check_existing,
            instances, pr, baremetal)

        self.assertIn("more than one existing instance", str(exc))
        pr.show_instance.assert_not_called()

    def test_duplicate_names(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        nodes = [
            mock.MagicMock(id='aaaa', instance_info={'display_name': 'host1'}),
            mock.MagicMock(id='bbbb', instance_info={'display_name': 'host2'}),
            mock.MagicMock(id='cccc', instance_info={'display_name': 'host3'})
        ]
        nodes[0].name = 'node1'
        nodes[1].name = 'node1'
        nodes[2].name = 'node1'
        baremetal.nodes.return_value = nodes
        instances = [
            {'hostname': 'host4',
             'name': 'node1',
             'image': {'href': 'overcloud-full'}},
        ]
        exc = self.assertRaises(
            bd.BaremetalDeployException, bd.check_existing,
            instances, pr, baremetal)

        self.assertIn("more than one existing node", str(exc))
        pr.show_instance.assert_not_called()

    def test_name_hostname_swapped(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        baremetal.nodes.return_value = [
            mock.MagicMock(id='aaaa', instance_info={'display_name': 'host3'}),
            mock.MagicMock(id='bbbb', instance_info={'display_name': 'host2'}),
            mock.MagicMock(id='cccc', instance_info={'display_name': 'host1'})
        ]

        instances = [
            {'hostname': 'host3', 'name': 'host1',
             'image': {'href': 'overcloud-full'}},
            {'hostname': 'host2', 'name': 'host2',
             'image': {'href': 'overcloud-full'}},
            {'hostname': 'host1', 'name': 'host3',
             'image': {'href': 'overcloud-full'}},
        ]
        existing = [
            mock.MagicMock(id='aaaa', hostname='host3', allocation=None),
            mock.MagicMock(id='aaaa', hostname='host2', allocation=None),
            mock.MagicMock(id='aaaa', hostname='host1', allocation=None),
        ]
        pr.show_instance.side_effect = existing
        found, not_found, unmanaged = bd.check_existing(instances, pr,
                                                        baremetal)

        self.assertEqual(existing, found)
        self.assertEqual([], not_found)
        pr.show_instance.assert_has_calls([
            mock.call(host) for host in ['aaaa', 'bbbb', 'cccc']
        ])

    def test_existing_no_allocation(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        baremetal.nodes.return_value = [mock.MagicMock(
            id='aaaa', name="server2", instance_info={'display_name': 'host2'})]
        instances = [
            {'name': 'server2', 'resource_class': 'compute',
             'hostname': 'host2',
             'capabilities': {'answer': '42'},
             'image': {'href': 'overcloud-full'}}
        ]
        existing = mock.MagicMock(
            uuid='aaaa', hostname='host2', allocation=None,
            state=metalsmith.InstanceState.ACTIVE)
        pr.show_instance.return_value = existing
        baremetal.get_allocation.side_effect = sdk_exc.ResourceNotFound

        found, not_found, unmanaged = bd.check_existing(instances, pr,
                                                        baremetal)
        baremetal.create_allocation.assert_called_once_with(
            name='host2', node='server2', resource_class='compute')

        self.assertEqual([], not_found)
        self.assertEqual([existing], found)
        pr.show_instance.assert_has_calls([mock.call('aaaa'),
                                           mock.call('aaaa')])

    def test_hostname_mismatch(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        baremetal.nodes.return_value = []
        instances = [
            {'hostname': 'host1',
             'image': {'href': 'overcloud-full'}},
        ]
        pr.show_instance.return_value.hostname = 'host2'
        exc = self.assertRaises(
            bd.BaremetalDeployException, bd.check_existing,
            instances, pr, baremetal)

        self.assertIn("hostname host1 was not found", str(exc))
        pr.show_instance.assert_called_once_with('host1')

    def test_hostname_mismatch_but_instance_info_display_name_correct(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        baremetal.nodes.return_value = [mock.MagicMock(
            id='aaaa', instance_info={'display_name': 'correct_hostname'})]
        instances = [
            {'name': 'bm_node1', 'resource_class': 'baremetal',
             'hostname': 'correct_hostname',
             'image': {'href': 'overcloud-full'}},
        ]
        existing = mock.MagicMock(
            uuid='aaaa', name='bm_node1', hostname='wrong_hostname',
            allocation=None,
            state=metalsmith.InstanceState.ACTIVE)
        pr.show_instance.return_value = existing
        baremetal.get_node.return_value.instance_info = {
            'display_name': 'correct_hostname'}
        baremetal.get_allocation.side_effect = [sdk_exc.ResourceNotFound,
                                                mock.MagicMock()]
        found, not_found, unmanaged = bd.check_existing(instances, pr,
                                                        baremetal)

        baremetal.create_allocation.assert_called_once_with(
            name='correct_hostname', node='bm_node1',
            resource_class='baremetal')

        self.assertEqual([], not_found)
        self.assertEqual([existing], found)
        self.assertEqual(2, pr.show_instance.call_count)
        pr.show_instance.assert_has_calls([mock.call('aaaa'),
                                           mock.call('aaaa')])

    def test_hostname_mismatch_and_instance_info_display_name_mismatch(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        nodes = [mock.MagicMock(
            id='aaaa', instance_info={'display_name': 'mismatching_hostname'})]
        baremetal.nodes.return_value = nodes
        nodes[0].name = 'bm_node1'
        instances = [
            {'name': 'bm_node1', 'resource_class': 'baremetal',
             'hostname': 'correct_hostname',
             'image': {'href': 'overcloud-full'}},
        ]
        existing = mock.MagicMock(
            id='aaaa', name='bm_node1', hostname='wrong_hostname',
            allocation=mock.MagicMock(),
            state=metalsmith.InstanceState.ACTIVE)
        pr.show_instance.return_value = existing
        baremetal.get_allocation.return_value = mock.MagicMock()
        baremetal.get_node.return_value.instance_info = {
            'display_name': 'mismatching_hostname'}
        exc = self.assertRaises(
            bd.BaremetalDeployException, bd.check_existing,
            instances, pr, baremetal)

        self.assertIn("hostname correct_hostname was not found", str(exc))
        pr.show_instance.assert_called_once_with('bm_node1')

    def test_check_existing_no_ironic(self):
        pr = mock.Mock()
        instances = [
            {'hostname': 'host1',
             'image': {'href': 'overcloud-full'}},
        ]
        exc = self.assertRaises(
            bd.BaremetalDeployException, bd.check_existing,
            instances, pr, None)

        self.assertIn(
            "Instance host1 is not specified as pre-provisioned", str(exc))

    def test_unexpected_error(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        baremetal.nodes.return_value = []
        instances = [
            {'image': {'href': 'overcloud-full'},
             'hostname': 'host%d' % i} for i in range(3)
        ]
        pr.show_instance.side_effect = RuntimeError('boom')
        exc = self.assertRaises(
            bd.BaremetalDeployException, bd.check_existing,
            instances, pr, baremetal)

        self.assertIn("for host0", str(exc))
        self.assertIn("RuntimeError: boom", str(exc))
        pr.show_instance.assert_called_once_with('host0')

    def test_merge_config_drive_defaults(self):

        def assertConfigDriveMerge(cd, cd_defaults, cd_instance):
            defaults = {}
            instance = {}
            if cd_defaults is not None:
                defaults['config_drive'] = cd_defaults
            if cd_instance is not None:
                instance['config_drive'] = cd_instance

            bd.merge_config_drive_defaults(defaults, instance)

            if cd is None:
                self.assertNotIn(instance, 'config_drive')
            self.assertEqual(cd, instance.get('config_drive'))

        # assert no config_drive key when nothing to merge
        assertConfigDriveMerge(None, None, None)
        assertConfigDriveMerge(None, {}, None)
        assertConfigDriveMerge({}, None, {})
        assertConfigDriveMerge({}, {}, {})

        # assert what expand does internally when no config_drive is specified
        assertConfigDriveMerge(
            {'meta_data': {'instance-type': 'Compute'}},
            {'meta_data': {'instance-type': 'Compute'}},
            None
        )

        # assert various combinations of defaults and instance to show that
        # merge works and instance has precedence over defaults
        assertConfigDriveMerge(
            {'meta_data': {'one': 1, 'two': 22, 'three': 3, 'four': 44}},
            {'meta_data': {'one': 1, 'two': 2, 'three': 3}},
            {'meta_data': {'two': 22, 'four': 44}},
        )
        assertConfigDriveMerge(
            {'cloud_config': {'one': 1, 'two': 22, 'three': 3, 'four': 44}},
            {'cloud_config': {'one': 1, 'two': 2, 'three': 3}},
            {'cloud_config': {'two': 22, 'four': 44}},
        )
