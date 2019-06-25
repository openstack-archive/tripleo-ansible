========================
Role - tripleo-docker-rm
========================

This role provides for the following services:

    * tripleo-docker-rm


.. DANGER::

    This role is a linked role to `tripleo-container-rm`. This role and exists
    to ensure we're providing a stable interface as we transition. In a future
    release this link will be removed in favor of using the stable role,
    `tripleo-container-rm`.


Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../tripleo_ansible/roles/tripleo-docker-rm/defaults/main.yml
  :language: yaml
  :start-after: under the License.


Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../tripleo_ansible/roles/tripleo-docker-rm/molecule/docker_rm/playbook.yml
  :language: yaml
  :start-after: under the License.
