#!/usr/bin/python
# Copyright 2020 Red Hat, Inc.
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

# NOTE: This is still using the legacy clients. We've not
#       changed to using the OpenStackSDK fully because
#       tripleo-common expects the legacy clients. Once
#       we've updated tripleo-common to use the SDK we
#       should revise this.
import os

from heatclient.v1 import client as heatclient
from ironicclient import client as ironicclient

from tripleo_common.utils import heat as tc_heat_utils
from tripleo_common.utils import nodes
from tripleo_common.utils import parameters


class TripleOCommon(object):
    def __init__(self, session):
        self.sess = session
        self.client_cache = dict()

    def get_orchestration_client(self):
        """Return the orchestration (heat) client.

        This method will return a client object using the legacy library. Upon
        the creation of a successful client creation, the client object will
        be stored in the `self.client_cache object`, should this method be
        called more than once, the cached object will automatically return,
        resulting in fewer authentications and faster API interactions.

        :returns: Object
        """

        if 'heatclient' in self.client_cache:
            return self.client_cache['heatclient']
        else:
            if os.environ.get('OS_HEAT_TYPE', '') == 'ephemeral':
                host = os.environ.get('OS_HEAT_HOST', '127.0.0.1')
                port = os.environ.get('OS_HEAT_PORT', 8006)
                self.client_cache['heatclient'] = \
                    tc_heat_utils.local_orchestration_client(host, int(port))
            else:
                self.client_cache['heatclient'] = \
                    heatclient.Client(session=self.sess)
            return self.client_cache['heatclient']

    def get_baremetal_client(self):
        """Return the baremetal (ironic) client.

        This method will return a client object using the legacy library. Upon
        the creation of a successful client creation, the client object will
        be stored in the `self.client_cache object`, should this method be
        called more than once, the cached object will automatically return,
        resulting in fewer authentications and faster API interactions.

        :returns: Object
        """

        if 'ironicclient' in self.client_cache:
            return self.client_cache['ironicclient']
        else:
            self.client_cache['ironicclient'] = \
                ironicclient.Client(
                    1,
                    session=self.sess,
                    os_ironic_api_version='1.36'
                )
            return self.client_cache['ironicclient']
