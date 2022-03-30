==============================
Role - tripleo-systemd-wrapper
==============================

An Ansible role to manage systemd wrappers in TripleO.


What it does
------------

In a nutshell, this role helps to configure systemd so it manages side car
containers (e.g. dnsmasq, HAproxy, keepalived, etc, requested by Neutron
agents).

Underneath, this role creates four files:

- /etc/systemd/system/<service>.path

This file will allow the host to monitor changes to
/var/lib/<service>/<service>-processes-timestamp which keeps track of the
service processes in a text file.
<service>-processes-timestamp file is managed by the <service>-wrapper script
with a flock to avoid race conditions.

- /etc/systemd/system/<service>.service

This file is the SystemD service that will run the synchronization of
processes. It is run as "Type=oneshot" because we just want the unit to execute
the <service>-process-sync script without keeping active processes.
In this Ansible role, we automatically enable and start this service.

- /var/lib/<service>/<service>/wrapper

Script that wrap the service lifecycle management. It takes care of starting
the side containers everytime the service is called.
Because it's a wrapper, the script has to be bind mounted from the host into
the container.

e.g.: /var/lib/neutron/neutron-dnsmasq/wrapper:/usr/local/bin/dnsmasq:ro

So in the case of Neutron DHCP agent, when an operator will create a network,
Neutron will call dnsmasq which will actually call our side container wrapper.

- /var/lib/neutron/<service>/process-sync

This script helps to keep the list of processes (side containers) up to date,
so we don't create more than one container per namespace. We use flock to avoid
a race condition if at the same time the wrapper is called. The flock protects
the list of processes and also the timestamps.


Requirements
------------

It requires systemd on the host. This role isn't designed nor tested to run
within a container.

Role variables
--------------

- tripleo_systemd_wrapper_cmd: -- Command to run in the container.
- tripleo_systemd_wrapper_config_bind_mount: -- Bind-mount used for container config.
- tripleo_systemd_wrapper_container_cli: -- Name of the container cli command to use (podman | docker).
- tripleo_systemd_wrapper_docker_additional_sockets: -- Additional docker sockets to use when interacting with docker
- tripleo_systemd_wrapper_image_name: -- Container image name.
- tripleo_systemd_wrapper_service_dir: -- Directory where state files will be created.
- tripleo_systemd_wrapper_service_kill_script: -- Name of the script to create for the kill action
- tripleo_systemd_wrapper_service_name: -- Name of the service to wrap in Systemd.

Example Playbook
----------------

Sample playbook to call the role::

  - name: Create Neutron dnsmasq systemd wrapper
    hosts: all
    roles:
      - tripleo-systemd-wrapper
    vars:
      tripleo_systemd_wrapper_cmd: "/usr/sbin/dnsmasq -k"
      tripleo_systemd_wrapper_config_bind_mount: "/var/lib/config-data/puppet-generated/neutron/etc/neutron:/etc/neutron:ro"
      tripleo_systemd_wrapper_container_cli: podman
      tripleo_systemd_wrapper_image_name: "quay.io/tripleomastercentos9/centos-binary-neutron-dhcp-agent:current-tripleo"
      tripleo_systemd_wrapper_service_dir: /var/lib/neutron
      tripleo_systemd_wrapper_service_kill_script: dnsmasq-kill
      tripleo_systemd_wrapper_service_name: neutron-dnsmasq


.. ansibleautoplugin::
  :role: tripleo_ansible/roles/tripleo-systemd-wrapper
