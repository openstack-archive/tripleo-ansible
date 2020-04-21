=====================================
Role - tripleo-redhat-enforce
=====================================

.. ansibleautoplugin::
  :role: tripleo_ansible/roles/tripleo-redhat-enforce

Description
~~~~~~~~~~~

This role is for OSP, the downstream version of tripleo and shouldn't
be used with other OS as it required the host to be subscribed.

It enforces policies regarding rhel version and subscribed channel
according to the OSP version used.

This module hosts those requirements, so that we prevent update to
wrong rhel release or subscription to wrong channels.

Currently it only implements a basic check to the subscribed rhel
version.

This check has some fail-safe logic to avoid crashing the update on
temporary network issue when running subscription-manager.

We are avoiding the validation framework as this can be easily
disabled and we want this enforcement to be mandatory as this could
lead user to unsupported combination of OSP/RHEL.

For upstream that change is transparent as the tasks are skipped if
the ansible_distribution is not Red Hat.

Usage
~~~~~

Very simple usage, just pass the right parameter for the version you
plan to check.

Remember this won't have any effects on anything else than a Red Hat
subscribed host.

.. code-block:: YAML

    - name: Enforce RHOSP rules regarding subscription.
      include_role:
        name: tripleo-redhat-enforce
      vars:
        tripleo_redhat_enforce_osp: 16.0
        tripleo_redhat_enforce_os: 8.1


Roles variables
~~~~~~~~~~~~~~~

+------------------------------------------------+-----------------------------+-------------------------------+
| Name                                           | Default Value               | Description                   |
+================================================+=============================+===============================+
| tripleo_redhat_enforce_debug                   | false                       | No used currently             |
+------------------------------------------------+-----------------------------+-------------------------------+
| tripleo_redhat_enforce                         | true on Red Hat distribution| Set to true to run validation |
|                                                | false everywhere else       |                               |
+------------------------------------------------+-----------------------------+-------------------------------+
| tripleo_redhat_enforce_osp                     | OSP version (16.0, 16.1,...)| Version of OSP                |
+------------------------------------------------+-----------------------------+-------------------------------+
| tripleo_redhat_enforce_os                      | RHEL version (8.1, 8.2, ...)| Version of RHEL               |
+------------------------------------------------+-----------------------------+-------------------------------+
