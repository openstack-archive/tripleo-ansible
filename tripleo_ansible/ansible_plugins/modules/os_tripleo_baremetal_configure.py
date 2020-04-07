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


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.openstack import openstack_module_kwargs
from ansible.module_utils.openstack import openstack_cloud_from_module


DOCUMENTATION = """
---
module: os_tripleo_baremetal_configure
short_description: Configure Baremetal nodes
extends_documentation_fragment: openstack
author:
  - "Dougal Matthews (@d0ugal)"
  - "Kevin Carter (@cloudnull)"
version_added: "2.10"
description:
    - Configure baremetal tripleo node.
options:
    action:
        description:
        - Run a given action on a baremetal node target.
        type: str
        required: true
        choices:
        - baremetal_configure_boot
        - baremetal_configure_root_device
    args:
      description:
      - A set of key=value arguments.
      type: dict
      required: true

requirements: ["openstacksdk"]
"""

EXAMPLES = """
# Invoke baremetal setup
- name: configure boot
  os_tripleo_baremetal_configure:
    cloud: undercloud
    action: baremetal_configure_boot
    args:
        node_uuid: "6d225f94-b385-4ac1-ab23-7581de425127"
        kernel_name: "bm-deploy-kernel"
        ramdisk_name: "bm-deploy-ramdisk"

- name: configure root device
  os_tripleo_baremetal_configure:
    cloud: undercloud
    action: baremetal_configure_root_device
    args:
        node_uuid: "6d225f94-b385-4ac1-ab23-7581de425127"
"""


import os

import yaml

# NOTE(cloudnull): This is still using the legacy clients. We've not
#                  changed to using the OpenStackSDK fully because
#                  tripleo-common expects the legacy clients. Once
#                  we've updated tripleo-common to use the SDK we
#                  should revise this.
from tripleo_common.actions import baremetal
from glanceclient import client as glanceclient
from ironicclient import client as ironicclient
import ironic_inspector_client


class TripleOCommon(object):
    def __init__(self, session):
        self.sess = session

    def baremetal_configure_boot(self, kwargs):
        action = baremetal.ConfigureBootAction(**kwargs)
        baremetal_client = ironicclient.Client(
            1,
            session=self.sess
        )
        image_client = glanceclient.Client(2, session=self.sess)
        return action.configure_boot(
            baremetal_client,
            image_client
        )

    def baremetal_configure_root_device(self, kwargs):
        action = baremetal.ConfigureRootDeviceAction(**kwargs)
        baremetal_client = ironicclient.Client(
            1,
            session=self.sess
        )
        inspector_client = ironic_inspector_client.ClientV1(session=self.sess)
        if not action.root_device:
            return
        else:
            return action.configure_root_device(
                baremetal_client,
                inspector_client
            )


def main():
    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )
    module = AnsibleModule(
        argument_spec,
        **openstack_module_kwargs()
    )

    _, conn = openstack_cloud_from_module(module)
    tripleo = TripleOCommon(session=conn.session)

    if hasattr(tripleo, module.params["action"]):
        action = getattr(tripleo, module.params["action"])
        result = action(
            kwargs=module.params["args"]
        )
        module.exit_json(result=result)
    else:
        module.fail_json(
            msg="Unknown action name {}".format(
                module.params["action"]
            )
        )


if __name__ == "__main__":
    main()
