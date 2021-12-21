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


Ironic Usage
~~~~~~~~~~~~

This Ansible role gets the most of the ironic/metallsmitch
service on the Undercloud to automate the restoration of
the nodes.

1. Install an NFS server as a data backup.
2. Install an NFS server on the Undercloud.
3. Install and configure ReaR.
4. Perform a ReaR backup.
5. Restore a Node.


Firstly, the user needs to have access to the
environment Ansible inventory.

We will use the *tripleo-ansible-inventory*
command to generate the inventory file.

::

  tripleo-ansible-inventory \
    --stack overcloud \
    --ansible_ssh_user heat-admin \
    --static-yaml-inventory ~/tripleo-inventory.yaml


Secondly, we need to create an Ansible playbook to
specify that we will install the NFS server in the
Undercloud node.

::

  cat <<'EOF' > ~/bar_nfs_setup.yaml
  # Playbook
  # We will setup the NFS node in the Undercloud node
  # (we don't have any other place at the moment to do this)
  - become: true
    hosts: backupServer
    name: Setup NFS server for ReaR
    roles:
    - role: backup_and_restore
  EOF


Then, we need to install and configure the NFS server.

::

  # Install and Configure NFS server node
  ansible-playbook \
      -v -i ~/tripleo-inventory.yaml \
      --extra="ansible_ssh_common_args='-o StrictHostKeyChecking=no'" \
      --become \
      --become-user root \
      --tags bar_setup_nfs_server \
      ~/bar_nfs_setup.yaml


The Undercloud needs to be configured to integrate ReaR with
Ironic. The first step is the creation of the playbook.

::

  cat <<'EOF' > ~/prepare-undercloud-pxe.yaml
  ---
  - name: TripleO PXE installation and configuration.
    hosts: Undercloud
    become: true
    vars:
      tripleo_backup_and_restore_shared_storage_folder: "{{ tripleo_backup_and_restore_ironic_images_path }}"
      tripleo_backup_and_restore_shared_storage_subfolders: ["pxelinux.cfg"]
    roles:
      - role: backup_and_restore
  EOF

After the playbook is created, let's execute ansible to apply the changes.

::

  ansible-playbook \
      -v -i ~/tripleo-inventory.yaml \
      --extra="ansible_ssh_common_args='-o StrictHostKeyChecking=no'" \
      --become \
      --become-user root \
      --tags bar_setup_nfs_server \
      ~/prepare-undercloud-pxe.yaml

Now, the overcloud nodes need to be configured. As before firstly the
playbook is created.

::

  cat <<'EOF' > ~cli-overcloud-conf-ironic.yaml
  ---
  - name: Get Undercloud data
    hosts: Undercloud
    tasks:
      - name: Get networking
        setup:
          gather_subset: network
        tags:
          - never

  - name: TripleO Ironic ReaR installation and configuration on Overcloud
    hosts: Controller
    become: true
    vars:
      tripleo_backup_and_restore_pxe_output_url: "nfs://{{ hostvars['undercloud']['ansible_facts']['br_ctlplane']['ipv4']['address'] }}{{ tripleo_backup_and_restore_ironic_images_path }}"
      tripleo_backup_and_restore_local_config:
        OUTPUT: PXE
        OUTPUT_PREFIX_PXE: $HOSTNAME
        BACKUP: NETFS
        PXE_RECOVER_MODE: '"unattended"'
        PXE_CREATE_LINKS: '"IP"'
        USE_STATIC_NETWORKING: y
        PXE_CONFIG_GRUB_STYLE: y
        KERNEL_CMDLINE: '"unattended"'
        POST_RECOVERY_SCRIPT: poweroff
        USER_INPUT_TIMEOUT: "10"
        PXE_TFTP_URL: "{{ tripleo_backup_and_restore_pxe_output_url }}"
        BACKUP_URL: "{{ tripleo_backup_and_restore_backup_url }}"
        PXE_CONFIG_URL: "{{ tripleo_backup_and_restore_pxe_output_url }}/pxelinux.cfg"
    roles:
      - role: backup_and_restore
  EOF

Install and configure ReaR on the overcloud controller nodes. If the nodes are using OVS,
ReaR does not know how to configure the network so the
tripleo_backup_and_restore_network_preparation_commands needs to be configure.

::

  ansible-playbook \
      -v -i tripleo-inventory.yaml \
      --extra="ansible_ssh_common_args='-o StrictHostKeyChecking=no'" \
      --become \
      --become-user root \
      --tags bar_setup_rear \
      ~/cli-overcloud-conf-ironic.yaml \
      -e "tripleo_backup_and_restore_network_preparation_commands=\"('ip l a br-ex type bridge' 'ip l s ens3 up' 'ip l s br-ex up' 'ip l s ens3 master br-ex' 'dhclient br-ex')\""


There are some playbooks that can be used to perform a backup of the nodes.

::

  ansible-playbook \
      -v -i ~/tripleo-inventory.yaml \
      --extra="ansible_ssh_common_args='-o StrictHostKeyChecking=no'" \
      --become \
      --become-user root \
      --tags bar_create_recover_image \
      /usr/share/ansible/tripleo-playbooks/cli-overcloud-backup.yaml


In the same way to Restore a node there is also a playbook to achieve it.
The tripleo_backup_and_restore_overcloud_restore_name is the name, uuid or
hostname of the node that is going to be restored.

::

  ansible-playbook \
      -v -i tripleo-inventory.yaml \
      /usr/share/ansible/tripleo-playbooks/cli-overcloud-restore-node.yml \
      -e "tripleo_backup_and_restore_overcloud_restore_name=control-0"
