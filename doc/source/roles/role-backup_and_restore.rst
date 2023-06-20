=========================
Role - backup_and_restore
=========================

.. ansibleautoplugin::
  :role: tripleo_ansible/roles/backup_and_restore

Usage
~~~~~

This Ansible role allows to
do the following tasks:

1. Install an NFS server.
2. Install ReaR.
3. Perform a ReaR backup.


This example is meant to describe a very simple
use case in which the user needs to create a set
of recovery images from the control plane nodes.

First, the user needs to have access to the
environment Ansible inventory.

We will use the *tripleo-ansible-inventory*
command to generate the inventory file.

::

  tripleo-ansible-inventory \
    --ansible_ssh_user heat-admin \
    --static-yaml-inventory ~/tripleo-inventory.yaml

In this particular case, we don't have an additional
NFS server to store the backups from the control plane nodes,
so, we will install the NFS server in the Undercloud node
(but any other node can be used as the NFS storage backend).

First, we need to create an Ansible playbook to
specify that we will install the NFS server in the
Undercloud node.

::

  cat <<'EOF' > ~/bar_nfs_setup.yaml
  # Playbook
  # We will setup the NFS node in the Undercloud node
  # (we don't have any other place at the moment to do this)
  - become: true
    hosts: undercloud
    name: Setup NFS server for ReaR
    roles:
    - role: backup_and_restore
  EOF

Then, we will create another playbook to determine the location
in which we will like to install ReaR.

::

  cat <<'EOF' > ~/bar_rear_setup.yaml
  # Playbook
  # We install and configure ReaR in the control plane nodes
  # As they are the only nodes we will like to backup now.
  - become: true
    hosts: Controller
    name: Install ReaR
    roles:
    - role: backup_and_restore
  EOF

There are cases where the default configuration of ReaR must be customized
for adding extra parameters. These parameters can help to fix restore problems
in the source environments. For instance, if a source environment with an LVM
filesystem has issues in the geometry of the volumes, it is possible to override
how MKFS will behave when formatting the partitions and forcing the tool
to recalculate all the volumes geometry.

In this case, if the `MKFS_XFS_OPTIONS` option is set to `'" "'` it will force
mkfs.xfs to recalculate all the geometry instead of using the data from the
source images.

::

  cat <<'EOF' > ~/bar_rear_setup_custom_configuration.yaml
  # Playbook
  # We install and configure ReaR in the control plane nodes
  # As they are the only nodes we will like to backup now.
  - become: true
    hosts: Controller
    name: Install ReaR
    vars:
      tripleo_backup_and_restore_local_config:
        MKFS_XFS_OPTIONS: '" "'
    roles:
    - role: backup_and_restore
  EOF

Make sure that if you override the `tripleo_backup_and_restore_local_config`
variable you include all the default options and values for all the mandatory
parameters that must be in the local ReaR configuration.

Now we create the playbook to create the actual backup.

::

  cat <<'EOF' > ~/bar_rear_create_restore_images.yaml
  # Playbook
  # We run ReaR in the control plane nodes.
  - become: true
    hosts: ceph_mon
    name: Backup ceph authentication
    tasks:
      - name: Backup ceph authentication role
        include_role:
          name: backup_and_restore
          tasks_from: ceph_authentication
        tags:
        -  bar_create_recover_image

  - become: true
    hosts: Controller
    name: Create the recovery images for the control plane
    roles:
    - role: backup_and_restore
  EOF

The last step is to run the previously create playbooks
filtering by the corresponding tag.

First, we configure the NFS server.

::

  # Configure NFS server in the Undercloud node
  ansible-playbook \
      -v -i ~/tripleo-inventory.yaml \
      --extra="ansible_ssh_common_args='-o StrictHostKeyChecking=no'" \
      --become \
      --become-user root \
      --tags bar_setup_nfs_server \
      ~/bar_nfs_setup.yaml

Then, we install ReaR in the desired nodes.

::

  # Configure ReaR in the control plane
  ansible-playbook \
      -v -i ~/tripleo-inventory.yaml \
      --extra="ansible_ssh_common_args='-o StrictHostKeyChecking=no'" \
      --become \
      --become-user root \
      --tags bar_setup_rear \
      ~/bar_rear_setup.yaml

Lastly, we execute the actual backup step. With or without ceph.

::

  # Create recovery images of the control plane
  ansible-playbook \
      -v -i ~/tripleo-inventory.yaml \
      --extra="ansible_ssh_common_args='-o StrictHostKeyChecking=no'" \
      --become \
      --become-user root \
      --tags bar_create_recover_image \
      ~/bar_rear_create_restore_images.yaml
