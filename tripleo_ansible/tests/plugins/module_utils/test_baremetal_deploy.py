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


# load baremetal_deploy so the next import works
base.load_module_utils('baremetal_deploy')

from ansible.module_utils import baremetal_deploy as bd  # noqa


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


class TestExpandRoles(base.TestCase):

    default_image = {'href': 'overcloud-full'}
    default_network = [{'network': 'ctlplane', 'vif': True}]

    def test_simple(self):
        roles = [
            {'name': 'Compute'},
            {'name': 'Controller'},
        ]
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )

        self.assertEqual(
            [
                {'hostname': 'overcloud-novacompute-0',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'}},
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

    def test_default_network(self):
        roles = [
            {'name': 'Compute'},
            {'name': 'Controller'},
        ]
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image, self.default_network
        )
        self.assertEqual(
            [
                {'hostname': 'overcloud-novacompute-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'ctlplane', 'vif': True}],
                 'nics': [{'network': 'ctlplane'}]},
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'ctlplane', 'vif': True}],
                 'nics': [{'network': 'ctlplane'}]},
            ],
            instances)

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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image, None
        )
        self.assertEqual(
            [
                {'hostname': 'overcloud-novacompute-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'some_net', 'vif': True}],
                 'nics': [{'network': 'some_net'}]},
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'some_net', 'vif': True}],
                 'nics': [{'network': 'some_net'}]},
            ],
            instances)

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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image, self.default_network
        )
        self.assertEqual(
            [
                {'hostname': 'overcloud-novacompute-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'foo', 'subnet': 'foo_subnet'},
                              {'network': 'ctlplane', 'vif': True}],
                 'nics': [{'network': 'ctlplane'}]},
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'},
                 'networks': [{'network': 'foo', 'subnet': 'foo_subnet'},
                              {'network': 'ctlplane', 'vif': True}],
                 'nics': [{'network': 'ctlplane'}]},
            ],
            instances)

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
        instances, environment, role_net_map = bd.expand(
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
                 ]},
            ],
            instances)

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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual(
            [
                {'hostname': 'overcloud-controller-0',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'overcloud-controller-1',
                 'image': {'href': 'file:///tmp/foo.qcow2',
                           'checksum': '12345678'}},
                {'hostname': 'overcloud-controller-2',
                 'image': {'href': 'file:///tmp/foo.qcow2',
                           'checksum': '12345678'}},
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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image,
            user_name='heat-admin', ssh_public_keys='aaaa'
        )
        self.assertEqual(
            [
                {'hostname': 'compute-0.example.com', 'profile': 'compute',
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin'},
                {'hostname': 'compute-1.example.com', 'profile': 'compute',
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin'},
                {'hostname': 'controller-0.example.com', 'profile': 'control',
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin'},
                {'hostname': 'controller-1.example.com', 'profile': 'control',
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin'},
                {'hostname': 'controller-2.example.com', 'profile': 'control',
                 'image': {'href': 'overcloud-full'},
                 'ssh_public_keys': 'aaaa',
                 'user_name': 'heat-admin'},
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
                ]
            }, {
                'name': 'node-0',
                'traits': ['CUSTOM_FOO'],
                'networks': [{'network': 'some_net', 'subnet': 'leaf-2',
                              'vif': True}]},
            ]},
        ]
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual(
            [
                {'hostname': 'compute-0.example.com', 'profile': 'compute',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'compute-1.example.com', 'profile': 'compute',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'controller-X.example.com',
                 'image': {'href': 'overcloud-full'},
                 'profile': 'control-X',
                 'networks': [{'fixed_ip': '10.1.1.1', 'network': 'inst_net'},
                              {'network': 'foo', 'subnet': 'foo_subnet'}],
                 },
                # Name provides the default for hostname later on.
                {'name': 'node-0', 'profile': 'control',
                 'hostname': 'node-0',
                 'networks': [
                     {'network': 'some_net', 'subnet': 'leaf-2', 'vif': True},
                     {'network': 'foo', 'subnet': 'foo_subnet'},
                 ],
                 'image': {'href': 'overcloud-full'},
                 'traits': ['CUSTOM_FOO'],
                 'nics': [{'network': 'some_net', 'subnet': 'leaf-2'}]},
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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'compute-0.example.com',
                'profile': 'compute',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'compute-1.example.com',
                'profile': 'compute',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'controller-X.example.com',
                'profile': 'control-X',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'node-0',
                'name': 'node-0',
                'nics': [{'subnet': 'leaf-2'}],
                'profile': 'control',
                'traits': ['CUSTOM_FOO'],
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'overcloud-controller-2',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'overcloud-controller-0',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'overcloud-controller-3',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
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

        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', False, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'overcloud-controller-1',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'overcloud-controller-2',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }],
            instances)
        self.assertEqual({}, environment)

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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'overcloud-controller-0',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'overcloud-controller-3',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'overcloud-controller-4',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'overcloud-controller-5',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
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

        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', False, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'overcloud-controller-1',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'overcloud-controller-2',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'controller-0',
                'name': 'node-0',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'controller-3',
                'name': 'node-3',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
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

        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', False, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'controller-1',
                'name': 'node-1',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'controller-2',
                'name': 'node-2',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }],
            instances)
        self.assertEqual({}, environment)

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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'node-0',
                'name': 'node-0',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'node-3',
                'name': 'node-3',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
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

        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', False, self.default_image
        )
        self.assertEqual([
            {
                'hostname': 'node-1',
                'name': 'node-1',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }, {
                'hostname': 'node-2',
                'name': 'node-2',
                'profile': 'control',
                'image': {'href': 'overcloud-full'}
            }],
            instances)
        self.assertEqual({}, environment)

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
        instances, environment, role_net_map = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual(
            [
                {'hostname': 'compute-0.example.com', 'profile': 'compute',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'compute-1.example.com', 'profile': 'compute',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'overcloud-controller-0', 'profile': 'control-X',
                 'image': {'href': 'overcloud-full'}},
                # Name provides the default for hostname
                {'name': 'node-0', 'profile': 'control',
                 'hostname': 'node-0',
                 'image': {'href': 'overcloud-full'},
                 'traits': ['CUSTOM_FOO'], 'nics': [{'subnet': 'leaf-2'}]},
            ],
            instances)

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
        instances = [
            {'hostname': 'host1',
             'image': {'href': 'overcloud-full'}},
            {'hostname': 'host3',
             'image': {'href': 'overcloud-full'}},
            {'hostname': 'host2', 'resource_class': 'compute',
             'capabilities': {'answer': '42'},
             'image': {'href': 'overcloud-full'}}
        ]
        existing = mock.MagicMock(hostname='host2', allocation=None)
        existing.uuid = 'aaaa'
        pr.show_instance.side_effect = [
            sdk_exc.ResourceNotFound(""),
            metalsmith.exceptions.Error(""),
            existing,
        ]
        found, not_found = bd.check_existing(instances, pr, baremetal)

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

    def test_existing_no_allocation(self):
        pr = mock.Mock()
        baremetal = mock.Mock()
        instances = [
            {'name': 'server2', 'resource_class': 'compute',
             'hostname': 'host2',
             'capabilities': {'answer': '42'},
             'image': {'href': 'overcloud-full'}}
        ]
        existing = mock.MagicMock(
            hostname='host2', allocation=None,
            state=metalsmith.InstanceState.ACTIVE)
        existing.uuid = 'aaaa'
        pr.show_instance.return_value = existing

        found, not_found = bd.check_existing(instances, pr, baremetal)
        baremetal.create_allocation.assert_called_once_with(
            name='host2', node='server2', resource_class='compute')

        self.assertEqual([], not_found)
        self.assertEqual([existing], found)
        pr.show_instance.assert_called_once_with('server2')

    def test_hostname_mismatch(self):
        pr = mock.Mock()
        instances = [
            {'hostname': 'host1',
             'image': {'href': 'overcloud-full'}},
        ]
        pr.show_instance.return_value.hostname = 'host2'
        exc = self.assertRaises(
            bd.BaremetalDeployException, bd.check_existing,
            instances, pr, mock.Mock())

        self.assertIn("hostname host1 was not found", str(exc))
        pr.show_instance.assert_called_once_with('host1')

    def test_unexpected_error(self):
        pr = mock.Mock()
        instances = [
            {'image': {'href': 'overcloud-full'},
             'hostname': 'host%d' % i} for i in range(3)
        ]
        pr.show_instance.side_effect = RuntimeError('boom')
        exc = self.assertRaises(
            bd.BaremetalDeployException, bd.check_existing,
            instances, pr, mock.Mock())

        self.assertIn("for host0", str(exc))
        self.assertIn("RuntimeError: boom", str(exc))
        pr.show_instance.assert_called_once_with('host0')
