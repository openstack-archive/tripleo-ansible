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


Local testing of new roles
~~~~~~~~~~~~~~~~~~~~~~~~~~

Role based testing with molecule can be executed from within the
role directory.

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
                                          -r test-requirements.txt
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
