#!/usr/bin/env python
# Copyright 2019 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from collections import OrderedDict
from operator import itemgetter


class FilterModule(object):
    def filters(self):
        return {
            'singledict': self.singledict,
            'subsort': self.subsort
        }

    def subsort(self, dict_to_sort, attribute, null_value=None):
        """Sort a hash from a sub-element.

        This filter will return a sorted list of tuples from a dictionary
        using an attribute from within the hash. If the sort attribute is
        undefined it will be set in the returned item as the defined
        `null_value`. This makes it possible to sort all items equally.
        """
        for k, v in dict_to_sort.items():
            if attribute not in v:
                dict_to_sort[k][attribute] = null_value

        return sorted(
            dict_to_sort.items(),
            key=lambda x: x[1][attribute]
        )

    def singledict(self, list_to_convert):
        """Generate a single dictionary from a list of dictionaries.

        This filter will return a single dictionary from a list of
        dictionaries.
        """
        return_dict = {}
        for i in list_to_convert:
            return_dict.update(i)
        return return_dict
