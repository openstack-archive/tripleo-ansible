============
Contributing
============

Adding roles into this project is easy and starts with a compatible skeleton.


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
    commands =
      python -m pytest --color=yes --html={envlogdir}/reports.html --self-contained-html {tty:-s} {toxinidir}/tests/test_molecule.py


When the role is ready for CI add a jobs entry into the `zuul.d/jobs.yaml`.

.. code-block:: yaml

    - job:
        name: tripleo-ansible-centos:mol-${NEWROLENAME}
        parent: tripleo-ansible-centos
        files:
        - ^tripleo_ansible/roles/${NEWROLENAME}/.*
        vars:
          tox_envlist: mol-${NEWROLENAME}


And finally add the job into the `zuul.d/layout.yaml` file.

.. code-block:: yaml

    - project:
        check:
          jobs:
            - tripleo-ansible-centos:mol-${NEWROLENAME}


The role addition process is also automated using ansible. If ansible is
available on the development workstation change directory to the root of
the `tripleo-ansible` repository and run the the following command which
will perform all of the tasks noted above.

.. code-block:: console

    $ ansible-playbook -i localhost, role-addition.yml -e role_name=${NEWROLENAME}


If this playbook is being executed from a virtual-environment be sure to activate
the virtual environment before running the playbook.

.. code-block:: console

    $ . ~/bin/venvs/ansible/bin/activate
    (ansible)$ ansible-playbook -i localhost, role-addition.yml -e role_name=${NEWROLENAME}
