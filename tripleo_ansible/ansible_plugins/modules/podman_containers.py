#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat, Inc.
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

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: podman_containers
author:
  - "Sagi Shnaidman (@sshnaidm)"
version_added: '2.9'
short_description: Manage podman containers in a batch
notes: []
description:
  - Manage groups of podman containers
requirements:
  - "Podman installed on host"
options:
  containers:
    description:
      - List of dictionaries with data for running containers
        for podman_container module.
    required: True
    type: list
    elements: dict
'''

EXAMPLES = '''
- name: Run three containers at once
  podman_containers:
    containers:
      - name: alpine
        image: alpine
        command: sleep 1d
      - name: web
        image: nginx
      - name: test
        image: python:3-alpine
        command: python -V
'''
