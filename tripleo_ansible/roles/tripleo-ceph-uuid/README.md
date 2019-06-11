Ansible Role to gather node UUIDs for node-specfic overrides
============================================================

Populates the host_vars of the ceph-ansible working directory,
as provided by the tripleo-ceph-work-dir role, by mapping each
hostname to its UUID. The UUID is determined by running the
`dmidecode -s system-uuid` command on each node with Ansible.
This role creates and executes its own playbook. This role
sets up the host_vars directory used by ceph-ansible so
that TripleO's "node specific overrides" can be used to
override a particular parameter for only a subset of hosts.
The most popular usecase for this role is to pass a different
list of block devices to be used as OSDs for a subset of servers
which differ from the majority of servers.

Requirements
------------

None

Role Variables
--------------

None

Dependencies
------------

- tripleo-ceph-common
- tripleo-ceph-work-dir
