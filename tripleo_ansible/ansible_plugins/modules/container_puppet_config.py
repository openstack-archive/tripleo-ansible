#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat, Inc.
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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.parsing.convert_bool import boolean
from datetime import datetime

import base64
import copy
import fnmatch
import json
import os
import shutil
import tempfile
import yaml


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: container_puppet_config
author:
  - "Emilien Macchi (@EmilienM)"
version_added: '2.9'
short_description: Generate puppet containers configs
notes: []
description:
  - Generate puppet containers configs
requirements:
  - None
options:
  no_archive:
    description:
      - Disables config-data archiving
    type: bool
    default: True
  check_mode:
    description:
      - Ansible check mode is enabled
    type: bool
    default: False
  config_vol_prefix:
    description:
      - Config volume prefix
    type: str
    default: '/var/lib/config-data'
  debug:
    description:
      - Enable debug
    type: bool
    default: False
  net_host:
    description:
      - Using host network
    type: bool
    default: True
  puppet_config:
    description: Path to the puppet configs
    type: str
    default: ""
  short_hostname:
    description:
      - Short hostname
    type: str
    default: ""
  step:
    description:
      - Step number
    default: 6
    type: int
  update_config_hash_only:
    description:
      - When set to True, the module will only inspect for new config hashes
        in config_vol_prefix and make sure the container-startup-configs
        are updated with these hashes. This is useful to execute
        before we manage the startup containers, so they will be restarted
        if needed (e.g. new config has been applied, container needs
        restart).
    type: bool
    default: False
"""

EXAMPLES = """
- name: Generate puppet container config for step 1
  container_puppet_config:
    step: 1
    puppet_config: /var/lib/container-puppet/container-puppet.json
    short_hostname: "{{ ansible_facts['hostname'] }}"
    update_config_hash_only: false
- name: Update config hashes for container startup configs
  container_puppet_config:
    update_config_hash_only: true
"""

CONTAINER_PUPPET_CONFIG = '/var/lib/tripleo-config/container-puppet-config'
CONTAINER_STARTUP_CONFIG = '/var/lib/tripleo-config/container-startup-config'
CONTAINER_ENTRYPOINT = '/var/lib/container-puppet/container-puppet.sh'


class ContainerPuppetManager:
    """Notes about this module.

    It will generate container config that will be consumed by the
    tripleo-container-manage role that is using podman_container module.
    """

    def __init__(self, module, results):

        super(ContainerPuppetManager, self).__init__()
        self.module = module
        self.results = results

        # parse args
        args = self.module.params

        # Set parameters
        puppet_config = args['puppet_config']
        update_config_hash_only = args['update_config_hash_only']
        self.config_vol_prefix = args['config_vol_prefix']

        if not update_config_hash_only:
            data = json.loads(self._slurp(puppet_config))

            self.step = args['step']
            self.net_host = args['net_host']
            self.debug = args['debug']
            self.check = args['check_mode']
            self.no_archive = args['no_archive']
            self.hostname = args['short_hostname']

            config_path = os.path.join(CONTAINER_PUPPET_CONFIG,
                                       'step_' + str(self.step))

            # Cleanup old configs generated in previous versions
            self._cleanup_old_configs()

            # Make sure config_path exists
            # Note: it'll cleanup old configs before creating new ones.
            self._create_dir(config_path)

            # Generate the container configs
            config = self._get_config(self._merge_volumes_configs(data))
            for k, v in config.items():
                config_dest = os.path.join(config_path, k + '.json')
                self._update_container_config(config_dest, v)

        # Update container-startup-config with new config hashes
        self._update_hashes()

        self.module.exit_json(**self.results)

    def _merge_volumes_configs(self, data):
        """Returns a list of puppet configs with unique config_volume keys.

        :param data: list
        :returns: list

        This method takes in input a list of container puppet configs and
        returns a list of container puppet configs with unique config_volume
        keys. It will allow to run puppet for a single volume at a time and
        avoid the situation where multiple configs using the same config
        volume would run separately; which would cause race condition issues
        because of the rsync commands executed at the end of puppet run.
        To also saves time we support configuring 'shared' services at the same
        time. For example configuring all of the heat services
        in a single container pass makes sense and will save some time.
        To support this we merge shared settings together here.
        We key off of config_volume as this should be the same for a
        given group of services.  We are also now specifying the container
        in which the services should be configured.  This should match
        in all instances where the volume name is also the same.
        """
        returned_dict = {}
        for config in data:
            config_volume = config.get('config_volume')
            if config_volume is None or config_volume == '':
                continue
            puppet_tags = config.get('puppet_tags')
            step_config = config.get('step_config')
            config_image = config.get('config_image')
            volumes = config.get('volumes')
            if config_volume in returned_dict:
                # A config already exists for that config_volume,
                # we'll append puppet_tags and step_config and extend volumes.
                config_image_orig = (
                    returned_dict[config_volume]['config_image']
                )
                if volumes:
                    volumes_orig = (
                        returned_dict[config_volume].get('volumes', [])
                    )
                    volumes_orig.extend(volumes)
                    returned_dict[config_volume]['volumes'] = (
                        sorted(set(volumes_orig))
                    )
                if puppet_tags is not None:
                    returned_dict[config_volume]['puppet_tags'] = '%s,%s' % (
                        returned_dict[config_volume]['puppet_tags'],
                        puppet_tags
                    )
                if step_config is not None:
                    returned_dict[config_volume]['step_config'] = '%s\n%s' % (
                        returned_dict[config_volume]['step_config'],
                        step_config
                    )
                if config_image != config_image_orig:
                    self.module.warn('{} config image does not match with '
                                     '{}'.format(config_image,
                                                 config_image_orig))
            else:
                # This is a new config
                returned_dict[config_volume] = config

        return returned_dict

    def _get_config(self, data):
        """Returns a list of puppet configs per container.

        :param data: list
        :returns: list

        This method takes in input a list of dicts and returns
        a dictionary which match with the podman_container module interface.
        """
        returned_dict = {}
        default_volumes = ['/etc/localtime:/etc/localtime:ro',
                           '/etc/puppet:/tmp/puppet-etc:ro',
                           '/etc/pki/ca-trust/extracted:'
                           '/etc/pki/ca-trust/extracted:ro',
                           '/etc/pki/tls/certs/ca-bundle.crt:'
                           '/etc/pki/tls/certs/ca-bundle.crt:ro',
                           '/etc/pki/tls/certs/ca-bundle.trust.crt:'
                           '/etc/pki/tls/certs/ca-bundle.trust.crt:ro',
                           '/etc/pki/tls/cert.pem:/etc/pki/tls/cert.pem:ro',
                           '%s:/var/lib/config-data'
                           ':rw' % self.config_vol_prefix,
                           '/var/lib/container-puppet/puppetlabs/facter.conf:'
                           '/etc/puppetlabs/facter/facter.conf:ro',
                           '/var/lib/container-puppet/puppetlabs:'
                           '/opt/puppetlabs:ro',
                           '%s:%s:ro' % (CONTAINER_ENTRYPOINT,
                                         CONTAINER_ENTRYPOINT),
                           '/usr/share/openstack-puppet/modules:'
                           '/usr/share/openstack-puppet/modules:ro',
                           '/dev/log:/dev/log:rw']
        # Defaults
        default_data = {
            # the security_opt can be removed once we properly address:
            # https://bugs.launchpad.net/tripleo/+bug/1864501
            'security_opt': ['label=disable'],
            'user': 0,
            # container-puppet shouldn't detach
            'detach': False,
            'entrypoint': CONTAINER_ENTRYPOINT,
            'environment': self._get_environment_config()
        }
        for config_volume, config in data.items():
            cdata = copy.deepcopy(default_data)
            volumes = copy.deepcopy(default_volumes)
            cname = 'container-puppet-' + config_volume
            if self.check:
                volumes += ['/etc/puppet/check-mode:'
                            '/tmp/puppet-check-mode:ro']
            if self.net_host:
                cdata['net'] = ['host']
                volumes += ['/etc/hosts:/etc/hosts:ro']
            else:
                cdata['net'] = ['none']

            cdata['environment']['PUPPET_TAGS'] = (
                self._get_puppet_tags(config))

            cdata['environment']['NAME'] = config_volume
            for k, v in config.items():
                if k == 'config_volume':
                    continue
                if k == 'puppet_tags':
                    continue
                if k == 'step_config':
                    cdata['environment']['STEP_CONFIG'] = v
                    continue
                if k == 'config_image':
                    cdata['image'] = v
                    continue
                if k == 'privileged':
                    cdata['privileged'] = v
                    continue
                if k == 'volumes':
                    if isinstance(v, (list)):
                        volumes.extend(v)
                    else:
                        volumes += [v]
                    continue
                # Keep this one at the very end to override any attribute:
                cdata[k] = v
            cdata['volumes'] = sorted(set(volumes))
            returned_dict[cname] = cdata
        return returned_dict

    def _get_environment_config(self):
        """Returns common environment configs.

        :returns: dict
        """
        returned_env = {
            'STEP': self._get_puppet_step(self.step),
            'NET_HOST': str(self.net_host).lower(),
            'DEBUG': str(self.debug).lower(),
        }
        if self.hostname is not None:
            returned_env['HOSTNAME'] = self.hostname
        if not self.no_archive:
            returned_env['NO_ARCHIVE'] = ''
        else:
            returned_env['NO_ARCHIVE'] = self.no_archive
        return returned_env

    def _get_puppet_step(self, step):
        """Returns the step used by Puppet during a run."

        :param step: integer
        :returns: integer
        """
        # When container_puppet_config is called at step1, it's to initialize
        # configuration files for all services like they were deployed; so
        # in Puppet it means after step5. Which is why we override the step
        # just for the Puppet run.
        # Note that it was the same behavior with container-puppet.py since
        # STEP was set to 6 by default and wasn't overriden when the script
        # was run at step1.
        if step == 1:
            return 6
        return step

    def _get_puppet_tags(self, config):
        """Returns Puppet tags.

        :returns: string
        """
        puppet_tags = 'file,file_line,concat,augeas,cron'
        config_puppet_tags = config.get('puppet_tags')
        if config_puppet_tags is not None:
            puppet_tags += ',%s' % config_puppet_tags
        return puppet_tags

    def _exists(self, path):
        """Returns True if a patch exists.

        :param path: string
        :returns: boolean
        """
        if os.path.exists(path):
            return True

    def _remove_dir(self, path):
        """Remove a directory.

        :param path: string
        """
        if self._exists(path):
            shutil.rmtree(path)

    def _remove_file(self, path):
        """Remove a file.

        :param path: string
        """
        if self._exists(path):
            os.remove(path)

    def _create_dir(self, path):
        """Creates a directory.

        :param path: string
        """
        if self._exists(path):
            self._remove_dir(path)
        os.makedirs(path)

    def _find(self, path, pattern='*.json'):
        """Returns a list of files in a directory.

        :param path: string
        :param pattern: string
        :returns: list
        """
        configs = []
        if self._exists(path):
            for root, dirnames, filenames in os.walk(path):
                for filename in fnmatch.filter(filenames, pattern):
                    configs.append(os.path.join(root, filename))
        else:
            self.module.warn('{} does not exists'.format(path))
        return configs

    def _slurp(self, path):
        """Slurps a file and return its content.

        :param path: string
        :returns: string
        """
        if self._exists(path):
            with open(path, 'r') as f:
                return f.read()
        else:
            self.module.warn('{} was not found.'.format(path))
            return ''

    def _update_container_config(self, path, config):
        """Update a container config.

        :param path: string
        :param config: string
        """
        with open(path, 'wb') as f:
            f.write(json.dumps(config, indent=2).encode('utf-8'))
        os.chmod(path, 0o600)
        self.results['changed'] = True

    def _get_config_hash(self, config_volume):
        """Returns a config hash from a config_volume.

        :param config_volume: string
        :returns: string
        """
        hashfile = "%s.md5sum" % config_volume
        hash_data = ''
        if self._exists(hashfile):
            return self._slurp(hashfile).strip('\n')

    def _get_config_base(self, prefix, volume):
        """Returns a config base path for a specific volume.

        :param prefix: string
        :param volume: string
        :returns: string
        """
        # crawl the volume's path upwards until we find the
        # volume's base, where the hashed config file resides
        path = volume
        base = prefix.rstrip(os.path.sep)
        base_generated = os.path.join(base, 'puppet-generated')
        while path.startswith(prefix):
            dirname = os.path.dirname(path)
            if dirname == base or dirname == base_generated:
                return path
            else:
                path = dirname
        self.module.fail_json(
            msg='Could not find config base for: {} '
                'with prefix: {}'.format(volume, prefix))

    def _match_config_volumes(self, config):
        """Return a list of volumes that match a config.

        :param config: dict
        :returns: list
        """
        # Match the mounted config volumes - we can't just use the
        # key as e.g "novacomute" consumes config-data/nova
        prefix = self.config_vol_prefix
        try:
            volumes = config.get('volumes', [])
        except AttributeError:
            self.module.fail_json(
                msg='Error fetching volumes. Prefix: '
                    '{} - Config: {}'.format(prefix, config))
        return sorted([self._get_config_base(prefix, v.split(":")[0])
                       for v in volumes if v.startswith(prefix)])

    def _update_hashes(self):
        """Update container startup config with new config hashes if needed.
        """
        configs = self._find(CONTAINER_STARTUP_CONFIG)
        for config in configs:
            old_config_hash = ''
            cname = os.path.splitext(os.path.basename(config))[0]
            if cname.startswith('hashed-'):
                # Take the opportunity to cleanup old hashed files which
                # don't exist anymore.
                self._remove_file(config)
                continue
            startup_config_json = json.loads(self._slurp(config))
            config_volumes = self._match_config_volumes(startup_config_json)
            config_hashes = [
                self._get_config_hash(vol_path) for vol_path in config_volumes
            ]
            config_hashes = filter(None, config_hashes)
            if 'environment' in startup_config_json:
                old_config_hash = startup_config_json['environment'].get(
                    'TRIPLEO_CONFIG_HASH', '')
            if config_hashes is not None and config_hashes:
                config_hash = '-'.join(config_hashes)
                if config_hash == old_config_hash:
                    # config doesn't need an update
                    continue
                self.module.debug(
                    'Config change detected for {}, new hash: {}'.format(
                        cname,
                        config_hash
                    )
                )
                if 'environment' not in startup_config_json:
                    startup_config_json['environment'] = {}
                startup_config_json['environment']['TRIPLEO_CONFIG_HASH'] = (
                    config_hash)
                self._update_container_config(config, startup_config_json)

    def _cleanup_old_configs(self):
        """Cleanup old container configurations and directories.
        """
        # This configuration file was removed here:
        # https://review.opendev.org/#/c/702876
        old_config = os.path.join(CONTAINER_STARTUP_CONFIG + '-step_'
                                  + str(self.step) + '.json')
        self._remove_file(old_config)


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        supports_check_mode=True,
    )
    results = dict(
        changed=False
    )
    ContainerPuppetManager(module, results)


if __name__ == '__main__':
    main()
