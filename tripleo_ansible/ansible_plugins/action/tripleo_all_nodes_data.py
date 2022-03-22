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


DOCUMENTATION = """
---
module: tripleo_all_nodes_data
author:
  - James Slagle (@slagle) <jslagle@redhat.com>
version_added: '2.8'
short_description: Renders the all_nodes data for TripleO as group_vars
notes: []
description:
  - This module renders the all_nodes data for TripleO as group_vars which are
    then available on overcloud nodes.
options:
  forks:
    description:
      - The number of forks to spawn in parallel to compute the data for each
        service. Defaults to the forks set for ansible.
    required: False
"""

EXAMPLES = """
- name: Render all_nodes data
  tripleo_all_nodes_data:
"""


import json
from multiprocessing import Manager, Process
import os
import traceback

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase

try:
    from ansible_collections.ansible.utils.plugins.filter import ipaddr
except ImportError:
    from ansible_collections.ansible.netcommon.plugins.filter import ipaddr

from ansible.utils.display import Display


DISPLAY = Display()


class ActionModule(ActionBase):
    """Renders the all_nodes data for TripleO as group_vars"""

    def compute_service(self, service, all_nodes):
        DISPLAY.vv("Processing {}".format(service))

        # <service>_enabled: true
        all_nodes[service + '_enabled'] = True

        # <service>_node_ips: <list of ips>
        DISPLAY.vv("  Computing data for {}_node_ips".format(service))
        service_network = self.service_net_map.get(
            service + '_network', 'ctlplane')
        service_hosts = self.groups.get(service, [])
        service_node_ips = list(
            map(lambda host: self.h_vars[host][service_network + '_ip'],
                service_hosts))
        for extra_node_ip in self.all_nodes_extra_map_data.get(
                service + '_node_ips', []):
            if extra_node_ip not in service_node_ips:
                service_node_ips.append(extra_node_ip)
        all_nodes[service + '_node_ips'] = service_node_ips

        if self.nova_additional_cell:
            # <service>_cell_node_names: <list of hostnames>
            v = service_network + '_hostname'
            service_cell_node_names = \
                list(map(lambda host: self.h_vars[host][v],
                         service_hosts))
            all_nodes[service + '_cell_node_names'] = \
                service_cell_node_names
        else:
            # <service>_node_names: <list of hostnames>
            DISPLAY.vv("  Computing data for {}_node_names".format(service))
            v = service_network + '_hostname'
            service_node_names = \
                list(map(lambda host: self.h_vars[host][v],
                         service_hosts))
            for extra_node_name in self.all_nodes_extra_map_data.get(
                    service + '_node_names', []):
                if extra_node_name not in service_node_names:
                    service_node_names.append(extra_node_name)
            all_nodes[service + '_node_names'] = service_node_names

        # <service>_short_node_names: <list of hostnames>
        DISPLAY.vv("  Computing data for {}_short_node_names".format(service))
        service_short_node_names = \
            list(map(lambda host: self.h_vars[host]['inventory_hostname'],
                     service_hosts))
        for extra_short_node_name in self.all_nodes_extra_map_data.get(
                service + '_short_node_names', []):
            if extra_short_node_name not in service_node_names:
                service_short_node_names.append(extra_short_node_name)
        all_nodes[service + '_short_node_names'] = \
            service_short_node_names

        # <service>_short_bootstrap_node_name: hostname
        DISPLAY.vv("  Computing data for {}_short_bootstrap_node_name".format(service))
        if self.all_nodes_extra_map_data.get(
                service + '_short_bootstrap_node_name', None):
            v = service + '_short_bootstrap_node_name'
            service_hosts += self.all_nodes_extra_map_data[v]
        service_hosts.sort()
        if service_hosts:
            all_nodes[service + '_short_bootstrap_node_name'] = \
                service_hosts[0]

        # <service>_bootstrap_node_ip: hostname
        DISPLAY.vv("  Computing data for {}_short_bootstrap_node_ip".format(service))
        if self.all_nodes_extra_map_data.get(
                service + '_bootstrap_node_ip', None):
            v = service + '_bootstrap_node_ip'
            service_bootstrap_node_ips = \
                service_node_ips.append(self.all_nodes_extra_map_data[v])
        else:
            service_bootstrap_node_ips = service_node_ips
        if service_bootstrap_node_ips:
            all_nodes[service + '_bootstrap_node_ip'] = \
                service_bootstrap_node_ips[0]

    def process_services(self, enabled_services, all_nodes, forks):
        # This breaks up the enabled_services list into smaller lists with
        # length equal to the number of forks.
        enabled_services_length = len(enabled_services)
        for i in range(0, enabled_services_length, forks):
            # It would be nice to be able to use multiprocessing.Pool here,
            # however, that resulted in many pickle errors.
            # For each smaller list, spawn a process to compute each service in
            # that chunk.
            end = i + forks
            if end > enabled_services_length:
                end = enabled_services_length
            processes = [Process(target=self.compute_service,
                                 args=(enabled_services[x], all_nodes))
                         for x in range(i, end)]
            [p.start() for p in processes]
            [p.join() for p in processes]
            [p.terminate() for p in processes]

    def compute_all_nodes(self, all_nodes, task_vars):
        DISPLAY.vv("Starting compute and render for all_nodes data")
        # Internal Ansible objects for inventory and variables
        inventory = self._task.get_variable_manager()._inventory
        self.groups = inventory.get_groups_dict()
        # host_vars
        self.h_vars = self._task.get_variable_manager().get_vars()['hostvars']

        # Needed tripleo variables for convenience
        self.service_net_map = task_vars['service_net_map']
        self.nova_additional_cell = task_vars['nova_additional_cell']
        self.all_nodes_extra_map_data = task_vars['all_nodes_extra_map_data']
        service_vip_vars = task_vars.get('service_vip_vars', {})
        net_vip_map = task_vars['net_vip_map']
        enabled_services = task_vars['enabled_services']
        primary_role_name = task_vars['primary_role_name']

        enabled_services += self.all_nodes_extra_map_data.get(
            'enabled_services', [])
        # make enabled_services unique and sorted
        enabled_services = list(set(enabled_services))
        enabled_services.sort()

        all_nodes['enabled_services'] = enabled_services

        forks = self._task.args.get('forks', task_vars['ansible_forks'])
        DISPLAY.vv("forks set to {}".format(forks))
        self.process_services(enabled_services, all_nodes, forks)

        # <service>: service_network
        DISPLAY.vv("Computing data for service_net_map")
        for key, value in self.service_net_map.items():
            all_nodes[key] = value

        # all values from all_nodes_extra_map_data when nova_additional_cell
        if self.nova_additional_cell:
            for key, value in self.all_nodes_extra_map_data.items():
                all_nodes[key] = value

        # redis_vip: ip
        DISPLAY.vv("Computing data for redis_vip")
        if 'redis' in enabled_services or self.nova_additional_cell:
            if 'redis_vip' in self.all_nodes_extra_map_data:
                all_nodes['redis_vip'] = self.all_nodes_extra_map_data['redis_vip']
            elif 'redis' in service_vip_vars:
                all_nodes['redis_vip'] = service_vip_vars['redis']
            elif 'redis' in net_vip_map:
                all_nodes['redis_vip'] = net_vip_map['redis']

        # ovn_dbs_vip: ip
        DISPLAY.vv("Computing data for ovn_dbs_vip")
        if 'ovn_dbs' in enabled_services or self.nova_additional_cell:
            if 'ovn_dbs_vip' in self.all_nodes_extra_map_data:
                all_nodes['ovn_dbs_vip'] = \
                    self.all_nodes_extra_map_data['ovn_dbs_vip']
            elif 'ovn_dbs' in service_vip_vars:
                all_nodes['ovn_dbs_vip'] = service_vip_vars['ovn_dbs']
            elif 'ovn_dbs' in net_vip_map:
                all_nodes['ovn_dbs_vip'] = net_vip_map['ovn_dbs']

        DISPLAY.vv("Computing data for top level vars")
        all_nodes['deploy_identifier'] = task_vars['deploy_identifier']
        all_nodes['container_cli'] = task_vars['container_cli']

        # controller_node_<ips/names>
        # note that these are supposed to be strings, not lists
        DISPLAY.vv("Computing data for controller node ips/names")
        primary_hosts = self.groups.get(primary_role_name, [])
        all_nodes['controller_node_ips'] = \
            ','.join(list(map(lambda host: self.h_vars[host]['ctlplane_ip'],
                              primary_hosts)))
        all_nodes['controller_node_names'] = \
            ','.join(list(map(lambda host: self.h_vars[host]['inventory_hostname'],
                              primary_hosts)))

        DISPLAY.vv("Done")

    def run(self, tmp=None, task_vars=None):
        """Renders the all_nodes data for TripleO as group_vars"""

        manager = Manager()
        all_nodes = manager.dict()
        try:
            self.compute_all_nodes(all_nodes, task_vars)

            all_nodes = dict(all_nodes)
            all_nodes_path = os.path.join(task_vars['playbook_dir'],
                                          'group_vars', 'overcloud.json')
            with open(all_nodes_path, 'w') as f:
                DISPLAY.vv("Rendering all_nodes to {}".format(all_nodes_path))
                json.dump(all_nodes, f, sort_keys=True, indent=4)
        except Exception as e:
            DISPLAY.error(traceback.format_exc())
            raise AnsibleError(str(e))
        finally:
            manager.shutdown()
            # multiprocessing can hang the plugin exit if there are still
            # references to the Manager() object. Even though we have called
            # .shutdown(), clean up all_nodes just to be safe.
            all_nodes = None

        DISPLAY.vv("returning")
        return dict(all_nodes=all_nodes)
