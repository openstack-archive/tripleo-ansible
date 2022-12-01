# Copyright 2022 Red Hat, Inc.
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
"""Test tripleo_inventory_manager module"""

import os

import tripleo_common.tests
from tripleo_ansible.ansible_plugins.module_utils import tripleo_inventory_manager
from tripleo_ansible.tests import base as tests_base


class TestTripleoInventoryHost(tests_base.TestCase):
    """Test the TripleoInventoryHost class"""
    def test_basic(self):
        """Basic construction test"""
        h = tripleo_inventory_manager.TripleoInventoryHost('foobar')
        self.assertEqual('foobar', str(h))
        self.assertEqual("TripleoInventoryHost('foobar')", repr(h))
        self.assertEqual({}, h.groups)
        self.assertEqual({}, h.vars)

    def test_add_group(self):
        """Test adding a host to a group creates a weak reference"""
        h = tripleo_inventory_manager.TripleoInventoryHost('foobar')

        class FakeGroup:
            name = 'bar'

        g = FakeGroup()
        h.add_group(g)
        self.assertEqual({'bar': g}, h.groups)
        del g
        self.assertEqual({'bar': None}, h.groups)


class TestTripleoInventoryGroup(tests_base.TestCase):
    """Test the TripleoInventoryGroup class"""
    def test_basic(self):
        """Basic construction test"""
        g = tripleo_inventory_manager.TripleoInventoryGroup('foobar')
        self.assertEqual('foobar', str(g))
        self.assertEqual("TripleoInventoryGroup('foobar')", repr(g))
        self.assertEqual({}, g.hosts)
        self.assertEqual({}, g.children)

    def test_add_host(self):
        """"Test adding a host to a group creates a weak reference"""
        class FakeHost:
            name = 'bar'

        h = FakeHost()
        g = tripleo_inventory_manager.TripleoInventoryGroup('foobar')
        g.add_host(h)
        self.assertEqual({'bar': h}, g.hosts)
        del h
        self.assertEqual({'bar': None}, g.hosts)

    def test_add_child(self):
        """Test adding a child to a group creates a weak reference"""
        g1 = tripleo_inventory_manager.TripleoInventoryGroup('foo')
        g2 = tripleo_inventory_manager.TripleoInventoryGroup('bar')
        g1.add_child(g2)
        g2.add_parent(g1)
        self.assertEqual({'bar': g2}, g1.children)
        del g2
        self.assertEqual({'bar': None}, g1.children)

    def test_add_parent(self):
        """Test adding a partent to a group creates a weak reference"""
        g1 = tripleo_inventory_manager.TripleoInventoryGroup('foo')
        g2 = tripleo_inventory_manager.TripleoInventoryGroup('bar')
        g2.add_child(g1)
        g1.add_parent(g2)
        self.assertEqual({'bar': g2}, g1.parents)
        del g2
        self.assertEqual({'bar': None}, g1.parents)

    def test_get_descendents(self):
        """Test get_descendents removes duplicates"""

        # Create a diamond dependancy graph
        g1 = tripleo_inventory_manager.TripleoInventoryGroup('foo')
        g2 = tripleo_inventory_manager.TripleoInventoryGroup('bar')
        g3 = tripleo_inventory_manager.TripleoInventoryGroup('baz')
        g4 = tripleo_inventory_manager.TripleoInventoryGroup('bez')
        g1.add_child(g2)
        g2.add_parent(g1)
        g1.add_child(g3)
        g3.add_parent(g1)
        g2.add_child(g4)
        g4.add_parent(g2)
        g3.add_child(g4)
        g4.add_parent(g3)
        self.assertEqual(set([g2, g3, g4]), set(g1.get_descendants()))

    def test_add_child_cyclic_dependency(self):
        """Test add_child cyclic dependency"""

        g1 = tripleo_inventory_manager.TripleoInventoryGroup('foo')
        g2 = tripleo_inventory_manager.TripleoInventoryGroup('bar')
        g1.add_child(g2)
        g2.add_parent(g1)
        self.assertRaises(RuntimeError, g2.add_child, g1)

    def test_add_parent_cyclic_dependency(self):
        """Test add_child cyclic dependency"""

        g1 = tripleo_inventory_manager.TripleoInventoryGroup('foo')
        g2 = tripleo_inventory_manager.TripleoInventoryGroup('bar')
        g1.add_child(g2)
        g2.add_parent(g1)
        self.assertRaises(RuntimeError, g1.add_parent, g2)


class TestTripleoInventoryManager(tests_base.TestCase):
    """Test the TripleoInventoryManager class"""
    def test_parse_simple_inventory(self):
        inv_data = {
            'all': {
                'children': {
                    'more': {
                        'hosts': {
                            'host1': {},
                            'host2': {'foo': 'bar'}
                        }
                    },
                    'and_more': {
                        'hosts': {
                            'host2': {}
                        },
                        'vars': {
                            'foo': 'two',
                            'bar': 'three'
                        }
                    }
                },
                'vars': {
                    'bar': 'baz'
                },
                'hosts': 'host3'  # ansible accepts this format too
            }
        }

        i = tripleo_inventory_manager.TripleoInventoryManager()
        h, g = i._parse_inventory(inv_data)
        self.assertEqual(set(['host1', 'host2', 'host3']), set(h.keys()))
        self.assertEqual({'bar': 'three', 'foo': 'bar'}, h['host2'].resolve_vars())

    def _get_tripleo_common_test_inv_path(self, filename):
        return os.path.join(os.path.dirname(tripleo_common.tests.__file__), 'inventory_data', filename)

    def test_real_inventory_old_style(self):
        i = tripleo_inventory_manager.TripleoInventoryManager(self._get_tripleo_common_test_inv_path('overcloud_static.yaml'))
        self.assertEqual(set(['overcloud-controller-0', 'overcloud-novacompute-0', 'undercloud']), set(i.hosts.keys()))
        self.assertEqual(set(['overcloud-controller-0', 'overcloud-novacompute-0']), set([h.name for h in i.get_hosts('tuned')]))
        self.assertEqual(set(['overcloud-controller-0']), set([h.name for h in i.get_hosts('nova_scheduler')]))
        self.assertEqual(set(['overcloud-novacompute-0']), set([h.name for h in i.get_hosts('nova_libvirt')]))
        self.assertEqual('Controller', i.hosts['overcloud-controller-0'].resolve_vars().get('tripleo_role_name'))
        self.assertEqual('Compute', i.hosts['overcloud-novacompute-0'].resolve_vars().get('tripleo_role_name'))

    def test_real_inventory_multistack_style(self):
        i = tripleo_inventory_manager.TripleoInventoryManager(self._get_tripleo_common_test_inv_path('merged_static.yaml'))
        self.assertEqual(
            set(['overcloud-controller-0', 'overcloud-novacompute-0', 'cell1-cellcontrol-0', 'cell1-compute-0', 'undercloud']),
            set(i.hosts.keys())
        )
        self.assertEqual(
            set(['overcloud-controller-0', 'overcloud-novacompute-0', 'cell1-cellcontrol-0', 'cell1-compute-0']),
            set([h.name for h in i.get_hosts('tuned')])
        )
        self.assertEqual(set(['overcloud-controller-0', 'overcloud-novacompute-0']), set([h.name for h in i.get_hosts('overcloud')]))
        self.assertEqual(set(['cell1-cellcontrol-0', 'cell1-compute-0']), set([h.name for h in i.get_hosts('cell1')]))
        self.assertEqual(set(['overcloud-controller-0']), set([h.name for h in i.get_hosts('nova_scheduler')]))
        self.assertEqual(set(['overcloud-controller-0', 'cell1-cellcontrol-0']), set([h.name for h in i.get_hosts('nova_conductor')]))
        self.assertEqual(set(['overcloud-novacompute-0', 'cell1-compute-0']), set([h.name for h in i.get_hosts('nova_libvirt')]))
        self.assertEqual('Controller', i.hosts['overcloud-controller-0'].resolve_vars().get('tripleo_role_name'))
        self.assertEqual('Compute', i.hosts['overcloud-novacompute-0'].resolve_vars().get('tripleo_role_name'))
        self.assertEqual('CellController', i.hosts['cell1-cellcontrol-0'].resolve_vars().get('tripleo_role_name'))
        self.assertEqual('Compute', i.hosts['cell1-compute-0'].resolve_vars().get('tripleo_role_name'))
