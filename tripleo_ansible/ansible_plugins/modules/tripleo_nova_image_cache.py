#!/usr/bin/python
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

from __future__ import absolute_import
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_cloud_from_module
from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.openstack import openstack_module_kwargs
import datetime
import hashlib
import os
import tempfile
import time

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: tripleo_nova_image_cache
short_description: Manage Nova image cache on TripleO OpenStack deployment
version_added: "2.0"
author: "Oliver Walsh (@owalsh)"
description:
    - Manage Nova image cache on TripleO OpenStack deployment
options:
    id:
      description:
         - ID of the image to cache
      required: true
    ttl:
      description:
         - Ensure the image remains cached for at least ttl days
      default: 7
    state:
      description:
        - Whether the image be present in cache or expired
          (nova should delete it later if it is no longer used)
      choices: [present, expired]
      default: present
    scp_source:
      description:
        - Attempt to scp the image from this nova-compute host
    scp_continue_on_error:
      description:
        - Fallback to image download if scp fails
      default: false

requirements: ["openstacksdk", "tripleo-common"]
'''

EXAMPLES = '''
- name: Cache image for at least 2 weeks
  tripleo_nova_image_cache:
    id: ec151bd1-aab4-413c-b577-ced089e7d3f8
    ttl: 14

- name: Allow nova to cleanup this image from cache
  tripleo_nova_image_cache:
    id: ec151bd1-aab4-413c-b577-ced089e7d3f8
    state: expired

- name: Cache image, try to copy from existing host
  tripleo_nova_image_cache:
    id: ec151bd1-aab4-413c-b577-ced089e7d3f8
    ttl: 14
    scp_source: nova-compute-0
    scp_continue_on_error: true

'''


def ttl_to_ts(ttl_days):
    """Return a timestamp at midnight UTC ttl_days in the future"""
    epoch = datetime.datetime.utcfromtimestamp(0)
    midnight_today = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0)
    expiry = midnight_today + datetime.timedelta(days=ttl_days+1)
    return (expiry - epoch).total_seconds()


def main():

    argument_spec = openstack_full_argument_spec(
        id=dict(required=True),
        ttl=dict(default=7, type='int', min=1),
        state=dict(default='present', choices=['expired', 'present']),
        _cache_dir=dict(required=True),
        _cache_file=dict(required=True),
        _chunk_size=dict(default=64 * 1024, type='int'),
        _prefetched_path=dict(default=None),
        scp_continue_on_error=dict(default=False, type='bool')
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    image_id = module.params['id']
    cache_dir = module.params['_cache_dir']
    cache_file = module.params['_cache_file']
    chunk_size = module.params['_chunk_size']
    prefetched_path = module.params['_prefetched_path']
    scp_continue = module.params['scp_continue_on_error']

    ttl_days = module.params['ttl']

    result = dict(
        changed=False,
        actions=[],
        image=None,
        cache_file='',
        exists_in_cache=False,
        mtime=0
    )

    sdk, cloud = openstack_cloud_from_module(module, min_version='0.11.3')

    try:
        result['exists_in_cache'] = exists_in_cache = os.path.exists(
            cache_file)
        if exists_in_cache:
            result['cache_file'] = cache_file

        image = cloud.image.find_image(name_or_id=image_id)
        exists_in_glance = image is not None
        if exists_in_glance:
            result['image'] = image.to_dict()

        if module.params['state'] == 'present':
            if not exists_in_cache:

                if not exists_in_glance:
                    module.fail_json(
                        msg="Image not found in glance: %s" % image_id)

                md5 = hashlib.md5()
                if prefetched_path:
                    result['actions'].append({
                        'name': 'Verify pre-fetched image checksum'
                    })
                    with open(prefetched_path, 'rb') as prefetched_image_file:
                        while True:
                            chunk = prefetched_image_file.read(chunk_size)
                            if not chunk:
                                break
                            md5.update(chunk)
                    prefetched_checksum = md5.hexdigest()
                    if prefetched_checksum == image.checksum:
                        result['actions'].append({
                            'name': 'Verify pre-fetched image',
                            'result': True,
                            'expected_md5': image.checksum,
                            'actual_md5': prefetched_checksum
                        })
                        # FIXME: chown to the container nova uid (42436)
                        # until we can run within the container
                        os.chown(prefetched_path, 42436, 42436)
                        os.rename(prefetched_path, cache_file)
                    else:
                        result['actions'].append({
                            'name': 'Verify pre-fetched image',
                            'result': False,
                            'expected_md5': image.checksum,
                            'actual_md5': prefetched_checksum
                        })
                        if not scp_continue:
                            module.fail_json(
                                msg="Pre-fetched image checksum failed")
                        # Ignore it and download direct from glance.
                        # As we did not create it we should not remove it.
                        prefetched_path = ''

                if not prefetched_path:
                    with tempfile.NamedTemporaryFile(
                            'wb',
                            dir=cache_dir,
                            delete=False) as temp_cache_file:
                        try:
                            md5 = hashlib.md5()
                            image_stream = cloud.image.download_image(
                                image,
                                stream=True
                            )
                            try:
                                for chunk in image_stream.iter_content(
                                        chunk_size=chunk_size):
                                    md5.update(chunk)
                                    temp_cache_file.write(chunk)
                            finally:
                                image_stream.close()
                                temp_cache_file.close()

                            download_checksum = md5.hexdigest()
                            if download_checksum != image.checksum:
                                result['actions'].append({
                                    'name': 'Verify downloaded image',
                                    'result': False,
                                    'expected_md5': image.checksum,
                                    'actual_md5': download_checksum
                                })
                                module.fail_json(
                                    msg="Image data does not match checksum")
                            result['actions'].append({
                                'name': 'Verify downloaded image',
                                'result': True,
                                'expected_md5': image.checksum,
                                'actual_md5': download_checksum
                            })

                            # FIXME: chown to the container nova uid (42436)
                            #        until we can run within the container
                            os.chown(temp_cache_file.name, 42436, 42436)
                            os.rename(temp_cache_file.name, cache_file)
                            result['changed'] = True
                        finally:
                            try:
                                os.unlink(temp_cache_file.name)
                            except Exception:
                                pass

            # Set the mtime in the future to prevent nova cleanup
            cache_file_stat = os.stat(cache_file)
            expiry_ts = ttl_to_ts(ttl_days)
            now = time.time()
            if cache_file_stat.st_mtime != expiry_ts:
                os.utime(cache_file, (now, expiry_ts))
                result['actions'].append({
                    'name': 'Update mtime',
                    'from': cache_file_stat.st_mtime,
                    'to': expiry_ts
                })
                result['changed'] = True

        else:  # expired
            if not exists_in_cache:
                result['changed'] = False
            else:
                # Set the mtime to epoch to enable nova cleanup
                now = time.time()
                ts = 0
                cache_file_stat = os.stat(cache_file)
                if cache_file_stat.st_mtime > ts:
                    os.utime(cache_file, (now, ts))
                    result['actions'].append({
                        'name': 'Update mtime',
                        'from': cache_file_stat.st_mtime,
                        'to': ts
                    })
                    result['changed'] = True

                cache_file_stat = os.stat(cache_file)
                result['mtime'] = cache_file_stat.st_mtime
                result['expires'] = time.strftime(
                    "%a, %d %b %Y %H:%M:%S %z",
                    time.localtime(cache_file_stat.st_mtime)
                )

        module.exit_json(**result)

    except sdk.exceptions.OpenStackCloudException as e:
        module.fail_json(msg=str(e), extra_data=e.extra_data)


if __name__ == "__main__":
    main()
