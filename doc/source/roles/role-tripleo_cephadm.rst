======================
Role - tripleo_cephadm
======================

.. ansibleautoplugin::
  :role: tripleo_ansible/roles/tripleo_cephadm

About
~~~~~

An Ansible role for TripleO integration with Ceph clusters deployed with
`cephadm`_ and managed with Ceph `orchestrator`_.

This role is provided as part of the implementation of the `tripleo_ceph_spec`_.
It is an Ansible wrapper to call the Ceph tools `cephadm`_ and `orchestrator`_
and it contains the Ansible module `ceph_key`_ from `ceph-ansible`_.

Assumptions
~~~~~~~~~~~

- This role assumes it has an inventory with a single host, known as the
  `bootstrap_host`. An inventory genereated by `tripleo-ansible-inventory`
  will have a `mons` group so the first node in this group is a good
  candidate for this host.

- The `cephadm`_ binary must be installed on the `bootstrap_host`.

- Though there only needs to be one Ceph node in the inventory `cephadm`_
  will configure the other servers with SSH. Thus, the following playbook
  should be run before one which uses this role to configure the `ceph-admin`
  user on the overcloud with the SSH keys that `cephadm`_ requires.

  .. code-block:: bash

      ansible-playbook -i $INV \
        tripleo-ansible/tripleo_ansible/playbooks/cli-enable-ssh-admin.yaml \
        -e @ceph-admin.yml

  Where `ceph-admin.yml` contains something like the following:

  .. code-block:: YAML

      ---
      tripleo_admin_user: ceph-admin
      ssh_servers: "{{ groups['mons'] }}"
      distribute_private_key: true

  The `ssh_servers` variable should be expanded to contain another other nodes
  hosting Ceph, e.g. `osds`.

- A `cephadm-spec`_ file should be provided which references the Ceph services
  to be run on the other `ssh_hosts`.  The path to this file can be set with
  the `ceph_spec` variable.

Usage
~~~~~

Here is an example of a playbook which bootstraps the first Ceph monitor
and then applies a spec file to add other hosts. It then creates RBD pools
for Nova, Cinder, and Glance and a cephx keyring called `openstack` to access
those pools. It then creates a file which can be passed as input to the role
`tripleo_ceph_client` so that an overcloud can be configured to use the deployed
Ceph cluster.

.. code-block:: YAML

    - name: Deploy Ceph with cephadm
      hosts: mons[0]
      vars:
        bootstrap_host: "{{ groups['mons'][0] }}"
        tripleo_cephadm_spec_on_bootstrap: false
        pools:
          - vms
          - volumes
          - images
      tasks:
        - name: Satisfy Ceph prerequisites
          import_role:
            role: tripleo_cephadm
            tasks_from: pre

        - name: Bootstrap Ceph
          import_role:
            role: tripleo_cephadm
            tasks_from: bootstrap

        - name: Apply Ceph spec
          import_role:
            role: tripleo_cephadm
            tasks_from: apply_spec
          when: not tripleo_cephadm_spec_on_bootstrap

        - name: Create Pools
          import_role:
            role: tripleo_cephadm
            tasks_from: pools

        - name: Create Keys
          import_role:
            role: tripleo_cephadm
            tasks_from: keys

        - name: Export configuration for tripleo_ceph_client
          import_role:
            role: tripleo_cephadm
            tasks_from: export
          vars:
            cephx_keys:
              - client.openstack


.. _tripleo_ceph_spec: https://specs.openstack.org/openstack/tripleo-specs/specs/wallaby/tripleo-ceph.html
.. _cephadm: https://docs.ceph.com/en/latest/cephadm/
.. _orchestrator: https://docs.ceph.com/en/latest/mgr/orchestrator/
.. _ceph_key: https://github.com/ceph/ceph-ansible/blob/master/library/ceph_key.py
.. _ceph-ansible: https://github.com/ceph/ceph-ansible/
.. _cephadm-spec: https://tracker.ceph.com/issues/44205
