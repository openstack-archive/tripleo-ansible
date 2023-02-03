==========================
Role - snapshot_and_revert
==========================

.. ansibleautoplugin::
  :role: tripleo_ansible/roles/snapshot_and_revert

Usage
~~~~~

This Ansible role allows to
do the following tasks:

1. Take LVM snapshots in both the Controller and Compute nodes.
2. Revert the state to the previously created snapshots.
3. Remove the snapshots.

LVM snapshots are a feature of Linux Logical Volume Manager (LVM)
that allows users to create a temporary, read-only copy of a
the logical volumes of the Overcloud nodes.
The copy is a point-in-time representation of the original volume
and can be used for various purposes like data backup, testing, and recovery.
The ext4 file system must be used on top of LVM logical volumes, otherwise
this feature can not be used.

This example is meant to describe a very simple
use case in which the user needs to create a set
of recovery LVM snapshots from the Controller and Compute nodes.

Login in the Undercloud node and run:

::

  # Create snapshots in the Compute and Controller nodes
  openstack overcloud backup snapshot

To revert the snapshots run:

::

  # Revert snapshots in the Compute and Controller nodes
  openstack overcloud backup snapshot --revert

Then, to remove the created snapshots run:

::

  # Remove snapshots in the Controller and Compute nodes
  openstack overcloud backup snapshot --remove
