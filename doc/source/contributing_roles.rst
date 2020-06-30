============
Contributing
============

Adding roles into this project is easy and starts with a compatible skeleton.


Create a new role manually
~~~~~~~~~~~~~~~~~~~~~~~~~~

From with the project root, creating a skeleton for the new role.

.. code-block:: console

    $ ansible-galaxy init --role-skeleton=_skeleton_role_ --init-path=tripleo_ansible/roles ${NEWROLENAME}

When the role is ready for CI, add a **job** entry into the
`zuul.d/molecule.yaml`.

.. code-block:: yaml

    - job:
        files:
        - ^tripleo_ansible/roles/${NEWROLENAME}/.*
        name: tripleo-ansible-centos-8-molecule-${NEWROLENAME}
        parent: tripleo-ansible-centos-8-base
        vars:
          tox_envlist: mol-${NEWROLENAME}


Make sure to add the **job** name into the check and gate section at the top
of the `molecule.yaml` file.

.. code-block:: yaml

    - project:
        check:
          jobs:
            - tripleo-ansible-centos-8-molecule-${NEWROLENAME}
        gate:
          jobs:
            - tripleo-ansible-centos-8-molecule-${NEWROLENAME}


Finally add a role documentation file at
`doc/source/roles/role-${NEWROLENAME}.rst`. This file will need to contain
a title, a literal include of the defaults yaml and a literal include of
the molecule playbook, or playbooks, used to test the role, which is noted
as an "example" playbook.


Create a new role with automation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The role addition process is also automated using ansible. If ansible is
available on the development workstation change directory to the root of
the `tripleo-ansible` repository and run the the following command which
will perform the basic tasks noted above.

.. code-block:: console

    $ ansible-playbook -i localhost, role-addition.yml -e role_name=${NEWROLENAME}


If this playbook is being executed from a virtual-environment be sure to
activate the virtual environment before running the playbook.

.. code-block:: console

    $ . ~/bin/venvs/ansible/bin/activate
    (ansible)$ ansible-playbook -i localhost, role-addition.yml -e role_name=${NEWROLENAME}


Local testing of new roles
~~~~~~~~~~~~~~~~~~~~~~~~~~

Local testing of new roles can be done in any number of ways, however,
the easiest way is via the script `run-local-test`. This script
will setup the local work environment to execute tests mimicking what
Zuul does.

.. warning::

    This script makes the assumption the executing user has the
    ability to escalate privileges and will modify the local system.

To use this script execute the following command.

.. code-block:: console

    $ ./scripts/run-local-test ${NEWROLENAME}

When using the `run-local-test` script, the TRIPLEO_JOB_ANSIBLE_ARGS
environment variable can be used to pass arbitrary Ansible arguments.
For example, the following shows how to use `--skip-tags` when testing
the `tripleo_ceph_run_ansible` role.

.. code-block:: console

    $ export TRIPLEO_JOB_ANSIBLE_ARGS="--skip-tags run_ceph_ansible,run_uuid_ansible"
    $ ./scripts/run-local-test tripleo_ceph_run_ansible

Role based testing with molecule can be executed directly from within
the role directory.

.. note::

    Most tests require docker for container based testing. If Docker
    is not available on the local workstation it will need to be
    installed prior to executing most molecule based tests.


.. note::

    The script `bindep-install`, in the **scripts** path, is
    available and will install all system dependencies.


Before running basic molecule tests, it is recommended to install all
of the python dependencies in a virtual environment.

.. code-block:: console

    $ python -m virtualenv --system-site-packages "${HOME}/test-python"
    $ ${HOME}/test-python/bin/pip install -r requirements.txt \
                                          -r test-requirements.txt \
                                          -r molecule-requirements.txt
    $ source ${HOME}/test-python/bin/activate


To run a basic molecule test, simply source the `ansibe-test-env.rc`
file from the project root, and then execute the following commands.

.. code-block:: console

    (test-python) $ cd tripleo_ansible/roles/${NEWROLENAME}/
    (test-python) $ molecule test --all


If a role has more than one scenario, a specific scenario can be
specified on the command line. Running specific scenarios will
help provide developer feedback faster. To pass-in a scenario use
the `--scenario-name` flag with the name of the desired scenario.

.. code-block:: console

    (test-python) $ cd tripleo_ansible/roles/${NEWROLENAME}/
    (test-python) $ molecule test --scenario-name ${EXTRA_SCENARIO_NAME}


When debugging molecule tests its sometimes useful to use the
`--debug` flag. This flag will provide extra verbose output about
test being executed and running the environment.

.. code-block:: console

    (test-python) $ molecule --debug test


Contributing plugins
~~~~~~~~~~~~~~~~~~~~

All plugins contributed to the TripleO-Ansible can be found in the
`tripleo_ansible/ansible_plugins` directory, from the root of this project.
When contributing a plugin, make sure to also add documentation in the
`doc/source/modules` folder. All documentation added to this folder will be
automatically indexed and rendered via `sphinx`.

If a contributed plugin is following the Ansible practice of placing
documentation within the plugin itself, the following snippet can be used in a
sphinx template to auto-render the in-code documentation.

.. code-block:: rst

    .. ansibleautoplugin::
       :module: tripleo_ansible/ansible_plugins/${DIRECTORY}/${PLUGINFILE}
       :documentation: true
       :examples: true

The snippet can take two options, `documentation` and `examples`. If a given
plugin does not have either of these in-code documentation objects,
documentation for either type can be disabled by omitting the option.

.. code-block:: rst

    .. ansibleautoplugin::
       :module: tripleo_ansible/ansible_plugins/${DIRECTORY}/${PLUGINFILE}
       :documentation: true
