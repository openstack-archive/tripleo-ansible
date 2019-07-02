Ansible Role to manage the exectution of ceph-ansible from within TripleO
=========================================================================

Executes playbooks from ceph-ansible using parameters from TripleO.

After the working directory is created by the tripleo-ceph-work-dir
role and the working directory has been populated with host_vars
mapping node specific overrides by the tripleo-ceph-uuid role, and
after the fetch directory is populated with context from previous
ceph-ansible runs, by the tripleo-ceph-fetch-dir role, the playbooks
from ceph-ansible may be executed.

This role creates the shell script ceph_ansible_command.sh within
the ceph-ansible working directory and then executes the shell script.
If the shell script's return is non-zero, the deployment fails and an
error message from ansible is displayed.

After this role is used, the tasks from backup_and_clean.yml from the
tripleo-ceph-work-dir role should be used to persist the ceph-ansible
fetch directory and then remove it so that future runs of ceph-ansible
by this role do not have permissions issues when the role is used by a
different user.

Requirements
------------

None

Role Variables
--------------

- ceph_ansible_playbooks_param: the list of ceph-ansible playbooks to
  be run; e.g. ['/usr/share/ceph-ansible/site-container.yml.sample'])
  is the default but any item in ceph-ansible/infrastructure-playbooks
  may be passed. If the list contains more than one item, each
  playbook is executed sequentially.

Dependencies
------------

- tripleo-ceph-common
- tripleo-ceph-work-dir
- tripleo-ceph-fetch-dir
- tripleo-ceph-uuid
