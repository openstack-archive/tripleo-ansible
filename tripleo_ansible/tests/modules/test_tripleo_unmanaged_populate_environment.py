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

import copy

from tripleo_ansible.ansible_plugins.modules import (
    tripleo_unmanaged_populate_environment as plugin)
from tripleo_ansible.tests import base as tests_base


FAKE_INSTANCES = [
    {'hostname': 'instance1',
     'managed': False,
     'networks': [{'network': 'ctlplane', 'fixed_ip': '1.1.1.1'}]},
    {'hostname': 'instance2',
     'managed': False,
     'networks': [{'network': 'ctlplane', 'fixed_ip': '1.1.1.2'}]},
    {'hostname': 'instance3',
     'networks': [{'network': 'ctlplane', 'vif': True}]},
]

FAKE_ENVIRONMENT = {
    'parameter_defaults': {
        'FooParam': 'foo',
        'DeployedServerPortMap': {
            'instance3-ctlplane': {
                'fixed_ips': [{'ip_address': '1.1.1.3'}]
            }
        }
    },
    'resource_registry': {
        'OS::Fake::Resource': '/path/to/fake/resource.yaml'
    },
}

FAKE_NODE_PORT_MAP = {
    'instance1': {
        'ctlplane': {'ip_address': '1.1.1.1'}
    },
    'instance2': {
        'ctlplane': {'ip_address': '1.1.1.2'}
    },
    'instance3': {
        'ctlplane': {'ip_address': '1.1.1.3'}
    },
}


class TestTripleoOvercloudNetworkPorts(tests_base.TestCase):

    def test_update_environment(self):
        env = copy.deepcopy(FAKE_ENVIRONMENT)
        plugin.update_environment(env, 'ctlplane', FAKE_NODE_PORT_MAP,
                                  FAKE_INSTANCES)
        expected = copy.deepcopy(FAKE_ENVIRONMENT)
        expected['parameter_defaults']['DeployedServerPortMap'].update(
            {'instance1-ctlplane': {'fixed_ips': [{'ip_address': '1.1.1.1'}]},
             'instance2-ctlplane': {'fixed_ips': [{'ip_address': '1.1.1.2'}]},
             }
        )
        self.assertEqual(expected, env)
