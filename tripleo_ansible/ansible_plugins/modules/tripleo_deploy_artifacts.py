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
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import os
import subprocess
import traceback
import urllib.request
import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}


DOCUMENTATION = '''
---
module: tripleo_deploy_artifacts
short_description: Deploy RPM/tar.gz artifact from a URL on a system
version_added: "2.9"
author: "Alex Schultz (@mwhahaha)"
description:
  - Takes a set of urls as inputs, fetches their contents and deploys them
    on the system.
options:
  artifact_urls:
    description:
      - List of artifact urls to deploy
    required: true
    type: list
'''

RETURN = '''
'''

EXAMPLES = '''
- name: Deploy artifacts
  tripleo_deploy_artifacts:
    artifact_urls:
      - http://example.com/foo.rpm
      - http://example.com/foo.tar.gz
'''


def _get_filetype(filename):
    cmd = "file -b " + filename
    try:
        r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True)
    except Exception as e:
        raise Exception('Unable to determine file type: %s' & e)
    if 'RPM' in r.stdout:
        return 'rpm'
    elif 'gzip compressed data' in r.stdout:
        return 'targz'
    return 'UNKNOWN'


def deploy_rpm(filename):
    rpm_filename = filename + '.rpm'
    cmd = "dnf install -y " + rpm_filename
    try:
        os.rename(filename, rpm_filename)
        _ = subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE,
                           universal_newlines=True)
    except Exception as e:
        raise Exception('Unable to install rpm: %s' % e)
    finally:
        if os.path.exists(rpm_filename):
            os.unlink(rpm_filename)


def deploy_targz(filename):
    cmd = "tar xvz -C / -f " + filename
    try:
        _ = subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE,
                           universal_newlines=True)
    except Exception as e:
        raise Exception('Unable to install tar.gz: %s' % e)
    finally:
        if os.path.exists(filename):
            os.unlink(filename)


def run(module):
    results = dict(
        changed=False
    )

    args = module.params
    urls = args.get('artifact_urls')
    tmpfile = None

    # run command
    for url in urls:
        try:
            (tmpfile, _) = urllib.request.urlretrieve(url)
            filetype = _get_filetype(tmpfile)
            if filetype == 'rpm':
                deploy_rpm(tmpfile)
            elif filetype == 'targz':
                deploy_targz(tmpfile)
            else:
                results['failed'] = True
                results['error'] = 'Invalid file format'
                results['msg'] = ('Unable to determine file format for %s' %
                                  url)
                break
            results['changed'] = True
        except Exception as e:
            results['failed'] = True
            results['error'] = traceback.format_exc()
            results['msg'] = "Unhandled exception: %s" % e
            break
        finally:
            if tmpfile and os.path.exists(tmpfile):
                os.unlink(tmpfile)

    module.exit_json(**results)


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=False,
    )
    run(module)


if __name__ == '__main__':
    main()
