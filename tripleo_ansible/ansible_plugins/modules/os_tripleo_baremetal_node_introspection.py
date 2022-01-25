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
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_full_argument_spec
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_module_kwargs
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import openstack_cloud_from_module

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
    log_level:
        description:
        - Set the logging level for the log which is available in the
            returned 'logging' result.
        default: info
        choices:
        - debug
        - info
        - warning
        - error
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
    node_uuids:
      - uuid1
      - uuid2
    concurrency: 10
    max_retries: 1
    node_timeout: 1000

'''

BASE_LOG_MAP = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR
}


def _configure_logging(log_level):
    log_fmt = ('%(asctime)s %(levelname)s %(name)s: %(message)s')
    urllib_level = logging.CRITICAL

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    logging.basicConfig(level=BASE_LOG_MAP[log_level], format=log_fmt,
                        handlers=[handler])
    logging.getLogger('urllib3.connectionpool').setLevel(urllib_level)
    return log_stream


def introspect(cloud, node_uuids, node_timeout, retry_timeout, max_retries,
               concurrency, fetch_data):
    result = {}
    if not node_uuids:
        return result
    introspect_jobs = []

    with futures.ThreadPoolExecutor(max_workers=concurrency) as p:
        for node_uuid in node_uuids:
            introspect_jobs.append(p.submit(
                introspect_node, cloud, node_uuid,
                node_timeout, retry_timeout, max_retries, fetch_data
            ))
    for job in futures.as_completed(introspect_jobs):
        e = job.exception()
        if e:
            # This should not happen, but handle it anyway
            result[node_uuid] = {
                "error": str(e),
                "failed": True,
                "status": 'failed'
            }
            LOG.error('Unexpected error: %s', e)
        else:
            result[node_uuid] = job.result()
    return result


def introspect_node(cloud, node_uuid, node_timeout, retry_timeout,
                    max_retries, fetch_data):
    last_error = None
    attempt = 0
    status = ''

    while attempt <= max_retries:
        attempt += 1

        node = cloud.baremetal.get_node(node_uuid)

        # Put into required state for attempt
        LOG.info("Preparing for attempt %s for node: %s", attempt, node_uuid)
        node = prepare_for_attempt(cloud, node, node_timeout, retry_timeout)

        try:

            # Start introspection
            LOG.info("Introspecting node: %s", node_uuid)
            node = cloud.baremetal.set_node_provision_state(
                node, 'inspect', wait=True, timeout=node_timeout)

            if node.power_state != 'power off':
                # power off the node
                LOG.info('Power off node: %s', node_uuid)
                cloud.baremetal.set_node_power_state(
                    node, 'power off', wait=True, timeout=node_timeout
                )

            if fetch_data:
                # Get the introspection data for the result
                LOG.info("Fetching introspection data: %s", node_uuid)
                status = cloud.baremetal_introspection.get_introspection_data(
                    node_uuid)

            LOG.info("Introspecting node complete: %s", node_uuid)
            # Success
            return {
                'status': status,
                'failed': False,
                'error': None
            }
        except Exception as e:
            last_error = str(e)
            LOG.error("Introspection of node %s failed on attempt %s: "
                      "%s", node_uuid, attempt, last_error)

    message = 'unknown error'
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


def prepare_for_attempt(cloud, node, node_timeout, retry_timeout):

    if node.provision_state not in ('manageable', 'inspect failed'):
        # Attempt to abort any existing introspection
        try:
            LOG.info('Node in state "%s", calling abort: %s',
                     node.provision_state, node.id)
            node = cloud.baremetal.set_node_provision_state(
                node, 'abort', wait=True, timeout=node_timeout)
        except Exception as e:
            LOG.warning("Abort introspection of node %s failed: %s",
                        node.id, str(e))

    if node.power_state != 'power off':
        # Attempt to power off the node
        try:
            LOG.info('Power off node: %s', node.id)
            cloud.baremetal.set_node_power_state(
                node, 'power off', wait=True, timeout=node_timeout
            )
        except Exception as e:
            LOG.warning("Power off of node %s failed: %s",
                        node.id, str(e))

    if node.reservation:
        # Wait until node is unlocked
        try:
            node = cloud.baremetal.wait_for_node_reservation(
                node, timeout=retry_timeout)
        except Exception as e:
            LOG.warning("Waiting for node unlock %s failed: %s",
                        node.id, str(e))
    return node


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
    log_stream = _configure_logging(module.params['log_level'])
    sdk, cloud = openstack_cloud_from_module(module)
    quiet = module.params['quiet']
    failed_nodes = []
    passed_nodes = []
    try:
        result = introspect(
            cloud,
            node_uuids=module.params["node_uuids"],
            node_timeout=module.params["node_timeout"],
            retry_timeout=module.params["retry_timeout"],
            max_retries=module.params["max_retries"],
            concurrency=module.params["concurrency"],
            fetch_data=not quiet)
    except Exception as e:
        # This should not happen, but handle it anyway
        LOG.error('Unexpected error: %s', e)
        module.fail_json(
            msg=str(e),
            failed_nodes=module.params["node_uuids"],
            passed_nodes=[],
            logging=log_stream.getvalue().split('\n')
        )

    for node_uuid, result in result.items():
        if result['failed']:
            failed_nodes.append(node_uuid)
        else:
            passed_nodes.append(node_uuid)

    failed = len(failed_nodes)

    if failed > 0:
        message = ("Introspection completed with failures. %s node(s) failed."
                   % failed)
        module.log("os_tripleo_baremetal_node_introspection ERROR %s" %
                   message)
    else:
        message = "Introspection completed successfully: %s nodes" % len(
            passed_nodes)
        module.log("os_tripleo_baremetal_node_introspection INFO %s" %
                   message)

    module.exit_json(
        changed=True,
        failed=failed > 0,
        introspection_data=result if not quiet else {},
        failed_nodes=failed_nodes,
        passed_nodes=passed_nodes,
        msg=message,
        logging=log_stream.getvalue().split('\n')
    )


if __name__ == "__main__":
    main()
