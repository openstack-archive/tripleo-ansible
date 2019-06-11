Ansible Role to manage a ceph-ansible fetch directory
=====================================================

When scaling Ceph monitors, ceph-ansible uses context from the
fetch_directory to prevent new monitors from trying to bootstrap
a new Ceph cluster

This role saves the fetch_directory to either Swift or a local
directory after each ceph-ansible playbook run; and if there is
a backup of fetch directory in Swift or the specificied local
directory, restores it before each ceph-ansible playbook run.

The main.yml does not include the backup_and_clean.yml because
that should be run separately as a post task as needed by a
separate import using tasks_from.

Requirements
------------

None

Role Variables
--------------

- ceph_ansible_tarball_name: The name of the file which will contain a
  tar.gz backup of the ceph-ansible fetch directory. Used for both the
  local and swift backup methods. (default: 'temporary_dir.tar.gz')

- old_ceph_ansible_tarball_name: The name of the file which will be
  saved in /tmp when the ceph-ansible fetch directory is downloaded
  from Swift. Not used for local backups and only used for
  Swift backups. (default: 'temporary_dir_old.tar.gz')

- new_ceph_ansible_tarball_name: The name of the file which will be
  saved in /tmp after ceph-ansible runs and then uploaded to Swift.
  Not used for local backups only only used for Swift backups.
  (default: 'temporary_dir_new.tar.gz')


Dependencies
------------

- tripleo-ceph-common
- tripleo-ceph-work-dir
