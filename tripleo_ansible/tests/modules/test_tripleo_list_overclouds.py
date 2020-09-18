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

from unittest import mock

from heatclient import exc as heat_exc

from tripleo_ansible.ansible_plugins.modules import tripleo_list_overclouds as tlo
from tripleo_ansible.tests import base as tests_base


class TestTripleoListOveclouds(tests_base.TestCase):

    def test_get_overclouds(self):
        mock_heat = mock.Mock()
        mock_stacks = mock.Mock()
        mock_heat.stacks = mock_stacks

        mock_stacks.list.return_value = [
            mock.Mock(id='111', stack_name='overcloud'),
            mock.Mock(id='222', stack_name='some-other-stack'),
            mock.Mock(id='333', stack_name='other-overcloud'),
        ]

        output_result = {"output": {
            "output_key": "AnsibleHostVarsMap",
            "output_value": {}
        }}
        mock_stacks.output_show.side_effect = [
            output_result,
            heat_exc.NotFound(),
            output_result
        ]
        result = list(tlo.get_overclouds(mock_heat))
        self.assertEqual([{
            'id': '111',
            'stack_name': 'overcloud'
        }, {
            'id': '333',
            'stack_name': 'other-overcloud'
        }], result)
