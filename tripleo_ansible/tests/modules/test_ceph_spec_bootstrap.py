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
"""Test the methods of the ceph_spec_bootstrap module"""

import io
import socket
import tempfile
import yaml

try:
    from ansible.module_utils import tripleo_inventory_manager
except ImportError:
    from tripleo_ansible.ansible_plugins.module_utils import tripleo_inventory_manager
from tripleo_ansible.ansible_plugins.modules import ceph_spec_bootstrap
from tripleo_ansible.tests import base as tests_base


class TestCephSpecBootstrap(tests_base.TestCase):
    """Test the methods of the ceph_spec_bootstrap module"""

    def test_metal_roles_based_spec(self):
        """verify we can build a ceph spec and supporting data
           structures from a metalsmith and tripleo roles file
        """
        ceph_service_types = ['mon', 'mgr', 'osd']
        metal = "roles/tripleo_cephadm/molecule/default/mock/mock_deployed_metal.yaml"
        tripleo_roles = "roles/tripleo_cephadm/molecule/default/mock/mock_overcloud_roles.yaml"
        tld = ""
        roles_to_svcs = ceph_spec_bootstrap.get_roles_to_svcs_from_roles(tripleo_roles)
        expected = {
            'Compute': [],
            'CephStorage': ['CephOSD'],
            'Controller': ['CephMgr', 'CephMon']}
        self.assertEqual(roles_to_svcs, expected)

        roles = roles_to_svcs.keys()
        roles_to_hosts = ceph_spec_bootstrap.get_deployed_roles_to_hosts(metal, roles, tld)
        expected = {
            'Controller': ['oc0-controller-0', 'oc0-controller-1', 'oc0-controller-2'],
            'Compute': ['oc0-compute-0'],
            'CephStorage': ['oc0-ceph-0', 'oc0-ceph-1', 'oc0-ceph-2']
        }
        self.assertEqual(roles_to_hosts, expected)

        hosts_to_ips = ceph_spec_bootstrap.get_deployed_hosts_to_ips(metal, tld)
        expected = {'oc0-ceph-0': '192.168.24.13',
                    'oc0-ceph-1': '192.168.24.11',
                    'oc0-ceph-2': '192.168.24.14',
                    'oc0-compute-0': '192.168.24.21',
                    'oc0-controller-0': '192.168.24.23',
                    'oc0-controller-1': '192.168.24.15',
                    'oc0-controller-2': '192.168.24.7'}
        self.assertEqual(hosts_to_ips, expected)

        label_map = ceph_spec_bootstrap.get_label_map(hosts_to_ips, roles_to_svcs,
                                                      roles_to_hosts, ceph_service_types)
        expected = {'oc0-ceph-0': ['osd'],
                    'oc0-ceph-1': ['osd'],
                    'oc0-ceph-2': ['osd'],
                    'oc0-compute-0': [],
                    'oc0-controller-0': ['mgr', 'mon', '_admin'],
                    'oc0-controller-1': ['mgr', 'mon', '_admin'],
                    'oc0-controller-2': ['mgr', 'mon', '_admin']}
        self.assertEqual(label_map, expected)

        specs = ceph_spec_bootstrap.get_specs(hosts_to_ips, label_map, ceph_service_types)
        expected = [
            {'service_type': 'host', 'addr': '192.168.24.13',
             'hostname': 'oc0-ceph-0', 'labels': ['osd']},
            {'service_type': 'host', 'addr': '192.168.24.11',
             'hostname': 'oc0-ceph-1', 'labels': ['osd']},
            {'service_type': 'host', 'addr': '192.168.24.14',
             'hostname': 'oc0-ceph-2', 'labels': ['osd']},
            {'service_type': 'host', 'addr': '192.168.24.23',
             'hostname': 'oc0-controller-0', 'labels': ['mgr', 'mon', '_admin']},
            {'service_type': 'host', 'addr': '192.168.24.15',
             'hostname': 'oc0-controller-1', 'labels': ['mgr', 'mon', '_admin']},
            {'service_type': 'host', 'addr': '192.168.24.7',
             'hostname': 'oc0-controller-2', 'labels': ['mgr', 'mon', '_admin']},
            {
                'service_type': 'mon',
                'service_name': 'mon',
                'service_id': 'mon',
                'placement': {
                    'hosts': ['oc0-controller-0', 'oc0-controller-1', 'oc0-controller-2']
                }
            },
            {
                'service_type': 'mgr',
                'service_name': 'mgr',
                'service_id': 'mgr',
                'placement': {
                    'hosts': ['oc0-controller-0', 'oc0-controller-1', 'oc0-controller-2']
                }
            },
            {
                'service_type': 'osd',
                'service_name': 'osd.default_drive_group',
                'service_id': 'default_drive_group',
                'placement': {
                    'hosts': ['oc0-ceph-0', 'oc0-ceph-1', 'oc0-ceph-2']
                },
                'data_devices': {'all': True}
            }
        ]
        for index in range(0, len(expected)):
            if expected[index].get('service_type', '') == 'host':
                expected[index].get('labels', {}).sort()
                specs[index].get('labels', {}).sort()

        self.assertEqual(specs, expected)

    def test_metal_roles_based_spec_with_tld(self):
        """verify we can build a ceph spec with tld and supporting data
           structures from a metalsmith and tripleo roles file
        """
        ceph_service_types = ['mon', 'mgr', 'osd']
        metal = "roles/tripleo_cephadm/molecule/default/mock/mock_deployed_metal.yaml"
        tripleo_roles = "roles/tripleo_cephadm/molecule/default/mock/mock_overcloud_roles.yaml"
        tld = "abc.local"
        roles_to_svcs = ceph_spec_bootstrap.get_roles_to_svcs_from_roles(tripleo_roles)
        expected = {
            'Compute': [],
            'CephStorage': ['CephOSD'],
            'Controller': ['CephMgr', 'CephMon']}
        self.assertEqual(roles_to_svcs, expected)

        roles = roles_to_svcs.keys()
        roles_to_hosts = ceph_spec_bootstrap.get_deployed_roles_to_hosts(metal, roles, tld)
        expected = {
            'Controller': ['oc0-controller-0.abc.local', 'oc0-controller-1.abc.local', 'oc0-controller-2.abc.local'],
            'Compute': ['oc0-compute-0.abc.local'],
            'CephStorage': ['oc0-ceph-0.abc.local', 'oc0-ceph-1.abc.local', 'oc0-ceph-2.abc.local']
        }
        self.assertEqual(roles_to_hosts, expected)

        hosts_to_ips = ceph_spec_bootstrap.get_deployed_hosts_to_ips(metal, tld)
        expected = {'oc0-ceph-0.abc.local': '192.168.24.13',
                    'oc0-ceph-1.abc.local': '192.168.24.11',
                    'oc0-ceph-2.abc.local': '192.168.24.14',
                    'oc0-compute-0.abc.local': '192.168.24.21',
                    'oc0-controller-0.abc.local': '192.168.24.23',
                    'oc0-controller-1.abc.local': '192.168.24.15',
                    'oc0-controller-2.abc.local': '192.168.24.7'}
        self.assertEqual(hosts_to_ips, expected)

        label_map = ceph_spec_bootstrap.get_label_map(hosts_to_ips, roles_to_svcs,
                                                      roles_to_hosts, ceph_service_types)
        expected = {'oc0-ceph-0.abc.local': ['osd'],
                    'oc0-ceph-1.abc.local': ['osd'],
                    'oc0-ceph-2.abc.local': ['osd'],
                    'oc0-compute-0.abc.local': [],
                    'oc0-controller-0.abc.local': ['mgr', 'mon', '_admin'],
                    'oc0-controller-1.abc.local': ['mgr', 'mon', '_admin'],
                    'oc0-controller-2.abc.local': ['mgr', 'mon', '_admin']}
        self.assertEqual(label_map, expected)

        specs = ceph_spec_bootstrap.get_specs(hosts_to_ips, label_map, ceph_service_types)
        expected = [
            {'service_type': 'host', 'addr': '192.168.24.13',
             'hostname': 'oc0-ceph-0.abc.local', 'labels': ['osd']},
            {'service_type': 'host', 'addr': '192.168.24.11',
             'hostname': 'oc0-ceph-1.abc.local', 'labels': ['osd']},
            {'service_type': 'host', 'addr': '192.168.24.14',
             'hostname': 'oc0-ceph-2.abc.local', 'labels': ['osd']},
            {'service_type': 'host', 'addr': '192.168.24.23',
             'hostname': 'oc0-controller-0.abc.local', 'labels': ['mgr', 'mon', '_admin']},
            {'service_type': 'host', 'addr': '192.168.24.15',
             'hostname': 'oc0-controller-1.abc.local', 'labels': ['mgr', 'mon', '_admin']},
            {'service_type': 'host', 'addr': '192.168.24.7',
             'hostname': 'oc0-controller-2.abc.local', 'labels': ['mgr', 'mon', '_admin']},
            {
                'service_type': 'mon',
                'service_name': 'mon',
                'service_id': 'mon',
                'placement': {
                    'hosts': ['oc0-controller-0.abc.local', 'oc0-controller-1.abc.local', 'oc0-controller-2.abc.local']
                }
            },
            {
                'service_type': 'mgr',
                'service_name': 'mgr',
                'service_id': 'mgr',
                'placement': {
                    'hosts': ['oc0-controller-0.abc.local', 'oc0-controller-1.abc.local', 'oc0-controller-2.abc.local']
                }
            },
            {
                'service_type': 'osd',
                'service_name': 'osd.default_drive_group',
                'service_id': 'default_drive_group',
                'placement': {
                    'hosts': ['oc0-ceph-0.abc.local', 'oc0-ceph-1.abc.local', 'oc0-ceph-2.abc.local']
                },
                'data_devices': {'all': True}
            }
        ]
        for index in range(0, len(expected)):
            if expected[index].get('service_type', '') == 'host':
                expected[index].get('labels', {}).sort()
                specs[index].get('labels', {}).sort()

        self.assertEqual(specs, expected)

    def test_metal_roles_based_spec_edge_site(self):
        """verify we can build a ceph spec and supporting data
           structures from a metalsmith and tripleo roles file for edge sites
        """
        ceph_service_types = ['mon', 'mgr', 'osd']
        metal = "roles/tripleo_cephadm/molecule/default/mock/mock_deployed_metal_edge_site.yaml"
        tripleo_roles = "roles/tripleo_cephadm/molecule/default/mock/mock_overcloud_roles_edge_site.yaml"
        tld = ""
        roles_to_svcs = ceph_spec_bootstrap.get_roles_to_svcs_from_roles(tripleo_roles)
        expected = {
            'DistributedComputeHCI': ['CephMgr', 'CephMon', 'CephOSD'],
            'DistributedComputeHCIScaleOut': ['CephOSD'],
            'DistributedComputeScaleOut': []}
        self.assertEqual(roles_to_svcs, expected)

        roles = roles_to_svcs.keys()
        roles_to_hosts = ceph_spec_bootstrap.get_deployed_roles_to_hosts(metal, roles, tld)
        expected = {
            'DistributedComputeHCI': ['oc0-distributedcomputehci-0', 'oc0-distributedcomputehci-1', 'oc0-distributedcomputehci-2'],
            'DistributedComputeHCIScaleOut': ['oc0-distributedcomputehciscaleout-0'],
            'DistributedComputeScaleOut': ['oc0-distributedcomputescaleout-0'],
        }
        self.assertEqual(roles_to_hosts, expected)

        hosts_to_ips = ceph_spec_bootstrap.get_deployed_hosts_to_ips(metal, tld)
        expected = {'oc0-distributedcomputehci-0': '192.168.24.13',
                    'oc0-distributedcomputehci-1': '192.168.24.11',
                    'oc0-distributedcomputehci-2': '192.168.24.14',
                    'oc0-distributedcomputehciscaleout-0': '192.168.24.21',
                    'oc0-distributedcomputescaleout-0': '192.168.24.23'}
        self.assertEqual(hosts_to_ips, expected)

        label_map = ceph_spec_bootstrap.get_label_map(hosts_to_ips, roles_to_svcs,
                                                      roles_to_hosts, ceph_service_types)
        expected = {'oc0-distributedcomputehci-0': ['mgr', 'mon', '_admin', 'osd'],
                    'oc0-distributedcomputehci-1': ['mgr', 'mon', '_admin', 'osd'],
                    'oc0-distributedcomputehci-2': ['mgr', 'mon', '_admin', 'osd'],
                    'oc0-distributedcomputehciscaleout-0': ['osd'],
                    'oc0-distributedcomputescaleout-0': []}
        self.assertEqual(label_map, expected)

        specs = ceph_spec_bootstrap.get_specs(hosts_to_ips, label_map, ceph_service_types)
        expected = [
            {'service_type': 'host', 'addr': '192.168.24.13',
             'hostname': 'oc0-distributedcomputehci-0', 'labels': ['mgr', 'mon', '_admin', 'osd']},
            {'service_type': 'host', 'addr': '192.168.24.11',
             'hostname': 'oc0-distributedcomputehci-1', 'labels': ['mgr', 'mon', '_admin', 'osd']},
            {'service_type': 'host', 'addr': '192.168.24.14',
             'hostname': 'oc0-distributedcomputehci-2', 'labels': ['mgr', 'mon', '_admin', 'osd']},
            {'service_type': 'host', 'addr': '192.168.24.21',
             'hostname': 'oc0-distributedcomputehciscaleout-0', 'labels': ['osd']},
            {
                'service_type': 'mon',
                'service_name': 'mon',
                'service_id': 'mon',
                'placement': {
                    'hosts': ['oc0-distributedcomputehci-0', 'oc0-distributedcomputehci-1', 'oc0-distributedcomputehci-2']
                }
            },
            {
                'service_type': 'mgr',
                'service_name': 'mgr',
                'service_id': 'mgr',
                'placement': {
                    'hosts': ['oc0-distributedcomputehci-0', 'oc0-distributedcomputehci-1', 'oc0-distributedcomputehci-2']
                }
            },
            {
                'service_type': 'osd',
                'service_name': 'osd.default_drive_group',
                'service_id': 'default_drive_group',
                'placement': {
                    'hosts': ['oc0-distributedcomputehci-0', 'oc0-distributedcomputehci-1', 'oc0-distributedcomputehci-2', 'oc0-distributedcomputehciscaleout-0']
                },
                'data_devices': {'all': True}
            }
        ]
        for index in range(0, len(expected)):
            if expected[index].get('service_type', '') == 'host':
                expected[index].get('labels', {}).sort()
                specs[index].get('labels', {}).sort()

        self.assertEqual(specs, expected)

    def test_inventory_based_spec(self):
        """verify we can build a ceph spec and supporting data
           structures from from a tripleo-ansible inventory
        """
        ceph_service_types = ['mon', 'mgr', 'osd']
        inventory_file = "roles/tripleo_cephadm/molecule/default/mock/mock_inventory.yml"
        tld = ""
        inventory = tripleo_inventory_manager.TripleoInventoryManager(
            inventory_file
        )
        roles_to_svcs = ceph_spec_bootstrap.get_roles_to_svcs_from_inventory(inventory)
        expected = {'Standalone': ['CephOSD', 'CephMgr', 'CephMon']}
        self.assertEqual(roles_to_svcs, expected)

        roles = roles_to_svcs.keys()
        hosts_to_ips = ceph_spec_bootstrap.get_inventory_hosts_to_ips(inventory, roles, tld)
        expected = {'standalone': '192.168.24.1'}
        self.assertEqual(hosts_to_ips, expected)

        roles_to_hosts = ceph_spec_bootstrap.get_inventory_roles_to_hosts(inventory, roles, tld)
        expected = {'Standalone': ['standalone']}
        self.assertEqual(roles_to_hosts, expected)

        label_map = ceph_spec_bootstrap.get_label_map(hosts_to_ips, roles_to_svcs,
                                                      roles_to_hosts, ceph_service_types)
        expected = {'standalone': ['osd', 'mgr', '_admin', 'mon']}
        # the order of the labels does not matter, sort them for consistency
        label_map['standalone'].sort()
        expected['standalone'].sort()
        self.assertEqual(label_map, expected)

        specs = ceph_spec_bootstrap.get_specs(hosts_to_ips, label_map, ceph_service_types)
        expected = [{'addr': '192.168.24.1',
                     'hostname': 'standalone',
                     'labels': ['osd', 'mgr', '_admin', 'mon'],
                     'service_type': 'host'},
                    {'placement': {'hosts': ['standalone']},
                     'service_id': 'mon',
                     'service_name': 'mon',
                     'service_type': 'mon'},
                    {'placement': {'hosts': ['standalone']},
                     'service_id': 'mgr',
                     'service_name': 'mgr',
                     'service_type': 'mgr'},
                    {'data_devices': {'all': True},
                     'placement': {'hosts': ['standalone']},
                     'service_id': 'default_drive_group',
                     'service_name': 'osd.default_drive_group',
                     'service_type': 'osd'}]
        # the order of the labels does not matter, sort them for consistency
        expected[0]['labels'].sort()
        specs[0]['labels'].sort()

        self.assertEqual(len(specs), len(expected))
        self.assertEqual(specs, expected)

    def test_inventory_based_spec_with_tld(self):
        """verify we can build a ceph spec and supporting data
           structures from from a tripleo-ansible inventory
        """
        ceph_service_types = ['mon', 'mgr', 'osd']
        inventory_file = "roles/tripleo_cephadm/molecule/default/mock/mock_inventory.yml"
        tld = "abc.local"
        inventory = tripleo_inventory_manager.TripleoInventoryManager(
            inventory_file
        )
        roles_to_svcs = ceph_spec_bootstrap.get_roles_to_svcs_from_inventory(inventory)
        expected = {'Standalone': ['CephOSD', 'CephMgr', 'CephMon']}
        self.assertEqual(roles_to_svcs, expected)

        roles = roles_to_svcs.keys()
        hosts_to_ips = ceph_spec_bootstrap.get_inventory_hosts_to_ips(inventory, roles, tld)
        expected = {'standalone.abc.local': '192.168.24.1'}
        self.assertEqual(hosts_to_ips, expected)

        roles_to_hosts = ceph_spec_bootstrap.get_inventory_roles_to_hosts(inventory, roles, tld)
        expected = {'Standalone': ['standalone.abc.local']}

        label_map = ceph_spec_bootstrap.get_label_map(hosts_to_ips, roles_to_svcs,
                                                      roles_to_hosts, ceph_service_types)
        expected = {'standalone.abc.local': ['osd', 'mgr', '_admin', 'mon']}
        # the order of the labels does not matter, sort them for consistency
        label_map['standalone.abc.local'].sort()
        expected['standalone.abc.local'].sort()
        self.assertEqual(label_map, expected)

    def test_standalone_spec(self):
        hostname = socket.gethostname()
        expected = []
        expected.append(yaml.safe_load('''
        addr: 192.168.122.252
        hostname: %s
        labels:
        - mon
        - _admin
        - osd
        - mgr
        service_type: host
        ''' % hostname))

        expected.append(yaml.safe_load('''
        placement:
          hosts:
          - %s
        service_id: mon
        service_name: mon
        service_type: mon
        ''' % hostname))

        expected.append(yaml.safe_load('''
        placement:
          hosts:
          - %s
        service_id: mgr
        service_name: mgr
        service_type: mgr
        ''' % hostname))

        expected.append(yaml.safe_load('''
        data_devices:
          all: true
        placement:
          hosts:
          - %s
        service_id: default_drive_group
        service_name: osd.default_drive_group
        service_type: osd
        ''' % hostname))

        expected_spec = tempfile.NamedTemporaryFile()
        for spec in expected:
            with open(expected_spec.name, 'a') as f:
                f.write('---\n')
                f.write(yaml.safe_dump(spec))

        my_spec = tempfile.NamedTemporaryFile()
        ceph_spec_bootstrap.ceph_spec_standalone(my_spec.name,
                                                 mon_ip='192.168.122.252', tld="")
        self.assertCountEqual(
            list(io.open(expected_spec.name)),
            list(io.open(my_spec.name)))
        expected_spec.close()
        my_spec.close()
