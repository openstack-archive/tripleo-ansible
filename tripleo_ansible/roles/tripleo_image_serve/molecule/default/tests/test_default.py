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


import os

import testinfra.utils.ansible_runner


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_package_installed(host):
    assert host.package("httpd").is_installed


def test_image_serve_conf_exists(host):
    assert host.file("/etc/httpd/conf.d/image-serve.conf").exists


def test_image_serve_dir_exists(host):
    assert host.file("/var/lib/image-serve").exists


def test_httpd_running(host):
    assert host.service("httpd").is_running


def test_httpd_enabled(host):
    assert host.service("httpd").is_enabled
