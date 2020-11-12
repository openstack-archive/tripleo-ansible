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

from concurrent import futures
import io
import logging
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_cloud_from_module
from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.openstack import openstack_module_kwargs

LOG = logging.getLogger('os_tripleo_baremetal_node_introspection')

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
    retry_timeout:
      description:
        - How much time to wait for node to be unlocked before introspection
          retry
      type: int
      default: 120
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


def _configure_logging():
    log_fmt = ('%(asctime)s %(levelname)s %(name)s: %(message)s')
    urllib_level = logging.CRITICAL

    base_level = logging.INFO

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    logging.basicConfig(level=base_level, format=log_fmt,
                        handlers=[handler])
    logging.getLogger('urllib3.connectionpool').setLevel(urllib_level)
    return log_stream


def introspect(cloud, node_uuids, node_timeout, retry_timeout, max_retries,
               concurrency):
    result = {}
    if not node_uuids:
        return result
    introspect_jobs = []

    with futures.ThreadPoolExecutor(max_workers=concurrency) as p:
        for node_uuid in node_uuids:
            introspect_jobs.append(p.submit(
                introspect_node, cloud, node_uuid,
                node_timeout, retry_timeout, max_retries
            ))
        for job in futures.as_completed(introspect_jobs):
            result[node_uuid] = job.result()
    return result


def introspect_node(cloud, node_uuid, node_timeout, retry_timeout,
                    max_retries):
    last_error = None
    attempt = 0

    while attempt <= max_retries:
        attempt += 1

        # Attempt cleanup from previous error
        if last_error:
            LOG.info("Preparing for retry %s for node: %s", attempt, node_uuid)
            prepare_for_retry(cloud, node_uuid, node_timeout, retry_timeout)

        try:
            LOG.info("Introspecting node: %s", node_uuid)

            # Start introspection
            cloud.baremetal.set_node_provision_state(
                node_uuid, 'inspect', wait=True, timeout=node_timeout)

            # Power off the node
            cloud.baremetal.set_node_power_state(
                node_uuid, 'power off', wait=True, timeout=node_timeout
            )

            # Wait for the node lock to be released
            cloud.baremetal.wait_for_node_reservation(
                node_uuid, timeout=node_timeout
            )

            # Get the introspection data for the result
            data = cloud.baremetal_introspection.get_introspection_data(
                node_uuid)

            LOG.info("Introspecting node complete: %s", node_uuid)
            # Success
            return {
                'status': data,
                'failed': False,
                'error': None
            }
        except Exception as e:
            last_error = str(e)
            LOG.error("Introspection of node %s failed on attempt %s: "
                      "%s", node_uuid, attempt, last_error)

    message = 'unknown error'
    status = ''
    # All attempts failed, fetch node to get the reason
    try:
        node = cloud.baremetal.get_node(node_uuid)
        message = node.last_error
        status = node.provision_state
    except Exception:
        if last_error:
            # Couldn't fetch the node, use the last exception message instead
            message = last_error

    return {
        "error": "Error for introspection node %s on attempt %s: %s " %
                 (node_uuid, attempt, message),
        "failed": True,
        "status": status
    }


def prepare_for_retry(cloud, node_uuid, node_timeout, retry_timeout):
    # Attempt to abort any existing introspection
    try:
        cloud.baremetal.set_node_provision_state(
            node_uuid, 'abort', wait=True, timeout=node_timeout)
    except Exception as e:
        LOG.warn("Abort introspection of node %s failed: %s",
                 node_uuid, str(e))

    # Attempt to power off the node
    try:
        cloud.baremetal.set_node_power_state(
            node_uuid, 'off', wait=True, timeout=node_timeout
        )
    except Exception as e:
        LOG.warn("Power off of node %s failed: %s",
                 node_uuid, str(e))

    # Wait until node is unlocked
    try:
        cloud.baremetal.wait_for_node_reservation(
            node_uuid, timeout=retry_timeout)
    except Exception as e:
        LOG.warn("Waiting for node unlock %s failed: %s",
                 node_uuid, str(e))


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

    log_stream = _configure_logging()

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

    result = introspect(
        cloud,
        node_uuids=module.params["node_uuids"],
        node_timeout=module.params["node_timeout"],
        retry_timeout=module.params["retry_timeout"],
        max_retries=module.params["max_retries"],
        concurrency=module.params["concurrency"])
    module_results = {"changed": True}

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
        "msg": message,
        "logging": log_stream.getvalue().split('\n')
    })
    module.exit_json(**module_results)


if __name__ == "__main__":
    main()
