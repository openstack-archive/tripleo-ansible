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

import mock

from tripleo_ansible.ansible_plugins.modules import (
    os_tripleo_baremetal_node_introspection as module)
from tripleo_ansible.tests import base as tests_base


class TestIntrospect(tests_base.TestCase):

    def setUp(self):
        super(TestIntrospect, self).setUp()
        c = mock.Mock()
        self.cloud = c
        self.node = mock.Mock(
            uuid='1234abcd',
            power_state='power on',
            provision_state='manageable',
            last_error=None,
        )
        c.baremetal.get_node.return_value = self.node
        c.baremetal.set_node_provision_state.return_value = self.node
        c.baremetal.wait_for_node_reservation.return_value = self.node
        c.baremetal_introspection.get_introspection_data.return_value = {
            'foo': 'bar'
        }

    @mock.patch.object(module, 'prepare_for_attempt')
    def test_introspect_node(self, mock_pfa):
        mock_pfa.return_value = self.node
        c = self.cloud

        result = module.introspect_node(
            c, '1234abcd', 1200, 120, 3, True)
        self.assertEqual({
            'status': {'foo': 'bar'},
            'failed': False,
            'error': None},
        result)

        mock_pfa.assert_called_once_with(c, self.node, 1200, 120)
        c.baremetal.set_node_provision_state.assert_called_once_with(
            self.node, 'inspect', wait=True, timeout=1200
        )
        c.baremetal.set_node_power_state.assert_called_once_with(
            self.node, 'power off', wait=True, timeout=1200
        )
        c.baremetal_introspection.get_introspection_data.assert_called_once_with(
            '1234abcd'
        )

    @mock.patch.object(module, 'prepare_for_attempt')
    def test_introspect_node_retries(self, mock_pfa):
        mock_pfa.return_value = self.node
        c = self.cloud
        ouch = Exception('ouch')
        c.baremetal.set_node_provision_state.side_effect = [
            ouch,
            ouch,
            ouch,
            self.node
        ]

        result = module.introspect_node(
            c, '1234abcd', 1200, 120, 3, fetch_data=False)
        self.assertEqual({
            'status': '',
            'failed': False,
            'error': None},
        result)

        mock_pfa.assert_has_calls([
            mock.call(c, self.node, 1200, 120),
            mock.call(c, self.node, 1200, 120),
            mock.call(c, self.node, 1200, 120),
            mock.call(c, self.node, 1200, 120)
        ])
        c.baremetal.set_node_provision_state.assert_has_calls([
            mock.call(self.node, 'inspect', wait=True, timeout=1200),
            mock.call(self.node, 'inspect', wait=True, timeout=1200),
            mock.call(self.node, 'inspect', wait=True, timeout=1200),
            mock.call(self.node, 'inspect', wait=True, timeout=1200),
        ])
        c.baremetal.set_node_power_state.assert_called_once_with(
            self.node, 'power off', wait=True, timeout=1200
        )
        # fetch_data is False
        c.baremetal_introspection.get_introspection_data.assert_not_called()

    @mock.patch.object(module, 'prepare_for_attempt')
    def test_introspect_node_retries_failed(self, mock_pfa):
        mock_pfa.return_value = self.node
        c = self.cloud
        ouch = Exception('ouch')
        c.baremetal.set_node_provision_state.side_effect = [
            ouch,
            ouch,
            ouch,
            ouch,
        ]

        result = module.introspect_node(
            c, '1234abcd', 1200, 120, 3, True)
        self.assertEqual({
            'error': 'Error for introspection node 1234abcd on attempt 4: None ',
            'failed': True,
            'status': 'manageable'}, result)

        mock_pfa.assert_has_calls([
            mock.call(c, self.node, 1200, 120),
            mock.call(c, self.node, 1200, 120),
            mock.call(c, self.node, 1200, 120),
            mock.call(c, self.node, 1200, 120),
        ])
        c.baremetal.set_node_provision_state.assert_has_calls([
            mock.call(self.node, 'inspect', wait=True, timeout=1200),
            mock.call(self.node, 'inspect', wait=True, timeout=1200),
            mock.call(self.node, 'inspect', wait=True, timeout=1200),
            mock.call(self.node, 'inspect', wait=True, timeout=1200),
        ])
        c.baremetal.set_node_power_state.assert_not_called()
        c.baremetal_introspection.get_introspection_data.assert_not_called()

    def test_prepare_for_attempt_noop(self):
        c = self.cloud
        self.node.provision_state = 'manageable'
        self.node.power_state = 'power off'
        self.node.reservation = None

        node = module.prepare_for_attempt(c, self.node, 1200, 120)

        self.assertEqual(node, self.node)
        c.baremetal.set_node_provision_state.assert_not_called()
        c.baremetal.set_node_power_state.assert_not_called()
        c.baremetal.wait_for_node_reservation.assert_not_called()

    def test_prepare_for_attempt_not_manageable(self):
        c = self.cloud
        self.node.provision_state = 'inspect wait'
        self.node.power_state = 'power off'
        self.node.reservation = None

        node = module.prepare_for_attempt(c, self.node, 1200, 120)

        self.assertEqual(node, self.node)
        c.baremetal.set_node_provision_state.assert_called_once_with(
            self.node, 'abort', wait=True, timeout=1200
        )
        c.baremetal.set_node_power_state.assert_not_called()
        c.baremetal.wait_for_node_reservation.assert_not_called()

    def test_prepare_for_attempt_powered_on(self):
        c = self.cloud
        self.node.provision_state = 'manageable'
        self.node.power_state = 'power on'
        self.node.reservation = None

        node = module.prepare_for_attempt(c, self.node, 1200, 120)

        self.assertEqual(node, self.node)
        c.baremetal.set_node_provision_state.assert_not_called()
        c.baremetal.set_node_power_state.assert_called_once_with(
            self.node, 'power off', wait=True, timeout=1200
        )
        c.baremetal.wait_for_node_reservation.assert_not_called()

    def test_prepare_for_attempt_reserved(self):
        c = self.cloud
        self.node.provision_state = 'manageable'
        self.node.power_state = 'power off'
        self.node.reservation = 'conductor1'

        node = module.prepare_for_attempt(c, self.node, 1200, 120)

        self.assertEqual(node, self.node)
        c.baremetal.set_node_provision_state.assert_not_called()
        c.baremetal.set_node_power_state.assert_not_called()
        c.baremetal.wait_for_node_reservation.assert_called_once_with(
            self.node, timeout=120
        )

    def test_prepare_for_attempt_everything_failed(self):
        c = self.cloud
        ouch = Exception('ouch')
        c.baremetal.set_node_provision_state.side_effect = ouch
        c.baremetal.set_node_power_state.side_effect = ouch
        c.baremetal.wait_for_node_reservation.side_effect = ouch

        self.node.provision_state = 'inspect wait'
        self.node.power_state = 'power on'
        self.node.reservation = 'conductor1'

        node = module.prepare_for_attempt(c, self.node, 1200, 120)

        self.assertEqual(node, self.node)
        c.baremetal.set_node_provision_state.assert_called_once_with(
            self.node, 'abort', wait=True, timeout=1200
        )
        c.baremetal.set_node_power_state.assert_called_once_with(
            self.node, 'power off', wait=True, timeout=1200
        )
        c.baremetal.wait_for_node_reservation.assert_called_once_with(
            self.node, timeout=120
        )
