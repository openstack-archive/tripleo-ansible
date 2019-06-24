===========================
Role - tripleo-create-admin
===========================

This role provides for the following services:

    * tripleo-create-admin


Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../tripleo_ansible/roles/tripleo-create-admin/defaults/main.yml
  :language: yaml
  :start-after: under the License.


Example default playbook
~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../tripleo_ansible/roles/tripleo-create-admin/molecule/default/playbook.yml
  :language: yaml
  :start-after: under the License.


Example keygen playbook
~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../tripleo_ansible/roles/tripleo-create-admin/molecule/keygen/playbook.yml
  :language: yaml
  :start-after: under the License.

Authorize existing user
^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: ../../../tripleo_ansible/roles/tripleo-create-admin/molecule/addkey/playbook.yml
  :language: yaml
  :start-after: under the License.
