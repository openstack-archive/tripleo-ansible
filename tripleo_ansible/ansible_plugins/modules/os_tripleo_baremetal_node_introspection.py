#!/usr/bin/python
# Copyright (c) 2019 OpenStack Foundation
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
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: os_tripleo_baremetal_node_introspection
short_description: Introspect Ironic nodes
extends_documentation_fragment: openstack
author:
  - "Dougal Matthews"
  - "Sagi Shnaidman"
version_added: "2.10"
description:
    - Requests Ironic for nodes info.
options:
    ironic_url:
      description:
        - If noauth mode is utilized, this is required to be set to the
          endpoint URL for the Ironic API.
          Use with "auth" and "auth_type" settings set to None.
      type: str
      required: False
    node_uuids:
      description:
        - node_uuids
      type: list
      required: True
    concurrency:
      description:
        - concurrency
      type: int
      default: 20
    max_retries:
      description:
        - max_retries
      type: int
      default: 2
    node_timeout:
      description:
        - node_timeout
      type: int
      default: 1200
    quiet:
      description:
        - Don't provide instrospection info in output of the module
      type: bool
      default: False
'''

RETURN = '''
introspection_data:
    description: Dictionary of new facts representing introspection data of
                 nodes.
    returned: changed
    type: dict
    sample: {
        "400b3cd0-d134-417b-8f0e-63e273e01e5a": {
            "failed": false,
            "retries": 0,
            "status": {
                "error": null,
                "finished_at": "2019-11-22T01:09:07",
                "id": "400b3cd0-d134-417b-8f0e-63e273e01e5a",
                "is_finished": true,
                "links": [
                    {
                        "href": "http://192.168.24.2:13050 .... ",
                        "rel": "self"
                    }
                ],
                "location": {
                    "cloud": "undercloud",
                    "project": {
                        "domain_id": null,
                        "domain_name": "Default",
                        "id": "......",
                        "name": "admin"
                    },
                    "region_name": "regionOne",
                    "zone": null
                },
                "name": null,
                "started_at": "2019-11-22T01:07:32",
                "state": "finished"
            }
        }
    }
'''

EXAMPLES = '''
# Invoke node introspection

- os_tripleo_baremetal_node_introspection:
    cloud: undercloud
    auth: password
    node_uuids:
      - uuid1
      - uuid2
    concurrency: 10
    max_retries: 1
    node_timeout: 1000

'''

import time
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.openstack import openstack_module_kwargs
from ansible.module_utils.openstack import openstack_cloud_from_module


class IntrospectionManagement(object):
    def __init__(self,
                 cloud,
                 module,
                 concurrency,
                 max_retries,
                 node_timeout):
        self.client = cloud.baremetal_introspection
        self.module = module
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.node_timeout = node_timeout

    def log(self, msg):
        self.module.log("os_tripleo_baremetal_node_introspection: %s" % msg)

    def push_next(self, pool, queue):
        try:
            next_introspection = next(queue)
            pool.append(next_introspection)
        except StopIteration:
            pass
        return pool

    def introspect(self, node_uuids):

        result = {}
        queue = (NodeIntrospection(
            uuid,
            self.client,
            self.node_timeout,
            self.max_retries,
            self.log) for uuid in node_uuids)
        pool = []

        for i in range(self.concurrency):
            pool = self.push_next(pool, queue)

        while len(pool) > 0:
            finished = []
            for intro in pool:
                if not intro.started:
                    try:
                        intro.start_introspection()
                        continue
                    except Exception as e:
                        self.log("ERROR Node %s can't start introspection"
                                 " because: %s" % (intro.node_id, str(e)))
                        result[intro.node_id] = {
                            "error": "Error for introspection node %s: %s " % (
                                intro.node_id, str(e)),
                            "failed": True,
                            "status": ''
                        }
                        finished.append(intro)
                        continue
                status = intro.get_introspection()
                if (not status.is_finished and intro.timeouted()) or (
                    status.is_finished and status.error is not None
                ):
                    if status.is_finished:
                        self.log("ERROR Introspection of node %s "
                                 "failed: %s" % (
                                     status.id, str(status.error))
                                 )
                    if intro.last_retry():
                        result[status.id] = (intro.error_msg()
                                             if status.is_finished
                                             else intro.timeout_msg())
                        finished.append(intro)
                    else:
                        intro.restart_introspection()
                if status.is_finished and status.error is None:
                    result[status.id] = {
                        'status': intro.get_introspection_data(),
                        'failed': False,
                        'error': None}
                    finished.append(intro)
            for i in finished:
                pool.remove(i)
                pool = self.push_next(pool, queue)
            # Let's not DDOS Ironic service
            if pool:
                time.sleep(min(10, self.node_timeout))

        return result


class NodeIntrospection:
    started = False

    def __init__(self, node_id, os_client, timeout, max_retries, log):
        self.node_id = node_id
        self.os_client = os_client
        self.timeout = timeout
        self.max_retries = max_retries
        self.log = log
        self.start = int(time.time())
        self.retries = 0
        self.last_status = None

    def restart_introspection(self):
        self.retries += 1
        try:
            self.os_client.abort_introspection(self.node_id)
        except Exception as e:
            # Node is locked
            self.log("ERROR Node %s can't abort introspection: %s" % (
                self.node_id, str(e)))
            return
        # need to wait before restarting introspection till it's aborted
        # to prevent hanging let's use introspect timeout for that
        try:
            self.os_client.wait_for_introspection(
                self.node_id, timeout=self.timeout, ignore_error=True)
        except Exception as e:
            self.log("ERROR Node %s can't restart introspection because can't "
                     "abort it: %s" % (self.node_id, str(e)))
            return
        self.start = int(time.time())
        return self.start_introspection(restart=True)

    def start_introspection(self, restart=False):
        self.started = True
        if restart:
            self.log("INFO Restarting (try %s of %s) introspection of "
                     "node %s" % (
                         self.retries, self.max_retries, self.node_id))
        else:
            self.log("INFO Starting introspection of node %s" % (self.node_id))
        return self.os_client.start_introspection(self.node_id)

    def get_introspection(self):
        self.last_status = self.os_client.get_introspection(self.node_id)
        return self.last_status

    def get_introspection_data(self):
        self.log(
            "Instrospection of node %s finished successfully!" % self.node_id)
        return self.os_client.get_introspection_data(self.node_id)

    def time_elapsed(self):
        return int(time.time()) - self.start

    def timeouted(self):
        return self.time_elapsed() > self.timeout

    def last_retry(self):
        return self.retries >= self.max_retries

    def timeout_msg(self):
        self.log(
            "ERROR Retry limit %s reached for introspection "
            "node %s: exceeded timeout" % (
                self.max_retries, self.node_id))
        return {"error": "Timeout error for introspection node %s: %s "
                         "sec exceeded max timeout of %s sec" % (
                             self.node_id, self.time_elapsed(), self.timeout),
                "failed": True,
                "status": self.last_status
                }

    def error_msg(self):
        self.log(
            "ERROR Retry limit %s reached for introspection "
            "node %s: %s" % (
                self.max_retries, self.node_id, self.last_status.error))
        return {"error": "Error for introspection node %s: %s " % (
            self.node_id, self.last_status.error),
            "failed": True,
            "status": self.last_status
        }


def main():
    argument_spec = openstack_full_argument_spec(
        **yaml.safe_load(DOCUMENTATION)['options']
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(
        argument_spec,
        supports_check_mode=False,
        **module_kwargs
    )
    auth_type = module.params.get('auth_type')
    ironic_url = module.params.get('ironic_url')
    if auth_type in (None, 'None'):
        if not ironic_url:
            module.fail_json(
                msg="Authentication appears to be disabled,"
                    " Please define an ironic_url parameter"
            )
        else:
            module.params['auth'] = {'endpoint': ironic_url}

    _, cloud = openstack_cloud_from_module(module)

    introspector = IntrospectionManagement(
        cloud,
        module,
        module.params["concurrency"],
        module.params["max_retries"],
        module.params["node_timeout"]
    )
    module_results = {"changed": True}
    result = introspector.introspect(module.params["node_uuids"])
    failed_nodes = [k for k, v in result.items() if v['failed']]
    passed_nodes = [k for k, v in result.items() if not v['failed']]
    failed = len(failed_nodes)
    if failed > 0:
        message = ("Introspection completed with failures. %s node(s) failed."
                   % failed)
        module.log("os_tripleo_baremetal_node_introspection ERROR %s" %
                   message)
        module_results.update({'failed': True})
    else:
        message = "Introspection completed successfully: %s nodes" % len(
            module.params["node_uuids"])
        module.log("os_tripleo_baremetal_node_introspection INFO %s" %
                   message)

    module_results.update({
        "introspection_data": result if not module.params['quiet'] else {},
        "failed_nodes": failed_nodes,
        "passed_nodes": passed_nodes,
        "msg": message
    })
    module.exit_json(**module_results)


if __name__ == "__main__":
    main()
