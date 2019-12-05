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
        result = self.filters.haskey(batched_container_data=data,
                                     attribute='restart', value='always')
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
        result = self.filters.haskey(batched_container_data=data,
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
        result = self.filters.haskey(batched_container_data=data,
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
        result = self.filters.haskey(batched_container_data=data,
                                     attribute='restart',
                                     reverse=True,
                                     any=True)
        self.assertEqual(result, expected_list)

    def test_needs_delete(self):
        data = [
            {
                'Name': 'mysql',
                'Config': {
                    'Labels': {
                        'config_id': 'dontdeleteme',
                        'managed_by': 'triple_ansible',
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
                        'name': 'rabbitmq',
                    }
                }
            },
            {
                'Name': 'swift',
                'Config': {
                    'Labels': {
                        'managed_by': 'tripleo_ansible',
                        'config_id': 'tripleo_step1',
                        'container_name': 'swift',
                        'name': 'swift',
                        'config_data': 'foo',
                    }
                }
            },
            {
                'Name': 'haproxy',
                'Config': {
                    'Labels': {
                        'config_id': 'test'
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
                    'Labels': None,
                }
            },
        ]
        config = {
            'mysql': '',
            'rabbitmq': '',
            'haproxy': '',
            'tripleo': '',
            'doesnt_exist': ''
        }
        expected_list = ['rabbitmq']
        result = self.filters.needs_delete(container_infos=data,
                                           config=config,
                                           config_id='tripleo_step1')
        self.assertEqual(result, expected_list)
