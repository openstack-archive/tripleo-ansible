====================================
Role - tripleo-container-image-build
====================================

.. ansibleautoplugin::
  :role: tripleo_ansible/roles/tripleo-container-image-build

This is an example application variable file.

.. code-block:: yaml

    ---

    # FROM
    tcib_from: "ubi8"

    # Path where container file be generated
    tcib_path: "{{ lookup('env', 'HOME') }}/tripleo-base"

    # this ends up being a LABEL
    tcib_labels:
      maintainer: "TripleO"

    # ENTRYPOINT
    tcib_entrypoint: "dumb-init --single-child --"

    # STOPSIGNAL
    tcib_stopsignal: "SIGTERM"

    # ENV
    tcib_envs:
      LANG: en_US.UTF-8

    # RUN commands
    tcib_runs:
      - mkdir -p /etc/ssh
      - touch /etc/ssh/ssh_known_host
      - mkdir -p /openstack
      - dnf install -y crudini curl

    # COPY
    tcib_copies:
      - /usr/share/tripleo-common/healthcheck/common.sh /openstack/common.sh


This role can be used with the TripleO playbook, `cli-generate-containerfile.yaml`.

.. code-block:: shell

    ansible-playbook -i 'localhost,' /usr/share/ansible/tripleo-playbooks/cli-generate-containerfile.yaml -e @~/tripleo-base.yaml
