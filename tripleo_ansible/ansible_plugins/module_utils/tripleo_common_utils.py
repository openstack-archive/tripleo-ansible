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

from glanceclient import client as glanceclient
from heatclient.v1 import client as heatclient
from ironicclient import client as ironicclient
from novaclient import client as novaclient
from swiftclient import client as swift_client

from tripleo_common.utils import heat as tc_heat_utils
from tripleo_common.utils import nodes
from tripleo_common.utils import parameters

import ironic_inspector_client


class DeriveParamsError(Exception):
    """Error while performing a derive parameters operation"""


class TripleOCommon(object):
    def __init__(self, session):
        self.sess = session
        self.client_cache = dict()

    def get_ironic_inspector_client(self):
        """Return the ironic inspector client.

        This method will return a client object using the legacy library. Upon
        the creation of a successful client creation, the client object will
        be stored in the `self.client_cache object`, should this method be
        called more than once, the cached object will automatically return,
        resulting in fewer authentications and faster API interactions.

        :returns: Object
        """

        if 'ironic_inspector_client' in self.client_cache:
            return self.client_cache['ironic_inspector_client']
        else:
            self.client_cache['ironic_inspector_client'] = \
                ironic_inspector_client.ClientV1(session=self.sess)
            return self.client_cache['ironic_inspector_client']

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

    def get_compute_client(self):
        """Return the compute (nova) client.

        This method will return a client object using the legacy library. Upon
        the creation of a successful client creation, the client object will
        be stored in the `self.client_cache object`, should this method be
        called more than once, the cached object will automatically return,
        resulting in fewer authentications and faster API interactions.

        :returns: Object
        """

        if 'novaclient' in self.client_cache:
            return self.client_cache['novaclient']
        else:
            self.client_cache['novaclient'] = \
                novaclient.Client(version=2, session=self.sess)
            return self.client_cache['novaclient']

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

    def get_image_client(self):
        """Return the image (glance) client.

        This method will return a client object using the legacy library. Upon
        the creation of a successful client creation, the client object will
        be stored in the `self.client_cache object`, should this method be
        called more than once, the cached object will automatically return,
        resulting in fewer authentications and faster API interactions.

        :returns: Object
        """

        if 'glanceclient' in self.client_cache:
            return self.client_cache['glanceclient']
        else:
            self.client_cache['glanceclient'] = \
                glanceclient.Client(
                    2,
                    session=self.sess
                )
            return self.client_cache['glanceclient']

    def get_object_client(self):
        """Return the object (swift) client.

        This method will return a client object using the legacy library. Upon
        the creation of a successful client creation, the client object will
        be stored in the `self.client_cache object`, should this method be
        called more than once, the cached object will automatically return,
        resulting in fewer authentications and faster API interactions.

        :returns: Object
        """

        if 'swift_client' in self.client_cache:
            return self.client_cache['swift_client']
        else:
            self.client_cache['swift_client'] = swift_client.Connection(
                session=self.sess,
                retries=10,
                starting_backoff=3,
                max_backoff=120
            )
            return self.client_cache['swift_client']

    def return_introspected_node_data(self, node_id):
        """Return baremetal data from the ironic inspector.

        :param node_id: Node UUID
        :type node_id: String

        :returns: Object
        """

        client = self.get_ironic_inspector_client()
        return client.get_data(node_id=node_id)

    def return_flavor_profile(self, flavor_name):
        """Return flavor profile information.

        :param flavor_name: Flavor name
        :type flavor_name: String

        :returns: Object
        """

        return parameters.get_profile_of_flavor(
            flavor_name=flavor_name,
            compute_client=self.get_compute_client()
        )
