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

# flake8: noqa: E501

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import yaml

from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.module_utils.podman.common import run_podman_command
from ansible.module_utils._text import to_bytes, to_native

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
module: podman_container
author:
  - "Sagi Shnaidman (@sshnaidm)"
version_added: '2.9'
short_description: Manage podman containers
notes: []
description:
  - Start, stop, restart and manage Podman containers
requirements:
  - "Podman installed on host"
options:
  name:
    description:
      - Name of the container
    required: True
    type: str
  executable:
    description:
      - Path to C(podman) executable if it is not in the C($PATH) on the
        machine running C(podman)
    default: 'podman'
    type: str
  state:
    description:
      - I(absent) - A container matching the specified name will be stopped and
        removed.
      - I(present) - Asserts the existence of a container matching the name and
        any provided configuration parameters. If no container matches the
        name, a container will be created. If a container matches the name but
        the provided configuration does not match, the container will be
        updated, if it can be. If it cannot be updated, it will be removed and
        re-created with the requested config. Image version will be taken into
        account when comparing configuration. Use the recreate option to force
        the re-creation of the matching container.
      - I(started) - Asserts there is a running container matching the name and
        any provided configuration. If no container matches the name, a
        container will be created and started. Use recreate to always re-create
        a matching container, even if it is running. Use force_restart to force
        a matching container to be stopped and restarted.
      - I(stopped) - Asserts that the container is first I(present), and then
        if the container is running moves it to a stopped state.
    type: str
    default: started
    choices:
      - absent
      - present
      - stopped
      - started
  image:
    description:
      - Repository path (or image name) and tag used to create the container.
        If an image is not found, the image will be pulled from the registry.
        If no tag is included, C(latest) will be used.
      - Can also be an image ID. If this is the case, the image is assumed to
        be available locally.
    type: str
  annotation:
    description:
      - Add an annotation to the container. The format is key value, multiple
        times.
    type: dict
  authfile:
    description:
      - Path of the authentication file. Default is
        ``${XDG_RUNTIME_DIR}/containers/auth.json``
        (Not available for remote commands) You can also override the default
        path of the authentication file by setting the ``REGISTRY_AUTH_FILE``
        environment variable. ``export REGISTRY_AUTH_FILE=path``
    type: str
  blkio_weight:
    description:
      - Block IO weight (relative weight) accepts a weight value between 10 and
        1000
    type: int
  blkio_weight_device:
    description:
      - Block IO weight (relative device weight, format DEVICE_NAME[:]WEIGHT).
    type: dict
  cap_add:
    description:
      - List of capabilities to add to the container.
    type: list
    elements: str
  cap_drop:
    description:
      - List of capabilities to drop from the container.
    type: list
    elements: str
  cgroup_parent:
    description:
      - Path to cgroups under which the cgroup for the container will be
        created.
        If the path is not absolute, the path is considered to be relative to
        the cgroups path of the init process. Cgroups will be created if they
        do not already exist.
    type: str
  cidfile:
    description:
      - Write the container ID to the file
    type: path
  cmd_args:
    description:
      - Any additionl command options you want to pass to podman command,
        cmd_args - ['--other-param', 'value']
        Be aware module doesn't support idempotency if this is set.
    type: list
    elements: str
  conmon_pidfile:
    description:
      - Write the pid of the conmon process to a file.
        conmon runs in a separate process than Podman,
        so this is necessary when using systemd to restart Podman containers.
    type: path
  command:
    description:
      - Override command of container. Can be a string or a list.
    type: raw
  cpu_period:
    description:
      - Limit the CPU real-time period in microseconds
    type: int
  cpu_rt_runtime:
    description:
      - Limit the CPU real-time runtime in microseconds
    type: int
  cpu_shares:
    description:
      - CPU shares (relative weight)
    type: int
  cpus:
    description:
      - Number of CPUs. The default is 0.0 which means no limit.
    type: str
  cpuset_cpus:
    description:
      - CPUs in which to allow execution (0-3, 0,1)
    type: str
  cpuset_mems:
    description:
      - Memory nodes (MEMs) in which to allow execution (0-3, 0,1). Only
        effective on NUMA systems.
    type: str
  detach:
    description:
      - Run container in detach mode
    type: bool
    default: True
  detach_keys:
    description:
      - Override the key sequence for detaching a container. Format is a single
        character or ctrl-value
    type: str
  device:
    description:
      - Add a host device to the container.
        The format is <device-on-host>[:<device-on-container>][:<permissions>]
        (e.g. device /dev/sdc:/dev/xvdc:rwm)
    type: str
  device_read_bps:
    description:
      - Limit read rate (bytes per second) from a device
        (e.g. device-read-bps /dev/sda:1mb)
    type: str
  device_read_iops:
    description:
      - Limit read rate (IO per second) from a device
        (e.g. device-read-iops /dev/sda:1000)
    type: str
  device_write_bps:
    description:
      - Limit write rate (bytes per second) to a device
        (e.g. device-write-bps /dev/sda:1mb)
    type: str
  device_write_iops:
    description:
      - Limit write rate (IO per second) to a device
        (e.g. device-write-iops /dev/sda:1000)
    type: str
  dns:
    description:
      - Set custom DNS servers
    type: list
    elements: str
  dns_option:
    description:
      - Set custom DNS options
    type: str
  dns_search:
    description:
      - Set custom DNS search domains (Use dns_search with '' if you don't wish
        to set the search domain)
    type: str
  entrypoint:
    description:
      - Overwrite the default ENTRYPOINT of the image
    type: str
  env:
    description:
      - Set environment variables.
        This option allows you to specify arbitrary environment variables that
        are available for the process that will be launched inside of the
        container.
    type: dict
  env_file:
    description:
      - Read in a line delimited file of environment variables
    type: path
  etc_hosts:
    description:
      - Dict of host-to-IP mappings, where each host name is a key in the
        dictionary. Each host name will be added to the container's
        ``/etc/hosts`` file.
    type: dict
    aliases:
      - add_hosts
  expose:
    description:
      - Expose a port, or a range of ports (e.g. expose "3300-3310") to set up
        port redirection on the host system.
    type: list
    elements: str
    aliases:
      - exposed
      - exposed_ports
  force_restart:
    description:
      - Force restart of container.
    type: bool
    default: False
    aliases:
      - restart
  gidmap:
    description:
      - Run the container in a new user namespace using the supplied mapping.
    type: str
  group_add:
    description:
      - Add additional groups to run as
    type: str
  healthcheck:
    description:
      - Set or alter a healthcheck command for a container.
    type: str
  healthcheck_interval:
    description:
      - Set an interval for the healthchecks
        (a value of disable results in no automatic timer setup)
        (default "30s")
    type: str
  healthcheck_retries:
    description:
      - The number of retries allowed before a healthcheck is considered to be
        unhealthy. The default value is 3.
    type: int
  healthcheck_start_period:
    description:
      - The initialization time needed for a container to bootstrap.
        The value can be expressed in time format like 2m3s. The default value
        is 0s
    type: str
  healthcheck_timeout:
    description:
      - The maximum time allowed to complete the healthcheck before an interval
        is considered failed. Like start-period, the value can be expressed in
        a time format such as 1m22s. The default value is 30s
    type: str
  hostname:
    description:
      - Container host name. Sets the container host name that is available
        inside the container.
    type: str
  http_proxy:
    description:
      - By default proxy environment variables are passed into the container if
        set for the podman process. This can be disabled by setting the
        http_proxy option to false. The environment variables passed in
        include http_proxy, https_proxy, ftp_proxy, no_proxy, and also the
        upper case versions of those.
        Defaults to true
    type: bool
  image_volume:
    description:
      - Tells podman how to handle the builtin image volumes.
        The options are bind, tmpfs, or ignore (default bind)
    type: str
    choices:
      - 'bind'
      - 'tmpfs'
      - 'ignore'
  init:
    description:
      - Run an init inside the container that forwards signals and reaps
        processes.
    type: str
  init_path:
    description:
      - Path to the container-init binary.
    type: str
  interactive:
    description:
      - Keep STDIN open even if not attached. The default is false.
        When set to true, keep stdin open even if not attached.
        The default is false.
    type: bool
  ip:
    description:
      - Specify a static IP address for the container, for example
        '10.88.64.128'.
        Can only be used if no additional CNI networks to join were specified
        via 'network:', and if the container is not joining another container's
        network namespace via 'network container:<name|id>'.
        The address must be within the default CNI network's pool
        (default 10.88.0.0/16).
    type: str
  ipc:
    description:
      - Default is to create a private IPC namespace (POSIX SysV IPC) for the
        container
    type: str
  kernel_memory:
    description:
      - Kernel memory limit
        (format <number>[<unit>], where unit = b, k, m or g)
    type: str
  label:
    description:
      - Add metadata to a container, pass dictionary of label names and values
    type: dict
  label_file:
    description:
      - Read in a line delimited file of labels
    type: str
  log_driver:
    description:
      - Logging driver. Used to set the log driver for the container.
        For example log_driver "k8s-file".
    type: str
    choices:
      - k8s-file
      - journald
      - json-file
  log_opt:
    description:
      - Logging driver specific options. Used to set the path to the container
        log file. For example log_opt
        "path=/var/log/container/mycontainer.json"
    type: str
    aliases:
      - log_options
  memory:
    description:
      - Memory limit (format 10k, where unit = b, k, m or g)
    type: str
  memory_reservation:
    description:
      - Memory soft limit (format 100m, where unit = b, k, m or g)
    type: str
  memory_swap:
    description:
      - A limit value equal to memory plus swap. Must be used with the -m
        (--memory) flag.
        The swap LIMIT should always be larger than -m (--memory) value.
        By default, the swap LIMIT will be set to double the value of --memory
    type: str
  memory_swappiness:
    description:
      - Tune a container's memory swappiness behavior. Accepts an integer
        between 0 and 100.
    type: int
  mount:
    description:
      - Attach a filesystem mount to the container. bind or tmpfs
        For example mount
        "type=bind,source=/path/on/host,destination=/path/in/container"
    type: str
  network:
    description:
      - Set the Network mode for the container
        * bridge create a network stack on the default bridge
        * none no networking
        * container:<name|id> reuse another container's network stack
        * host use the podman host network stack.
        * <network-name>|<network-id> connect to a user-defined network
        * ns:<path> path to a network namespace to join
        * slirp4netns use slirp4netns to create a user network stack.
          This is the default for rootless containers
    type: str
    aliases:
      - net
  no_hosts:
    description:
      - Do not create /etc/hosts for the container
        Default is false.
    type: bool
  oom_kill_disable:
    description:
      - Whether to disable OOM Killer for the container or not.
        Default is false.
    type: bool
  oom_score_adj:
    description:
      - Tune the host's OOM preferences for containers (accepts -1000 to 1000)
    type: int
  pid:
    description:
      - Set the PID mode for the container
    type: str
  pids_limit:
    description:
      - Tune the container's pids limit. Set -1 to have unlimited pids for the
        container.
    type: str
  pod:
    description:
      - Run container in an existing pod.
        If you want podman to make the pod for you, preference the pod name
        with "new:"
    type: str
  privileged:
    description:
      - Give extended privileges to this container. The default is false.
    type: bool
  publish:
    description:
      - Publish a container's port, or range of ports, to the host.
        Format - ip:hostPort:containerPort | ip::containerPort |
        hostPort:containerPort | containerPort
    type: list
    elements: str
    aliases:
      - ports
      - published
      - published_ports
  publish_all:
    description:
      - Publish all exposed ports to random ports on the host interfaces. The
        default is false.
    type: bool
  read_only:
    description:
      - Mount the container's root filesystem as read only. Default is false
    type: bool
  read_only_tmpfs:
    description:
      - If container is running in --read-only mode, then mount a read-write
        tmpfs on /run, /tmp, and /var/tmp. The default is true
    type: bool
  recreate:
    description:
      - Use with present and started states to force the re-creation of an
        existing container.
    type: bool
    default: False
  restart_policy:
    description:
      - Restart policy to follow when containers exit.
        Restart policy will not take effect if a container is stopped via the
        podman kill or podman stop commands. Valid values are
        * no - Do not restart containers on exit
        * on-failure[:max_retries] - Restart containers when they exit with a
          non-0 exit code, retrying indefinitely
          or until the optional max_retries count is hit
        * always - Restart containers when they exit, regardless of status,
          retrying indefinitely
    type: str
  rm:
    description:
      - Automatically remove the container when it exits. The default is false.
    type: bool
    aliases:
      - remove
  rootfs:
    description:
      - If true, the first argument refers to an exploded container on the file
        system. The dafault is false.
    type: bool
  security_opt:
    description:
      - Security Options. For example security_opt "seccomp=unconfined"
    type: str
  shm_size:
    description:
      - Size of /dev/shm. The format is <number><unit>. number must be greater
        than 0.
        Unit is optional and can be b (bytes), k (kilobytes), m(megabytes), or
        g (gigabytes).
        If you omit the unit, the system uses bytes. If you omit the size
        entirely, the system uses 64m
    type: str
  sig_proxy:
    description:
      - Proxy signals sent to the podman run command to the container process.
        SIGCHLD, SIGSTOP, and SIGKILL are not proxied. The default is true.
    type: bool
  stop_signal:
    description:
      - Signal to stop a container. Default is SIGTERM.
    type: str
  stop_timeout:
    description:
      - Timeout (in seconds) to stop a container. Default is 10.
    type: int
  subgidname:
    description:
      - Run the container in a new user namespace using the map with 'name' in
        the /etc/subgid file.
    type: str
  subuidname:
    description:
      - Run the container in a new user namespace using the map with 'name' in
        the /etc/subuid file.
    type: str
  sysctl:
    description:
      - Configure namespaced kernel parameters at runtime
    type: dict
  systemd:
    description:
      - Run container in systemd mode. The default is true.
    type: bool
  tmpfs:
    description:
      - Create a tmpfs mount. For example tmpfs
        "/tmp" "rw,size=787448k,mode=1777"
    type: dict
  tty:
    description:
      - Allocate a pseudo-TTY. The default is false.
    type: bool
  uidmap:
    description:
      - Run the container in a new user namespace using the supplied mapping.
    type: list
  ulimit:
    description:
      - Ulimit options
    type: list
  user:
    description:
      - Sets the username or UID used and optionally the groupname or GID for
        the specified command.
    type: str
  userns:
    description:
      - Set the user namespace mode for the container.
        It defaults to the PODMAN_USERNS environment variable.
        An empty value means user namespaces are disabled.
    type: str
  uts:
    description:
      - Set the UTS mode for the container
    type: str
  volume:
    description:
      - Create a bind mount. If you specify, volume /HOST-DIR:/CONTAINER-DIR,
        podman bind mounts /HOST-DIR in the host to /CONTAINER-DIR in the
        podman container.
    type: list
    elements: str
    aliases:
      - volumes
  volumes_from:
    description:
      - Mount volumes from the specified container(s).
    type: list
    elements: str
  workdir:
    description:
      - Working directory inside the container.
        The default working directory for running binaries within a container
        is the root directory (/).
    type: str
"""

EXAMPLES = """
- name: Run container
  podman_container:
    name: container
    image: quay.io/bitnami/wildfly
    state: started

- name: Create a data container
  podman_container:
    name: mydata
    image: busybox
    volume:
      - /tmp/data

- name: Re-create a redis container
  podman_container:
    name: myredis
    image: redis
    command: redis-server --appendonly yes
    state: present
    recreate: yes
    expose:
      - 6379
    volumes_from:
      - mydata

- name: Restart a container
  podman_container:
    name: myapplication
    image: redis
    state: started
    restart: yes
    etc_hosts:
        other: "127.0.0.1"
    restart_policy: "no"
    device: "/dev/sda:/dev/xvda:rwm"
    ports:
        - "8080:9000"
        - "127.0.0.1:8081:9001/udp"
    env:
        SECRET_KEY: "ssssh"
        BOOLEAN_KEY: "yes"

- name: Container present
  podman_container:
    name: mycontainer
    state: present
    image: ubuntu:14.04
    command: "sleep 1d"

- name: Stop a container
  podman_container:
    name: mycontainer
    state: stopped

- name: Start 4 load-balanced containers
  podman_container:
    name: "container{{ item }}"
    recreate: yes
    image: someuser/anotherappimage
    command: sleep 1d
  with_sequence: count=4

- name: remove container
  podman_container:
    name: ohno
    state: absent

- name: Writing output
  podman_container:
    name: myservice
    image: busybox
    log_options: path=/var/log/container/mycontainer.json
    log_driver: k8s-file
"""

RETURN = """
container:
    description:
      - Facts representing the current state of the container. Matches the
        podman inspection output.
      - Note that facts are part of the registered vars since Ansible 2.8. For
        compatibility reasons, the facts
        are also accessible directly as C(podman_container). Note that the
        returned fact will be removed in Ansible 2.12.
      - Empty if C(state) is I(absent).
      - If detached is I(False), will include Output attribute containing any
        output from container run.
    returned: always
    type: dict
    sample: '{
        "AppArmorProfile": "",
        "Args": [
            "sh"
        ],
        "BoundingCaps": [
            "CAP_CHOWN",
            ...
        ],
        "Config": {
            "Annotations": {
                "io.kubernetes.cri-o.ContainerType": "sandbox",
                "io.kubernetes.cri-o.TTY": "false"
            },
            "AttachStderr": false,
            "AttachStdin": false,
            "AttachStdout": false,
            "Cmd": [
                "sh"
            ],
            "Domainname": "",
            "Entrypoint": "",
            "Env": [
                "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                "TERM=xterm",
                "HOSTNAME=",
                "container=podman"
            ],
            "Hostname": "",
            "Image": "docker.io/library/busybox:latest",
            "Labels": null,
            "OpenStdin": false,
            "StdinOnce": false,
            "StopSignal": 15,
            "Tty": false,
            "User": {
                "gid": 0,
                "uid": 0
            },
            "Volumes": null,
            "WorkingDir": "/"
        },
        "ConmonPidFile": "...",
        "Created": "2019-06-17T19:13:09.873858307+03:00",
        "Dependencies": [],
        "Driver": "overlay",
        "EffectiveCaps": [
            "CAP_CHOWN",
            ...
        ],
        "ExecIDs": [],
        "ExitCommand": [
            "/usr/bin/podman",
            "--root",
            ...
        ],
        "GraphDriver": {
            ...
        },
        "HostConfig": {
            ...
        },
        "HostnamePath": "...",
        "HostsPath": "...",
        "ID": "...",
        "Image": "...",
        "ImageName": "docker.io/library/busybox:latest",
        "IsInfra": false,
        "LogPath": "/tmp/container/mycontainer.json",
        "MountLabel": "system_u:object_r:container_file_t:s0:c282,c782",
        "Mounts": [
            ...
        ],
        "Name": "myservice",
        "Namespace": "",
        "NetworkSettings": {
            "Bridge": "",
            ...
        },
        "Path": "sh",
        "ProcessLabel": "system_u:system_r:container_t:s0:c282,c782",
        "ResolvConfPath": "...",
        "RestartCount": 0,
        "Rootfs": "",
        "State": {
            "Dead": false,
            "Error": "",
            "ExitCode": 0,
            "FinishedAt": "2019-06-17T19:13:10.157518963+03:00",
            "Healthcheck": {
                "FailingStreak": 0,
                "Log": null,
                "Status": ""
            },
            "OOMKilled": false,
            "OciVersion": "1.0.1-dev",
            "Paused": false,
            "Pid": 4083,
            "Restarting": false,
            "Running": false,
            "StartedAt": "2019-06-17T19:13:10.152479729+03:00",
            "Status": "exited"
        },
        "StaticDir": "..."
            ...
    }'
"""


class PodmanModuleParams:
    """Creates list of arguments for podman CLI command.

       Arguments:
           action {str} -- action type from 'run', 'stop', 'create', 'delete',
                           'start'
           params {dict} -- dictionary of module parameters

       """
    def __init__(self, action, params):
        self.params = params
        self.action = action

    def construct_command_from_params(self):
        """Create a podman command from given module parameters.

        Returns:
           list -- list of byte strings for Popen command
        """
        if self.action in ['start', 'stop', 'delete']:
            return self.start_stop_delete()
        if self.action in ['create', 'run']:
            cmd = [self.action, '--name', self.params['name']]
            all_param_methods = [func for func in dir(self)
                                 if callable(getattr(self, func)) and
                                 func.startswith("addparam")]
            params_set = (i for i in self.params if self.params[i] is not None)
            for param in params_set:
                func_name = "_".join(["addparam", param])
                if func_name in all_param_methods:
                    cmd = getattr(self, func_name)(cmd)
            cmd.append(self.params['image'])
            if self.params['command']:
                if isinstance(self.params['command'], list):
                    cmd += self.params['command']
                else:
                    cmd += self.params['command'].split()
            return [to_bytes(i, errors='surrogate_or_strict') for i in cmd]

    def start_stop_delete(self):

        if self.action in ['stop', 'start']:
            cmd = [self.action, self.params['name']]
            return [to_bytes(i, errors='surrogate_or_strict') for i in cmd]

        if self.action == 'delete':
            cmd = ['rm', '-f', self.params['name']]
            return [to_bytes(i, errors='surrogate_or_strict') for i in cmd]

    def addparam_detach(self, c):
        return c + ['--detach'] if self.params['detach'] else c

    def addparam_etc_hosts(self, c):
        for host_ip in self.params['etc_hosts'].items():
            c += ['--add-host', ':'.join(host_ip)]
        return c

    def addparam_annotation(self, c):
        for annotate in self.params['annotation'].items():
            c += ['--annotation', '='.join(annotate)]
        return c

    def addparam_blkio_weight(self, c):
        return c + ['--blkio-weight', self.params['blkio_weight']]

    def addparam_blkio_weight_device(self, c):
        for blkio in self.params['blkio_weight_device'].items():
            c += ['--blkio-weight-device', ':'.join(blkio)]
        return c

    def addparam_cap_add(self, c):
        for cap_add in self.params['cap_add']:
            c += ['--cap-add', cap_add]
        return c

    def addparam_cap_drop(self, c):
        for cap_drop in self.params['cap_drop']:
            c += ['--cap-drop', cap_drop]
        return c

    def addparam_cgroup_parent(self, c):
        return c + ['--cgroup-parent', self.params['cgroup_parent']]

    def addparam_cidfile(self, c):
        return c + ['--cidfile', self.params['cidfile']]

    def addparam_conmon_pidfile(self, c):
        return c + ['--conmon-pidfile', self.params['conmon_pidfile']]

    def addparam_cpu_period(self, c):
        return c + ['--cpu-period', self.params['cpu_period']]

    def addparam_cpu_rt_runtime(self, c):
        return c + ['--cpu-rt-runtime', self.params['cpu_rt_runtime']]

    def addparam_cpu_shares(self, c):
        return c + ['--cpu-shares', self.params['cpu_shares']]

    def addparam_cpus(self, c):
        return c + ['--cpus', self.params['cpus']]

    def addparam_cpuset_cpus(self, c):
        return c + ['--cpuset-cpus', self.params['cpuset_cpus']]

    def addparam_cpuset_mems(self, c):
        return c + ['--cpuset-mems', self.params['cpuset_mems']]

    def addparam_detach_keys(self, c):
        return c + ['--detach-keys', self.params['detach_keys']]

    def addparam_device(self, c):
        return c + ['--device', self.params['device']]

    def addparam_device_read_bps(self, c):
        return c + ['--device-read-bps', self.params['device_read_bps']]

    def addparam_device_read_iops(self, c):
        return c + ['--device-read-iops', self.params['device_read_iops']]

    def addparam_device_write_bps(self, c):
        return c + ['--device-write-bps', self.params['device_write_bps']]

    def addparam_device_write_iops(self, c):
        return c + ['--device-write-iops', self.params['device_write_iops']]

    def addparam_dns(self, c):
        return c + ['--dns', ','.join(self.params['dns'])]

    def addparam_dns_option(self, c):
        return c + ['--dns-option', self.params['dns_option']]

    def addparam_dns_search(self, c):
        return c + ['--dns-search', self.params['dns_search']]

    def addparam_entrypoint(self, c):
        return c + ['--entrypoint', self.params['entrypoint']]

    def addparam_env(self, c):
        for env_value in self.params['env'].items():
            c += ['--env',
                  b"=".join([to_bytes(k, errors='surrogate_or_strict')
                             for k in env_value])]
        return c

    def addparam_env_file(self, c):
        return c + ['--env-file', self.params['env_file']]

    def addparam_expose(self, c):
        for exp in self.params['expose']:
            c += ['--expose', exp]
        return c

    def addparam_gidmap(self, c):
        return c + ['--gidmap', self.params['gidmap']]

    def addparam_group_add(self, c):
        return c + ['--group-add', self.params['group_add']]

    def addparam_healthcheck(self, c):
        return c + ['--healthcheck', self.params['healthcheck']]

    def addparam_healthcheck_interval(self, c):
        return c + ['--healthcheck-interval',
                    self.params['healthcheck_interval']]

    def addparam_healthcheck_retries(self, c):
        return c + ['--healthcheck-retries',
                    self.params['healthcheck_retries']]

    def addparam_healthcheck_start_period(self, c):
        return c + ['--healthcheck-start-period',
                    self.params['healthcheck_start_period']]

    def addparam_healthcheck_timeout(self, c):
        return c + ['--healthcheck-timeout',
                    self.params['healthcheck_timeout']]

    def addparam_hostname(self, c):
        return c + ['--hostname', self.params['hostname']]

    def addparam_http_proxy(self, c):
        return c + ['--http-proxy', self.params['http_proxy']]

    def addparam_image_volume(self, c):
        return c + ['--image-volume', self.params['image_volume']]

    def addparam_init(self, c):
        return c + ['--init', self.params['init']]

    def addparam_init_path(self, c):
        return c + ['--init-path', self.params['init_path']]

    def addparam_interactive(self, c):
        return c + ['--interactive'] if self.params['interactive'] else c

    def addparam_ip(self, c):
        return c + ['--ip', self.params['ip']]

    def addparam_ipc(self, c):
        return c + ['--ipc', self.params['ipc']]

    def addparam_kernel_memory(self, c):
        return c + ['--kernel-memory', self.params['kernel_memory']]

    def addparam_label(self, c):
        for label in self.params['label'].items():
            c += ['--label', '='.join(label)]
        return c

    def addparam_label_file(self, c):
        return c + ['--label-file', self.params['label_file']]

    def addparam_log_driver(self, c):
        return c + ['--log-driver', self.params['log_driver']]

    def addparam_log_opt(self, c):
        return c + ['--log-opt', self.params['log_opt']]

    def addparam_memory(self, c):
        return c + ['--memory', self.params['memory']]

    def addparam_memory_reservation(self, c):
        return c + ['--memory-reservation', self.params['memory_reservation']]

    def addparam_memory_swap(self, c):
        return c + ['--memory-swap', self.params['memory_swap']]

    def addparam_memory_swappiness(self, c):
        return c + ['--memory-swappiness', self.params['memory_swappiness']]

    def addparam_mount(self, c):
        return c + ['--mount', self.params['mount']]

    def addparam_network(self, c):
        return c + ['--network', self.params['network']]

    def addparam_no_hosts(self, c):
        return c + ['--no-hosts', self.params['no_hosts']]

    def addparam_oom_kill_disable(self, c):
        return c + ['--oom-kill-disable', self.params['oom_kill_disable']]

    def addparam_oom_score_adj(self, c):
        return c + ['--oom-score-adj', self.params['oom_score_adj']]

    def addparam_pid(self, c):
        return c + ['--pid', self.params['pid']]

    def addparam_pids_limit(self, c):
        return c + ['--pids-limit', self.params['pids_limit']]

    def addparam_pod(self, c):
        return c + ['--pod', self.params['pod']]

    def addparam_privileged(self, c):
        return c + ['--privileged'] if self.params['privileged'] else c

    def addparam_publish(self, c):
        for pub in self.params['publish']:
            c += ['--publish', pub]
        return c

    def addparam_publish_all(self, c):
        return c + ['--publish-all', self.params['publish_all']]

    def addparam_read_only(self, c):
        return c + ['--read-only', self.params['read_only']]

    def addparam_read_only_tmpfs(self, c):
        return c + ['--read-only-tmpfs', self.params['read_only_tmpfs']]

    def addparam_restart_policy(self, c):
        return c + ['--restart=%s' % self.params['restart_policy']]

    def addparam_rm(self, c):
        return c + ['--rm'] if self.params['rm'] else c

    def addparam_rootfs(self, c):
        return c + ['--rootfs'] if self.params['rootfs'] else c

    def addparam_security_opt(self, c):
        return c + ['--security-opt', self.params['security_opt']]

    def addparam_shm_size(self, c):
        return c + ['--shm-size', self.params['shm_size']]

    def addparam_sig_proxy(self, c):
        return c + ['--sig-proxy', self.params['sig_proxy']]

    def addparam_stop_signal(self, c):
        return c + ['--stop-signal', self.params['stop_signal']]

    def addparam_stop_timeout(self, c):
        return c + ['--stop-timeout', self.params['stop_timeout']]

    def addparam_subgidname(self, c):
        return c + ['--subgidname', self.params['subgidname']]

    def addparam_subuidname(self, c):
        return c + ['--subuidname', self.params['subuidname']]

    def addparam_sysctl(self, c):
        for sysctl in self.params['sysctl'].items():
            c += ['--sysctl',
                  b"=".join([to_bytes(k, errors='surrogate_or_strict')
                             for k in sysctl])]
        return c

    def addparam_systemd(self, c):
        return c + ['--systemd', self.params['systemd']]

    def addparam_tmpfs(self, c):
        for tmpfs in self.params['tmpfs'].items():
            c += ['--tmpfs', ':'.join(tmpfs)]
        return c

    def addparam_tty(self, c):
        return c + ['--tty'] if self.params['tty'] else c

    def addparam_uidmap(self, c):
        for uidmap in self.params['uidmap']:
            c += ['--uidmap', uidmap]
        return c

    def addparam_ulimit(self, c):
        for u in self.params['ulimit']:
            c += ['--ulimit', u]
        return c

    def addparam_user(self, c):
        return c + ['--user', self.params['user']]

    def addparam_userns(self, c):
        return c + ['--userns', self.params['userns']]

    def addparam_uts(self, c):
        return c + ['--uts', self.params['uts']]

    def addparam_volume(self, c):
        for vol in self.params['volume']:
            if vol:
                c += ['--volume', vol]
        return c

    def addparam_volumes_from(self, c):
        for vol in self.params['volumes_from']:
            c += ['--volumes-from', vol]
        return c

    def addparam_workdir(self, c):
        return c + ['--workdir', self.params['workdir']]

    # Add your own args for podman command
    def addparam_cmd_args(self, c):
        return c + self.params['cmd_args']


def ensure_image_exists(module, image):
    """If image is passed, ensure it exists, if not - pull it or fail.

    Arguments:
        module {obj} -- ansible module object
        image {str} -- name of image

    Returns:
        list -- list of image actions - if it pulled or nothing was done
    """
    image_actions = []
    if not image:
        return image_actions
    rc, out, err = run_podman_command(module, args=['image', 'exists', image],
                                      ignore_errors=True)
    if rc == 0:
        return image_actions
    rc, out, err = run_podman_command(module, args=['image', 'pull', image],
                                      ignore_errors=True)
    if rc != 0:
        module.fail_json(msg="Can't pull image %s" % image, stdout=out,
                         stderr=err)
    image_actions.append("pulled image %s" % image)
    return image_actions


class PodmanContainer:
    """Perform container tasks.

    Manages podman container, inspects it and checks its current state
    """

    def __init__(self, module, name):
        """Initialize PodmanContainer class.

        Arguments:
            module {obj} -- ansible module object
            name {str} -- name of container
        """

        super(PodmanContainer, self).__init__()
        self.module = module
        self.name = name
        self.info = self.get_info()

    @property
    def exists(self):
        """Check if container exists."""
        return bool(self.info != {})

    @property
    def different(self):
        """Check if container is different."""
        # TODO(sshnaidm): implement difference calculation between input vars
        # and current container to understand if we need to recreate it
        return True

    @property
    def running(self):
        """Return True if container is running now."""
        return self.exists and self.info['State']['Running']

    @property
    def stopped(self):
        """Return True if container exists and is not running now."""
        return self.exists and not self.info['State']['Running']

    def get_info(self):
        """Inspect container and gather info about it."""
        rc, out, err = run_podman_command(
            module=self.module,
            args=['container', 'inspect', self.name], ignore_errors=True)
        return json.loads(out)[0] if rc == 0 else {}

    def _perform_action(self, action):
        """Perform action with container.

        Arguments:
            action {str} -- action to perform - start, create, stop, run,
                            delete
        """
        b_command = PodmanModuleParams(action, self.module.params
                                       ).construct_command_from_params()
        self.module.log("PODMAN-CONTAINER-DEBUG: " +
                        "%s" % " ".join([to_native(i) for i in b_command]))
        rc, out, err = run_podman_command(
            module=self.module,
            args=[b'container'] + b_command,
            ignore_errors=True)
        if rc != 0:
            self.module.fail_json(
                msg="Can't %s container %s" % (action, self.name),
                stdout=out, stderr=err)

    def run(self):
        """Run the container."""
        self._perform_action('run')

    def delete(self):
        """Delete the container."""
        self._perform_action('delete')

    def stop(self):
        """Stop the container."""
        self._perform_action('stop')

    def start(self):
        """Start the container."""
        self._perform_action('start')

    def create(self):
        """Create the container."""
        self._perform_action('create')

    def recreate(self):
        """Recreate the container."""
        self.delete()
        self.run()

    def restart(self):
        """Restart the container."""
        self.stop()
        self.run()


class PodmanManager:
    """Module manager class.

    Defines according to parameters what actions should be applied to container
    """

    def __init__(self, module):
        """Initialize PodmanManager class.

        Arguments:
            module {obj} -- ansible module object
        """

        super(PodmanManager, self).__init__()

        self.module = module
        self.results = {
            'changed': False,
            'actions': [],
            'container': {},
        }
        self.name = self.module.params['name']
        self.executable = \
            self.module.get_bin_path(self.module.params['executable'],
                                     required=True)
        self.image = self.module.params['image']
        image_actions = ensure_image_exists(self.module, self.image)
        self.results['actions'] += image_actions
        self.state = self.module.params['state']
        self.restart = self.module.params['force_restart']
        self.recreate = self.module.params['recreate']
        self.container = PodmanContainer(self.module, self.name)

    def update_container_result(self, changed=True):
        """Inspect the current container, update results with last info, exit.

        Keyword Arguments:
            changed {bool} -- whether any action was performed
                              (default: {True})
        """
        facts = self.container.get_info()
        self.results.update({'changed': changed, 'container': facts,
                             'ansible_facts': {'podman_container': facts}})
        self.module.exit_json(**self.results)

    def make_started(self):
        """Run actions if desired state is 'started'."""
        if self.container.running and \
                (self.container.different or self.recreate):
            self.container.recreate()
            self.results['actions'].append('recreated %s' %
                                           self.container.name)
            self.update_container_result()
        elif self.container.running and not self.container.different:
            if self.restart:
                self.container.restart()
                self.results['actions'].append('restarted %s' %
                                               self.container.name)
                self.update_container_result()
            self.module.exit_json(**self.results)
        elif not self.container.exists:
            self.container.run()
            self.results['actions'].append('started %s' % self.container.name)
            self.update_container_result()
        elif self.container.stopped and self.container.different:
            self.container.recreate()
            self.results['actions'].append('recreated %s' %
                                           self.container.name)
            self.update_container_result()
        elif self.container.stopped and not self.container.different:
            self.container.start()
            self.results['actions'].append('started %s' % self.container.name)
            self.update_container_result()

    def make_stopped(self):
        """Run actions if desired state is 'stopped'."""
        if not self.container.exists and not self.image:
            self.module.fail_json(msg='Cannot create container when image' +
                                      ' is not specified!')
        if not self.container.exists:
            self.container.create()
            self.results['actions'].append('created %s' % self.container.name)
            self.update_container_result()
        if self.container.stopped:
            self.update_container_result(changed=False)
        elif self.container.running:
            self.container.stop()
            self.results['actions'].append('stopped %s' % self.container.name)
            self.update_container_result()

    def make_absent(self):
        """Run actions if desired state is 'absent'."""
        if not self.container.exists:
            self.results.update({'changed': False})
        elif self.container.exists:
            self.container.delete()
            self.results['actions'].append('deleted %s' % self.container.name)
            self.results.update({'changed': True})
        self.results.update({'container': {},
                             'ansible_facts': {'podman_container': {}}})
        self.module.exit_json(**self.results)

    def execute(self):
        """Execute the desired action according to map of actions & states."""
        states_map = {
            'present': self.make_started,
            'started': self.make_started,
            'absent': self.make_absent,
            'stopped': self.make_stopped
        }
        process_action = states_map[self.state]
        process_action()
        self.module.fail_json(msg="Unexpected logic error happened, " +
                                  "please contact maintainers ASAP!")


def main():
    module = AnsibleModule(
        argument_spec=yaml.safe_load(DOCUMENTATION)['options'],
        mutually_exclusive=(
            ['no_hosts', 'etc_hosts'],

        ),
    )
    # work on input vars
    if module.params['state'] in ['started', 'present'] and \
            not module.params['image']:
        module.fail_json(msg="State '%s' required image to be configured!" %
                             module.params['state'])

    PodmanManager(module).execute()


if __name__ == '__main__':
    main()
