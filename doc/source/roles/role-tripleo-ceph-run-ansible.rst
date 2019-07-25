===============================
Role - tripleo-ceph-run-ansible
===============================

.. ansibleautoplugin::
   :role: tripleo_ansible/roles/tripleo-ceph-run-ansible


Required test arguments
~~~~~~~~~~~~~~~~~~~~~~~

+--------------------------+-------------------------------------------------+
| Environment Variable     | Variable Value                                  |
+==========================+=================================================+
| TRIPLEO_JOB_ANSIBLE_ARGS | '--skip-tags=run_uuid_ansible,run_ceph_ansible' |
+--------------------------+-------------------------------------------------+
