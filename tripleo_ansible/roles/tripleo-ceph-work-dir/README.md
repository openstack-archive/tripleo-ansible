Ansible Role to manage a ceph-ansible working directory
=======================================================

The aim of this role and its supporting roles is to automate steps
that a ceph-ansible user normally does manually so that TripleO
may complete these steps for the user before and after ceph-ansible
runs.

Creates a directory within config-download called "ceph-ansible"
which contains the following contents, which are prerequisites
for ceph-ansible to be used:

- group_vars directory
- host_vars directory
- an inventory with the host groups ceph-ansible expects
- an extra_vars.yml file

The group_vars directory will be populated with the file all.yml which
contains content from the ceph_ansible_group_vars_all variable.
Additional files in group_vars will be populated by config-download
external_deploy_tasks Ansible embdeded directly in TripleO Heat
Templates.

The host_vars directory will be populated for each host based on
that host's UUID by the tripleo-ceph-uuid role.

The extra_vars.yml file will be populated with content from the
ceph_ansible_extra_vars variable.

This role also crecates an empty fetch_directory within the work
directory but the tripleo-ceph-fetch-dir role should be used to
populate and persist this fecth directory before the tripleo-run-
ceph-ansible role is used.

Requirements
------------

None

Role Variables
--------------

- ceph_ansible_group_vars_all: map containing all variables typically
  found in ceph-ansible/group_vars/all.yml.

- ceph_ansible_extra_vars: map containing all variables the user
  wishes to pass to the ceph-ansible run using 'ansible-playbook
  --extra-vars @extra_vars.yml'

- ceph_ansible_private_key_file: The private SSH key that ceph-ansible
  will use to connect to the nodes it will configure. (defaults to the
  config-download "{{ playbook_dir }}/ssh_private_key")

Dependencies
------------

- tripleo-ceph-common
