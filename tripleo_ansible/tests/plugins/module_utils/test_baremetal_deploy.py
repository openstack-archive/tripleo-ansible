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


class TestExpandRoles(base.TestCase):

    default_image = {'href': 'overcloud-full'}

    def test_simple(self):
        roles = [
            {'name': 'Compute'},
            {'name': 'Controller'},
        ]
        instances, environment = bd.expand(
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
                'ComputeDeployedServerHostnameFormat':
                '%stackname%-novacompute-%index%',
                'ComputeDeployedServerCount': 1,
                'ControllerDeployedServerHostnameFormat':
                '%stackname%-controller-%index%',
                'ControllerDeployedServerCount': 1,
                'HostnameMap': {
                    'overcloud-novacompute-0': 'overcloud-novacompute-0',
                    'overcloud-controller-0': 'overcloud-controller-0'
                }
            },
            environment['parameter_defaults'])

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
        instances, environment = bd.expand(
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
        instances, environment = bd.expand(
            roles, 'overcloud', True, self.default_image
        )
        self.assertEqual(
            [
                {'hostname': 'compute-0.example.com', 'profile': 'compute',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'compute-1.example.com', 'profile': 'compute',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'controller-0.example.com', 'profile': 'control',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'controller-1.example.com', 'profile': 'control',
                 'image': {'href': 'overcloud-full'}},
                {'hostname': 'controller-2.example.com', 'profile': 'control',
                 'image': {'href': 'overcloud-full'}},
            ],
            instances)
        self.assertEqual(
            {
                'ComputeDeployedServerHostnameFormat':
                'compute-%index%.example.com',
                'ComputeDeployedServerCount': 2,
                'ControllerDeployedServerHostnameFormat':
                'controller-%index%.example.com',
                'ControllerDeployedServerCount': 3,
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
                'profile': 'control'
            },
            'instances': [{
                'hostname': 'controller-X.example.com',
                'profile': 'control-X'
            }, {
                'name': 'node-0',
                'traits': ['CUSTOM_FOO'],
                'nics': [{'subnet': 'leaf-2'}]},
            ]},
        ]
        instances, environment = bd.expand(
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
                 'profile': 'control-X'},
                # Name provides the default for hostname later on.
                {'name': 'node-0', 'profile': 'control',
                 'hostname': 'node-0',
                 'image': {'href': 'overcloud-full'},
                 'traits': ['CUSTOM_FOO'], 'nics': [{'subnet': 'leaf-2'}]},
            ],
            instances)
        self.assertEqual(
            {
                'ComputeDeployedServerHostnameFormat':
                'compute-%index%.example.com',
                'ComputeDeployedServerCount': 2,
                'ControllerDeployedServerHostnameFormat':
                '%stackname%-controller-%index%',
                'ControllerDeployedServerCount': 2,
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
        instances, environment = bd.expand(
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
            'ComputeDeployedServerCount': 2,
            'ComputeDeployedServerHostnameFormat':
                'compute-%index%.example.com',
            'ControllerDeployedServerCount': 3,
            'ControllerDeployedServerHostnameFormat':
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
        instances, environment = bd.expand(
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
            'ControllerDeployedServerCount': 2,
            'ControllerRemovalPolicies': [
                {'resource_list': [1, 2]}
            ],
            'ControllerDeployedServerHostnameFormat':
                '%stackname%-controller-%index%',
            'HostnameMap': {
                'overcloud-controller-0': 'overcloud-controller-0',
                'overcloud-controller-1': 'overcloud-controller-1',
                'overcloud-controller-2': 'overcloud-controller-2',
                'overcloud-controller-3': 'overcloud-controller-3'}
            },
            environment['parameter_defaults'])

        instances, environment = bd.expand(
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
        instances, environment = bd.expand(
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
            'ControllerDeployedServerCount': 4,
            'ControllerRemovalPolicies': [
                {'resource_list': [1, 2]}
            ],
            'ControllerDeployedServerHostnameFormat':
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

        instances, environment = bd.expand(
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
        instances, environment = bd.expand(
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
            'ControllerDeployedServerCount': 2,
            'ControllerRemovalPolicies': [
                {'resource_list': [1, 2]}
            ],
            'ControllerDeployedServerHostnameFormat':
                '%stackname%-controller-%index%',
            'HostnameMap': {
                'overcloud-controller-0': 'controller-0',
                'overcloud-controller-1': 'controller-1',
                'overcloud-controller-2': 'controller-2',
                'overcloud-controller-3': 'controller-3'}
            },
            environment['parameter_defaults'])

        instances, environment = bd.expand(
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
        instances, environment = bd.expand(
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
            'ControllerDeployedServerCount': 2,
            'ControllerRemovalPolicies': [
                {'resource_list': [1, 2]}
            ],
            'ControllerDeployedServerHostnameFormat':
                '%stackname%-controller-%index%',
            'HostnameMap': {
                'overcloud-controller-0': 'node-0',
                'overcloud-controller-1': 'node-1',
                'overcloud-controller-2': 'node-2',
                'overcloud-controller-3': 'node-3'}
            },
            environment['parameter_defaults'])

        instances, environment = bd.expand(
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
        instances, environment = bd.expand(
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
