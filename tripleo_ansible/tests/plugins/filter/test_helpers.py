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

from ansible import errors

from tripleo_ansible.ansible_plugins.filter import helpers
from tripleo_ansible.tests import base as tests_base


class TestHelperFilters(tests_base.TestCase):

    def setUp(self):
        super(TestHelperFilters, self).setUp()
        self.filters = helpers.FilterModule()

    def test_subsort(self):
        dict = {
          'keystone': {
            'start_order': 1,
            'image': 'quay.io/tripleo/keystone'
          },
          'haproxy': {
            'image': 'quay.io/tripleo/haproxy'
          },
          'mysql': {
            'start_order': 0,
            'image': 'quay.io/tripleo/mysql'
          }
        }
        expected_ordered_dict = {
          0: [
            {'haproxy': {
              'image': 'quay.io/tripleo/haproxy',
              'start_order': 0
            }},
            {'mysql': {
              'image': 'quay.io/tripleo/mysql',
              'start_order': 0
            }}
          ],
          1: [
            {'keystone': {
              'image': 'quay.io/tripleo/keystone',
              'start_order': 1
            }}
          ]
        }
        result = self.filters.subsort(dict_to_sort=dict,
                                      attribute='start_order')
        self.assertEqual(result, expected_ordered_dict)

    def test_subsort_with_null_value(self):
        dict = {
          'keystone': {
            'start_order': 1,
            'image': 'quay.io/tripleo/keystone'
          },
          'haproxy': {
            'image': 'quay.io/tripleo/haproxy'
          },
          'mysql': {
            'start_order': 0,
            'image': 'quay.io/tripleo/mysql'
          }
        }
        expected_ordered_dict = {
          0: [
            {'mysql': {
              'image': 'quay.io/tripleo/mysql',
              'start_order': 0
            }}
          ],
          1: [
            {'keystone': {
              'image': 'quay.io/tripleo/keystone',
              'start_order': 1
            }}
          ],
          5: [
            {'haproxy': {
              'image': 'quay.io/tripleo/haproxy',
              'start_order': 5
            }}
          ]
        }
        result = self.filters.subsort(dict_to_sort=dict,
                                      attribute='start_order', null_value=5)
        self.assertEqual(result, expected_ordered_dict)

    def test_singledict(self):
        list = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone'
                },
            },
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                }
            }
        ]
        expected_dict = {
          'keystone': {
            'start_order': 1,
            'image': 'quay.io/tripleo/keystone'
          },
          'mysql': {
            'start_order': 0,
            'image': 'quay.io/tripleo/mysql'
          }
        }
        result = self.filters.singledict(list)
        self.assertEqual(result, expected_dict)

    def test_singledict_with_merge(self):
        list = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone'
                },
            },
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                }
            }
        ]
        expected_dict = {
          'keystone': {
            'start_order': 1,
            'image': 'quay.io/tripleo/keystone'
          },
          'mysql': {
            'start_order': 0,
            'image': 'quay.io/tripleo/mysql:hotfix'
          }
        }
        override = {
          'mysql': {
            'image': 'quay.io/tripleo/mysql:hotfix'
          }
        }
        result = self.filters.singledict(list, merge_with=override)
        self.assertEqual(result, expected_dict)

    def test_list_of_keys(self):
        keys = [
            {
                'foo1': 'bar1'
            },
            {
                'foo2': 'bar2'
            },
        ]
        expected_list = ['foo1', 'foo2']
        result = self.filters.list_of_keys(keys)
        self.assertEqual(result, expected_list)

    def test_haskey(self):
        data = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone',
                  'restart': 'always'
                },
            },
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                }
            }
        ]
        expected_list = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone',
                  'restart': 'always'
                },
            }
        ]
        result = self.filters.haskey(data=data,
                                     attribute='restart', value='always')
        self.assertEqual(result, expected_list)

    def test_haskey_exclude(self):
        data = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone',
                  'command': 'sleep 10',
                  'restart': 'always'
                },
            },
            {
                'nova': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/nova',
                  'command': 'sleep 10',
                  'action': 'exec'
                },
            },
            {
                'mysql': {
                  'start_order': 0,
                  'command': 'sleep 10',
                  'image': 'quay.io/tripleo/mysql'
                }
            },
            {
                'haproxy': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/haproxy'
                }
            }
        ]
        expected_list = [
            {
                'mysql': {
                  'start_order': 0,
                  'command': 'sleep 10',
                  'image': 'quay.io/tripleo/mysql'
                },
            }
        ]
        result = self.filters.haskey(data=data,
                                     attribute='command',
                                     excluded_keys=['action', 'restart'])
        self.assertEqual(result, expected_list)

    def test_haskey_reverse_exclude(self):
        data = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone',
                  'restart': 'always'
                },
            },
            {
                'nova': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/nova',
                  'action': 'exec'
                },
            },
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                }
            }
        ]
        expected_list = [
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                },
            }
        ]
        result = self.filters.haskey(data=data,
                                     attribute='restart',
                                     value='always',
                                     reverse=True,
                                     excluded_keys=['action'])
        self.assertEqual(result, expected_list)

    def test_haskey_reverse(self):
        data = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone',
                  'restart': 'always'
                },
            },
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                }
            }
        ]
        expected_list = [
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                },
            }
        ]
        result = self.filters.haskey(data=data,
                                     attribute='restart',
                                     value='always',
                                     reverse=True)
        self.assertEqual(result, expected_list)

    def test_haskey_any(self):
        data = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone',
                  'restart': 'always'
                },
            },
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                }
            }
        ]
        expected_list = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone',
                  'restart': 'always'
                },
            }
        ]
        result = self.filters.haskey(data=data,
                                     attribute='restart',
                                     any=True)
        self.assertEqual(result, expected_list)

    def test_haskey_any_reverse(self):
        data = [
            {
                'keystone': {
                  'start_order': 1,
                  'image': 'quay.io/tripleo/keystone',
                  'restart': 'always'
                },
            },
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                }
            }
        ]
        expected_list = [
            {
                'mysql': {
                  'start_order': 0,
                  'image': 'quay.io/tripleo/mysql'
                },
            }
        ]
        result = self.filters.haskey(data=data,
                                     attribute='restart',
                                     reverse=True,
                                     any=True)
        self.assertEqual(result, expected_list)

    def test_abspath(self):
        file_path = '/etc/hosts'
        result = self.filters.tht_abspath(file_path)
        self.assertEqual(result, '/etc/hosts')

        file_path = ['/etc', 'tmp']
        result = self.filters.tht_abspath(
            file_path, ignore_error=True)
        self.assertEqual(result, file_path)

    def test_abspath_not_found(self):
        file_path = 'plan-environment.yaml'
        ex = self.assertRaises(
            errors.AnsibleFilterError,
            self.filters.tht_abspath, file_path)
        msg = ("Can't find path plan-environment.yaml")
        self.assertEqual(msg, str(ex))

    def test_needs_delete(self):
        data = [
            {
                'Name': 'mysql',
                'Config': {
                    'Labels': {
                        'config_id': 'tripleo_step1'
                    }
                }
            },
            {
                'Name': 'rabbitmq',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo_ansible',
                        'config_id': 'tripleo_step1',
                        'container_name': 'rabbitmq',
                        'name': 'rabbitmq'
                    }
                }
            },
            {
                'Name': 'swift',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo',
                        'config_id': 'tripleo_step1',
                        'container_name': 'swift',
                        'name': 'swift',
                        'config_data': {'foo': 'bar'}
                    }
                }
            },
            {
                'Name': 'heat',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo-Undercloud',
                        'config_id': 'tripleo_step1',
                        'container_name': 'heat',
                        'name': 'heat',
                        'config_data': "{'start_order': 0}"
                    }
                }
            },
            {
                'Name': 'test1',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo-other',
                        'config_id': 'tripleo_step1',
                        'container_name': 'test1',
                        'name': 'test1',
                        'config_data': {'start_order': 0}
                    }
                }
            },
            {
                'Name': 'haproxy',
                'Config': {
                    'Labels': {
                        'managed_by': 'paunch',
                        'config_id': 'tripleo_step1',
                        'config_data': ""
                    }
                }
            },
            {
                'Name': 'tripleo',
                'Config': {
                    'Labels': {
                        'foo': 'bar'
                    }
                }
            },
            {
                'Name': 'none_tripleo',
                'Config': {
                    'Labels': None
                }
            },
            {
                'Name': 'old_tripleo',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo_ansible',
                        'config_id': 'tripleo_step1',
                        'config_data': ""
                    }
                }
            },
        ]
        config = {
            # we don't want that container to be touched: no restart
            'mysql': '',
            # container has no Config, therefore no Labels: restart needed
            'rabbitmq': '',
            # container has no config_data: restart needed
            'haproxy': '',
            # container isn't part of config_id: no restart
            'tripleo': '',
            # container isn't in container_infos but not part of config_id:
            # no restart.
            'doesnt_exist': '',
            # config_data didn't change: no restart
            'swift': {'foo': 'bar'},
            # config_data changed: restart needed
            'heat': {'start_order': 1},
            # config_data changed: restart needed
            'test1': {'start_order': 2},
        }
        expected_list = ['rabbitmq', 'haproxy', 'heat', 'test1', 'old_tripleo']
        result = self.filters.needs_delete(container_infos=data,
                                           config=config,
                                           config_id='tripleo_step1',
                                           clean_orphans=True)
        self.assertEqual(result, expected_list)

    def test_needs_delete_no_config_check(self):
        data = [
            {
                'Name': 'mysql',
                'Config': {
                    'Labels': {
                        'config_id': 'tripleo_step1'
                    }
                }
            },
            {
                'Name': 'rabbitmq',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo_ansible',
                        'config_id': 'tripleo_step1',
                        'container_name': 'rabbitmq',
                        'name': 'rabbitmq'
                    }
                }
            },
            {
                'Name': 'swift',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo',
                        'config_id': 'tripleo_step1',
                        'container_name': 'swift',
                        'name': 'swift',
                        'config_data': {'foo': 'bar'}
                    }
                }
            },
            {
                'Name': 'heat',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo-Undercloud',
                        'config_id': 'tripleo_step1',
                        'container_name': 'heat',
                        'name': 'heat',
                        'config_data': "{'start_order': 0}"
                    }
                }
            },
            {
                'Name': 'test1',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo-other',
                        'config_id': 'tripleo_step1',
                        'container_name': 'test1',
                        'name': 'test1',
                        'config_data': {'start_order': 0}
                    }
                }
            },
            {
                'Name': 'haproxy',
                'Config': {
                    'Labels': {
                        'managed_by': 'paunch',
                        'config_id': 'tripleo_step1',
                        'config_data': ""
                    }
                }
            },
            {
                'Name': 'tripleo',
                'Config': {
                    'Labels': {
                        'foo': 'bar'
                    }
                }
            },
            {
                'Name': 'none_tripleo',
                'Config': {
                    'Labels': None
                }
            },
            {
                'Name': 'old_tripleo',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo_ansible',
                        'config_id': 'tripleo_step1',
                        'config_data': ""
                    }
                }
            },
        ]
        config = {
            # we don't want that container to be touched: no restart
            'mysql': '',
            # container has no Config, therefore no Labels: restart needed
            # but will be skipped because check_config is False
            'rabbitmq': '',
            # container has no config_data: restart needed
            # but will be skipped because check_config is False
            'haproxy': '',
            # container isn't part of config_id: no restart
            'tripleo': '',
            # container isn't in container_infos but not part of config_id:
            # no restart.
            'doesnt_exist': '',
            # config_data didn't change: no restart
            'swift': {'foo': 'bar'},
            # config_data changed: restart needed
            # but will be skipped because check_config is False
            'heat': {'start_order': 1},
            # config_data changed: restart needed
            # but will be skipped because check_config is False
            'test1': {'start_order': 2},
        }
        expected_list = ['rabbitmq', 'old_tripleo']
        result = self.filters.needs_delete(container_infos=data,
                                           config=config,
                                           config_id='tripleo_step1',
                                           check_config=False,
                                           clean_orphans=True)
        self.assertEqual(result, expected_list)

    def test_needs_delete_single_config(self):
        data = [
            {
                'Name': 'rabbitmq',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo_ansible',
                        'config_id': 'tripleo_step1',
                        'container_name': 'rabbitmq',
                        'name': 'rabbitmq'
                    }
                }
            },
            {
                'Name': 'swift',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo',
                        'config_id': 'tripleo_step1',
                        'container_name': 'swift',
                        'name': 'swift',
                        'config_data': {'foo': 'bar'}
                    }
                }
            },
            {
                'Name': 'heat',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo-Undercloud',
                        'config_id': 'tripleo_step1',
                        'container_name': 'heat',
                        'name': 'heat',
                        'config_data': "{'start_order': 0}"
                    }
                }
            },
            {
                'Name': 'haproxy',
                'Config': {
                    'Labels': {
                        'managed_by': 'paunch',
                        'config_id': 'tripleo_step1',
                        'config_data': ""
                    }
                }
            },
            {
                'Name': 'none_tripleo',
                'Config': {
                    'Labels': None
                }
            },
            {
                'Name': 'old_tripleo',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo_ansible',
                        'config_id': 'tripleo_step1',
                        'config_data': ""
                    }
                }
            },
        ]
        config = {
            # config_data changed: restart needed
            'heat': {'start_order': 1},
        }
        expected_list = ['heat']
        result = self.filters.needs_delete(container_infos=data,
                                           config=config,
                                           config_id='tripleo_step1')
        self.assertEqual(result, expected_list)

    def test_needs_delete_no_config(self):
        data = [
            {
                'Name': 'heat',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo-Undercloud',
                        'config_id': 'tripleo_step1',
                        'container_name': 'heat',
                        'name': 'heat',
                        'config_data': "{'start_order': 0}"
                    }
                }
            },
        ]
        config = {}
        expected_list = []
        result = self.filters.needs_delete(container_infos=data,
                                           config=config,
                                           config_id='tripleo_step1')
        self.assertEqual(result, expected_list)

    def test_get_key_from_dict(self):
        data = {
           'nova_api': {
             'project': 'service1'
           },
           'glance_api': {
             'project': 'service1'
           },
           'heat_api': {
             'user': 'heat'
           },
           'cinder_api': {
             'project': 'service2'
           }
        }
        expected_list = ['service1', 'service3', 'service2']
        result = self.filters.get_key_from_dict(data, key='project',
                                                default='service3')
        self.assertEqual(result, expected_list)

    def test_get_key_from_dict_with_list_input(self):
        data = {
           'nova_api': {
             'roles': ['service', 'admin']
           },
           'glance_api': {
             'roles': 'service1'
           },
           'heat_api': {
             'user': 'heat'
           },
           'cinder_api': {
             'project': 'service2',
             'roles': ['service', 'service4']
           }
        }
        expected_list = ['service', 'admin', 'service1', 'service4']
        result = self.filters.get_key_from_dict(data, key='roles',
                                                default='service')
        self.assertEqual(result, expected_list)

    def test_get_key_from_dict_with_dict_input(self):
        data = {
           'nova_api': {
             'users': {'nova': {'password': 'secret',
                       'roles': ['foo', 'bar']}},
           },
           'glance_api': {
             'roles': 'service1'
           },
           'heat_api': {
             'user': 'heat'
           },
           'cinder_api': {
             'project': 'service2'
           }
        }
        expected_list = [{'nova': {'password': 'secret', 'roles':
                         ['foo', 'bar']}}]
        result = self.filters.get_key_from_dict(data, key='users')
        self.assertEqual(result, expected_list)

    def test_recursive_get_key_from_dict(self):
        data = {
            'step': {'container': {'name': 'foo', 'image': 'bar'},
                     'other_container': {'name': 'meh', 'image': 'baz'}
            }
        }
        expected_list = ['bar', 'baz']
        result = self.filters.recursive_get_key_from_dict(data, 'image')
        self.assertEqual(result, expected_list)

    def test_recursive_get_key_from_dict_multiple_levels(self):
        data = {
            'a': {'b': {'val': 1},
                  'c': {'val': 2, 'd': {'val': 3}}
            }
        }
        expected_list = [1, 2, 3]
        result = self.filters.recursive_get_key_from_dict(data, 'val')
        self.assertEqual(result, expected_list)

    def test_container_exec_cmd(self):
        data = {
            "action": "exec",
            "environment": {
                "OS_BOOTSTRAP_PASSWORD": "IH7PdaZc5DozbmunSTjMa7",
                "KOLLA_BOOTSTRAP": True
            },
            "start_order": 3,
            "command": [
                "keystone",
                "/usr/bin/bootstrap_host_exec",
                "keystone",
                "keystone-manage",
                "bootstrap"
            ],
            "user": "root"
        }
        expected_cmd = ['podman', 'exec', '--user=root',
                        '--env=KOLLA_BOOTSTRAP=True',
                        '--env=OS_BOOTSTRAP_PASSWORD=IH7PdaZc5DozbmunSTjMa7',
                        'keystone', '/usr/bin/bootstrap_host_exec',
                        'keystone', 'keystone-manage', 'bootstrap']
        result = self.filters.container_exec_cmd(data=data)
        self.assertEqual(result, expected_cmd)

    def test_containers_not_running(self):
        results = [
            {
                "Name": "keystone",
                "State": {"Running": False}
            },
            {
                "Name": "neutron",
                "State": {"Running": True}
            }
        ]
        commands = [{
            "keystone_bootstrap": {
                "action": "exec",
                "command": [
                    "keystone",
                    "/usr/bin/bootstrap_host_exec",
                    "keystone",
                    "keystone-manage",
                    "bootstrap"
                ]
            },
            "neutron_bootstrap": {
                "action": "exec",
                "command": [
                    "neutron",
                    "/usr/bin/bootstrap_host_exec",
                    "neutron",
                    "neutron-manage",
                    "bootstrap"
                ]
            }
        }]

        expected = ['keystone']
        actual = self.filters.containers_not_running(results, commands)
        self.assertEqual(actual, expected)

    def test_containers_not_running_missing_command(self):
        results = [
            {
                "Name": "keystone",
                "State": {"Running": True}
            },
            {
                "Name": "neutron",
                "State": {"Running": True}
            }
        ]
        commands = [{
            "keystone_bootstrap": {
                "action": "exec",
                "command": [
                    "keystone",
                    "/usr/bin/bootstrap_host_exec",
                    "keystone",
                    "keystone-manage",
                    "bootstrap"
                ]
            },
            "neutron_bootstrap": {
                "action": "exec",
            }
        }]
        expected = []
        actual = self.filters.containers_not_running(results, commands)
        self.assertEqual(actual, expected)

    def test_get_role_assignments(self):
        data = [{
           'nova': {
             'roles': ['service', 'admin'],
           },
           'glance': {
             'roles': 'service1',
             'user': 'glance'
           },
           'cinder': {
             'project': 'service2'
           },
           'heat': {
             'domain': 'heat_domain'
           }
        }]
        expected_hash = {
          'admin': [{'nova': {'project': 'service'}},
                    {'cinder': {'project': 'service2'}},
                    {'heat': {'domain': 'heat_domain'}}
                   ],
          'service': [{'nova': {'project': 'service'}}],
          'service1': [{'glance': {'project': 'service'}}]
        }
        result = self.filters.get_role_assignments(data)
        self.assertEqual(result, expected_hash)

    def test_get_domain_id(self):
        openstack_domains = [
            {
                "description": "The default domain",
                "enabled": "true",
                "id": "default",
                "name": "Default"
            },
            {
                "description": "The heat stack domain",
                "enabled": "true",
                "id": "fd85b560d4554fd8bf363728e4a3863e",
                "name": "heat_stack"
            }
        ]
        result = self.filters.get_domain_id('heat_stack', openstack_domains)
        self.assertEqual(result, 'fd85b560d4554fd8bf363728e4a3863e')

    def test_get_domain_id_empty(self):
        openstack_domains = []
        result = self.filters.get_domain_id('', openstack_domains)
        self.assertEqual(result, None)

    def test_get_domain_id_not_found(self):
        openstack_domains = [
            {
                "description": "The default domain",
                "enabled": "true",
                "id": "default",
                "name": "Default"
            },
            {
                "description": "The heat stack domain",
                "enabled": "true",
                "id": "fd85b560d4554fd8bf363728e4a3863e",
                "name": "heat_stack"
            }
        ]
        self.assertRaises(
            KeyError,
            lambda: self.filters.get_domain_id('ghost', openstack_domains)
        )

    def test_get_changed_containers(self):
        data = [
            {
                "podman_actions": [],
                "container": {
                    "Name": "haproxy",
                }
            },
            {
                "podman_actions": ['podman rm mysql'],
                "container": {
                    "Name": "mysql",
                }
            }
        ]
        expected_list = ['mysql']
        result = self.filters.get_changed_containers(data)
        self.assertEqual(result, expected_list)

    def test_get_failed_containers(self):
        data = [
            {
                "ansible_job_id": "948704694230.17597",
                "ansible_loop_var": "container_data",
                "changed": True,
                "create_async_result_item": {
                    "container_data": {
                        "haproxy": {
                            "image": "haproxy:latest",
                        }
                    }
                },
                "failed": False,
                "finished": 1,
                "results_file": "/root/.ansible_async/948704694230.17597",
                "started": 1
            },
            {
                "ansible_job_id": "9487088344230.17597",
                "ansible_loop_var": "container_data",
                "changed": True,
                "create_async_result_item": {
                    "stderr": "not happy",
                    "container_data": {
                        "haproxy_failed": {
                            "image": "haproxy:latest",
                        }
                    }
                },
                "failed": False,
                "finished": 1,
                "results_file": "/root/.ansible_async/948704694230.17597",
                "started": 1
            },
            {
                "ansible_job_id": "948704694230.17597",
                "ansible_loop_var": "container_data",
                "changed": True,
                "create_async_result_item": {
                    "container_data": {
                        "memcached": {
                            "image": "memcached:latest",
                        }
                    }
                },
                "failed": True,
                "finished": 1,
                "results_file": "/root/.ansible_async/948704694230.17597",
                "started": 1
            },
            {
                "ansible_job_id": "316140143697.17616",
                "ansible_loop_var": "container_data",
                "changed": True,
                "create_async_result_item": {
                    "container_data": {
                        "mysql": {
                            "image": "mysql:latest",
                        }
                    }
                },
                "failed": False,
                "finished": 0,
                "results_file": "/root/.ansible_async/316140143697.17616",
                "started": 1
            },
            {
                "ansible_job_id": "3161822143697.17616",
                "ansible_loop_var": "container_data",
                "changed": True,
                "create_async_result_item": {},
                "finished": 0,
                "results_file": "/root/.ansible_async/316143697.17616",
                "started": 1
            }
        ]
        expected_list = ['haproxy_failed', 'memcached', 'mysql']
        result = self.filters.get_failed_containers(data)
        self.assertEqual(result, expected_list)

    def test_get_changed_async_task_names(self):
        results = [
            {
                "ansible_loop_var": "systemd_loop",
                "changed": False,
                "failed": False,
                "systemd_loop": {
                    'keystone': {
                        "config": "foo"
                    }
                },
            },
            {
                "ansible_loop_var": "systemd_loop",
                "changed": False,
                "failed": False,
                "systemd_loop": {
                    'mysql': {
                        "config": "foo"
                    }
                },
            },
            {
                "ansible_loop_var": "systemd_loop",
                "changed": True,
                "failed": False,
                "systemd_loop": {
                    'haproxy': {
                        "config": "foo"
                    }
                },
            },
            {
                "changed": True,
                "failed": False,
                "item": {
                    'memcached': {
                        "config": "foo"
                    }
                },
            },
        ]
        data = {}
        data['results'] = results
        expected_list = ['mysql', 'haproxy', 'memcached']
        result = self.filters.get_changed_async_task_names(data=data, extra=['mysql'])
        self.assertEqual(result, expected_list)

    def test_dict_to_list(self):
        dict = {
          'keystone': {
            'image': 'quay.io/tripleo/keystone'
          },
          'haproxy': {
            'image': 'quay.io/tripleo/haproxy'
          }
        }
        expected_list = [
          {'keystone': {
            'image': 'quay.io/tripleo/keystone',
          }},
          {'haproxy': {
            'image': 'quay.io/tripleo/haproxy',
          }}
        ]
        result = self.filters.dict_to_list(data=dict)
        self.assertEqual(result, expected_list)

    def test_snake_case(self):
        expected_string = "ceph_storage"
        result = self.filters.snake_case("CephStorage")
        self.assertEqual(result, expected_string)

        expected_string = "http_worker"
        result = self.filters.snake_case("HTTPWorker")
        self.assertEqual(result, expected_string)

        expected_string = "metrics_qdr"
        result = self.filters.snake_case("MetricsQdr")
        self.assertEqual(result, expected_string)

    def test_get_changed_async_task_names_empty(self):
        result = self.filters.get_changed_async_task_names(data=[])
        self.assertEqual(result, [])

    def test_get_filtered_service_chain(self):
        expected_dict = {'id': 1, 'data': 'things'}
        role_chain_resources = [1, 3, 4]
        resource_chains = [{'id': 1, 'data': 'things'}, {'id': 2}]
        result = self.filters.get_filtered_service_chain(resource_chains, role_chain_resources)
        self.assertEqual(result, expected_dict)

    def test_get_filtered_role_resources(self):
        expected_dict = {'test1': {'data': 'things'}}
        service_chain_resources = ['test1', 'test3']
        tripleo_resources = {'test1': {'data': 'things'}, 'test2': {}}
        result = self.filters.get_filtered_role_resources(service_chain_resources, tripleo_resources)
        self.assertEqual(result, expected_dict)

    def test_get_filtered_resource_chains(self):
        expected_dict = {'name': 'testServiceChain', 'data': 'things'}
        resources = {'test1': {'name': 'testServiceChain', 'data': 'things'}, 'test2': {'name': 'broken'}}
        role_name = 'test'
        result = self.filters.get_filtered_resource_chains(resources, role_name)
        self.assertEqual(result, expected_dict)

    def test_get_filtered_resources(self):
        expected_list = [{'type': 'test::Type', 'data': 'things'}]
        resources = {'test1': {'type': 'test::Type', 'data': 'things'}, 'test2': {'type': 'broken'}}
        filter_value = 'test::Type'
        result = self.filters.get_filtered_resources(resources, filter_value)
        self.assertEqual(result, expected_list)

    def test_get_node_capabilities(self):
        expected_list = [{'uuid': 1, 'hint': 'x'}]
        nodes = [{'id': 1, 'properties': {'capabilities': 'profile:value, cap1:testing, node:x'}}]
        result = self.filters.get_node_capabilities(nodes)
        self.assertEqual(result, expected_list)

    def test_get_node_profile(self):
        expected_list = [{'uuid': 1, 'profile': 'value'}]
        nodes = [{'id': 1, 'properties': {'capabilities': 'profile:value, cap1:testing'}}]
        result = self.filters.get_node_profile(nodes)
        self.assertEqual(result, expected_list)
