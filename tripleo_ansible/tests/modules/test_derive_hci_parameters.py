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
"""Test the derive and get_vcpus_per_osd methods of the HCI module"""

import yaml

from tripleo_ansible.ansible_plugins.modules import tripleo_derive_hci_parameters as derive_params
from tripleo_ansible.tests import base as tests_base


class TestTripleoDeriveHciParameters(tests_base.TestCase):
    """Test the derive method of the HCI module"""

    def test_derive_positive(self):
        """Test the derive method with valid input and confirm expected result
        """
        der = derive_params.derive(mem_gb=256, vcpus=4, osds=1,
                                   average_guest_memory_size_in_mb=2048,
                                   average_guest_cpu_utilization_percentage=20)
        self.assertFalse(der['failed'])
        self.assertEqual(der['nova_reserved_mem_mb'], 56320)
        self.assertEqual(der['cpu_allocation_ratio'], 3.75)

    def test_derive_negative(self):
        """Test the derive method with invalid input
        """
        der = derive_params.derive(mem_gb=2, vcpus=1, osds=1,
                                   average_guest_memory_size_in_mb=0,
                                   average_guest_cpu_utilization_percentage=0)
        self.assertTrue(der['failed'])

    def test_vcpu_ratio(self):
        """Test the get_vcpus_per_osd method and confirm expected result
        """

        def mock_ironic():
            """Return a dictionary with partial disks section of introspection
            """
            return {'data':
                    {'inventory':
                     {'disks':
                      [
                      {'by_path': '/dev/disk/by-path/pci-0000:00:07.0-scsi-0:0:0:5',
                       'name': '/dev/sda',
                       'rotational': True,
                       'wwn': None},
                      {'by_path': '/dev/disk/by-path/pci-0000:00:07.0-scsi-0:0:0:4',
                       'name': '/dev/sdb',
                       'rotational': True,
                       'wwn': None},
                      {'by_path': '/dev/disk/by-path/pci-0000:00:07.0-scsi-0:0:0:3',
                       'name': '/dev/sdc',
                       'rotational': True,
                       'wwn': None},
                      {'by_path': '/dev/disk/by-path/pci-0000:00:07.0-scsi-0:0:0:2',
                       'name': '/dev/sdd',
                       'rotational': True,
                       'wwn': None},
                      {'by_path': '/dev/disk/by-path/pci-0000:00:01.1-ata-1',
                       'name': '/dev/sde',
                       'rotational': True,
                       'wwn': None}
                      ]
                      }
                     }
                    }

        def get_ironic(flavor='hdd'):
            """Returns a dictionary which mocks ironic introspection
            data. Uses mock introspection data as the source but then
            applies flavor variations to make it look like the system
            which was introspected has SSD or NVMe SSDs.
            """
            ironic = mock_ironic()
            if flavor in 'ssd':
                for dev in ironic['data']['inventory']['disks']:
                    dev['rotational'] = False
            if flavor in 'nvme':
                i = 1
                for dev in ironic['data']['inventory']['disks']:
                    nvm_name = "/dev/nvme0n%i" % i
                    dev['name'] = nvm_name
                    dev['rotational'] = False
                    i += 1
            return ironic

        def get_env(flavor='hdd', osds_per_device=1):
            """Returns a dictionary which mocks the content of the
            tripleo_environment_parameters CephAnsibleDisksConfig
            where the deployer requests four OSDs using device
            list within ceph-ansible of differing flavor types.
            The flavor may be set to one of hdd, ssd, by_path,
            or nvme and it is also possible to set the
            osds_per_device (usually used with NVMe). Uses mock
            introspection data in molecule to build the device
            list with flavor variations.
            """
            ironic = mock_ironic()
            devices = []
            i = 1
            for dev in ironic['data']['inventory']['disks']:
                if flavor in ('hdd', 'ssd'):
                    devices.append(dev['name'])
                elif flavor in 'by_path':
                    devices.append(dev['by_path'])
                elif flavor in 'nvme':
                    nvm_name = "/dev/nvme0n%i" % i
                    devices.append(nvm_name)
                i += 1
                if i > 4:
                    break
            disks_config = {
                "osd_objectstore": "bluestore",
                "osd_scenario": "lvm",
                "devices": devices
                }
            if osds_per_device > 1:
                disks_config['osds_per_device'] = osds_per_device
            env = {
                "CephAnsibleDisksConfig": disks_config
            }
            return env

        ratio_map = {
            'hdd': 1,
            'ssd': 4,
            'by_path': 1,
            'nvme': 3
            }
        for flavor in ratio_map:
            if flavor == 'nvme':
                osds_per_device = 4
            else:
                osds_per_device = 0
            env = get_env(flavor, osds_per_device)
            ironic = get_ironic(flavor)
            num_osds = len(env['CephAnsibleDisksConfig']['devices'])
            vcpu_ratio, vcpu_msg = derive_params.get_vcpus_per_osd(ironic,
                                                                   env,
                                                                   num_osds)
            self.assertEqual(vcpu_ratio, ratio_map[flavor])
            self.assertIsNotNone(vcpu_msg)

    def test_derive_without_workload(self):
        """Test the derive method without passing the expected average
        guest cpu and mem utilization and confirm expected result
        """
        der = derive_params.derive(mem_gb=256, vcpus=56, osds=16)
        self.assertFalse(der['failed'])
        self.assertEqual(der['nova_reserved_mem_mb'], 81920)

    def test_count_memory(self):
        """Test that the count_memory method can the right number
        regardless of which value ironic might provide.
        """
        mock_ironic_memory_mb = {'data':
                                 {'memory_mb': 262144}}
        mock_ironic_memory_bytes = {'data':
                                    {'memory_mb': 0,
                                     'inventory':
                                     {'memory':
                                      {'total': 274877906944}}}}
        gb_from_mb = derive_params.count_memory(mock_ironic_memory_mb)
        gb_from_bytes = derive_params.count_memory(mock_ironic_memory_bytes)
        self.assertEqual(gb_from_mb, gb_from_bytes)
