============
Contributing
============

Adding roles into this project is easy and starts with a compatible skeleton.


Create a new role manually
~~~~~~~~~~~~~~~~~~~~~~~~~~

From with the project root, creating a skeleton for the new role.

.. code-block:: console

    $ ansible-galaxy init --role-skeleton=_skeleton_role_ --init-path=tripleo_ansible/roles ${NEWROLENAME}


Once the new role has been created, and is ready for testing add the role into
the `tox.ini` file as an test scenario.

.. code-block:: ini

    [testenv:mol-${NEWROLENAME}]
    basepython={[testenv:mol]basepython}
    deps={[testenv:mol]deps}
    changedir = {toxinidir}/tripleo_ansible/roles/${NEWROLENAME}
    envdir = {toxworkdir}/mol
    commands = python -m pytest --color=yes --html={envlogdir}/reports.html --self-contained-html {tty:-s} {toxinidir}/tests/test_molecule.py


If a given role has more than one scenario to test, the `--scenario` argument
can be used to set the scenario accordingly.

.. code-block:: ini

    [testenv:mol-${NEWROLENAME}-${SCENARIO_2}]
    basepython={[testenv:mol-${NEWROLENAME}]basepython}
    deps={[testenv:mol-${NEWROLENAME}]deps}
    changedir = {[testenv:mol-${NEWROLENAME}]changedir}
    envdir = {[testenv:mol-${NEWROLENAME}]envdir}
    commands = python -m pytest --color=yes --html={envlogdir}/reports.html --self-contained-html {tty:-s} {toxinidir}/tests/test_molecule.py --scenario=${SCENARIO_2}


When the role is ready for CI, add a **job** entry into the `zuul.d/molecule.yaml`.

.. code-block:: yaml

    - job:
        files:
        - ^tripleo_ansible/roles/${NEWROLENAME}/.*
        name: tripleo-ansible-centos-7-molecule-${NEWROLENAME}
        parent: tripleo-ansible-centos
        vars:
          tox_envlist: mol-${NEWROLENAME}


Make sure to add the **job** name into the check and gate section at the top of
the `molecule.yaml` file.

.. code-block:: yaml

    - project:
        check:
          jobs:
            - tripleo-ansible-centos-7-molecule-${NEWROLENAME}
        gate:
          jobs:
            - tripleo-ansible-centos-7-molecule-${NEWROLENAME}


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


If this playbook is being executed from a virtual-environment be sure to activate
the virtual environment before running the playbook.

.. code-block:: console

    $ . ~/bin/venvs/ansible/bin/activate
    (ansible)$ ansible-playbook -i localhost, role-addition.yml -e role_name=${NEWROLENAME}
