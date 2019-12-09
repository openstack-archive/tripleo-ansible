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

from collections import Counter
from unittest import mock

from tripleo_ansible.ansible_plugins.modules import lvm2_physical_devices_facts as lvm2
from tripleo_ansible.tests import base as tests_base


class TestLvm2PhysicalDevicesFacts(tests_base.TestCase):

    def test_get_pvs(self):
        mock_module = mock.Mock()

        mock_module.run_command.return_value = (0, ' myvgname\n myvgname\n', '')
        result = lvm2.get_vgs_with_active_lvs(mock_module)
        self.assertEqual(['myvgname'], result)

        mock_module.run_command.return_value = (0, ' /dev/sdb1\n /dev/sdb2\n', '')
        result = lvm2.get_vgs_with_active_lvs(mock_module)
        self.assertEqual(Counter(['/dev/sdb1', '/dev/sdb2']), Counter(result))
