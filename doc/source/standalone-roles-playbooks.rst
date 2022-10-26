==============================
Standalone Roles and Playbooks
==============================

The roles provided by tripleo-ansible can be used directly by ansible or
ansible-playbook, without requiring direct integration with
tripleo-heat-templates or the config-download mechanism. This usage is referred
to as standalone usage.

It is a design goal of tripleo-ansible that all of the ansible roles, plugins,
modules, inventory, and playbooks provided by this repository are able to be
used in this standalone fashion.

Given the evolution of development within tripleo-ansible, not all roles were
developed with standalone usage in mind, and not all roles offer the same
interfaces. However, it is the goal of this documentation to document the
consistent patterns that are present across the effort to make standalone roles
a primary interface provided by tripleo-ansible.

Roles
=====

The following patterns define the interfaces provided by standalone roles. Not
all roles will follow all patterns documented here as not all will be
applicable, and different roles have already been developed. However, new
development SHOULD follow these patterns in every extent possible.

Standalone roles names should be formatted as ``tripleo_<service>_<component>``
like ``tripleo_ovn_dbs`` and ``tripleo_ovn_controller`` Each component of a
service, or services shared configs, should become a standalone ansible role.
Small shared components of a service, like ones responsible for common service
logging, could be merged with either, or all, of the service components roles.

Variables
---------

We aim to maintain both standalone ansible and legacy t-h-t/puppet deployment
methods for a while. We need them syncronized, backportable, and its covered
features to be kept in parity. For that, role variables for services and
components should follow the naming rules:

#. If there is a corresponding Heat parameter for it in tripleo-heat-templates,
   the variable names should be: ``tripleo_<service>_<component>_<param_name>``
   Where ``param_name>`` is ``snake_case`` translation of its ``CamelCase`` name.
   For example, the ``tripleo_nova_compute`` role variable for
   ``NovaComputeLibvirtPreAllocateImages`` should be named
   ``tripleo_nova_compute_libvirt_pre_allocate_images``
#. If there is a corresponding Heat parameter shared between multiple
   services/components templates, each standalone ansible role should refer to
   its dedicated role var, and provide a failback to a shared variable, like:
   ``UpgradeLevelNovaCompute`` should be named ``tripleo_nova_libvirt_upgrade_level_compute``
   for the ``tripleo_nova_libvirt`` role variable, and
   ``tripleo_nova_compute_upgrade_level_compute`` for the ``tripleo_nova_compute``
   role. And both should failback to ``tripleo_upgrade_level_compute`` in the
   roles default vars.
#. Complex values may be evaluated as facts in ``tasks/main.yml`` For example,
   ``cinder_common_kolla_permissions`` and ``kolla_permissions`` that correspond to
   ``CephExternalMultiConfig`` of Nova Libvirt and Cinder Common t-h-t services,
   could be defined via the service-name prefixed ``_ceph_multiconfig_permissions``
   facts for the ``tripleo_nova_libvirt`` and ``tripleo_cinder_common`` roles.
   Then roles for cinder backup and volume components may share that fact from
   the cinder common role. Beware that setting facts is expensive - it requires
   running a task which costs time and thus it should be avoided. However, when
   there are complex t-h-t yaql and str_replace templating functions from Heat,
   it is OK to translate these into jinja and set facts. If bottlenecks are
   found which will affecting production clusters, then they can be optimized
   later.
#. Puppet Hiera data should ideally be mapped into standalone roles variables
   as well. Unless there is ansible config templating and/or conf files snippets
   used as direct user inputs. However, please always remember about the goal of
   simplified backports of this state-of-art TripleO deployment framework into
   the "legacy world" of Heat and Puppet. The example role var name for hiera
   ``nova::compute::libvirt::cpu_model_extra_flags`` could be
   ``tripleo_nova_compute_cpu_model_extra_flags``
#. When there is a Heat parameter assigned to Hiera data for Puppet, only
   provide a role var for the former, and omit it for the latter. For example,
   ``NovaEnableVTPM``s value in t-h-t is assigned to Hiera's
   ``nova::compute::libvirt::swtpm_enabled`` Use the role name
   ``tripleo_nova_compute_enable_vtpm`` to cover both mappings with a single
   input. Had there been no matching Heat parameter for it, the role var name
   would become ``tripleo_nova_compute_libvirt_swtpm_enabled`` to match the Hiera
   data mapping.

Following these rules will help TripleO developers to maintain both deployment
methods, and simply using ansible group vars to call standalone roles from
tripleo-heat-templates, as a drop-in replacement for existing Heat parameters
and Hiera data, with full feature parity maintained automagically. That would
also help a lot the TripleO project users to convert their Heat templates and
customizations to quickly provide it as inputs for standalone roles.

To simplify code generation and verification of role vars mappings to Heat
parameters and Puppet Hiera data, there is a helper script_ (provided as the
best effort).

.. _script: https://gist.github.com/bogdando/ab2118f4c6fbb88c1c127fd6eb82b756

Task files
----------

Tasks within roles should be broken out by the tasks high level management
function, with each function in its own task file. The following task files are
common to most roles, and roles providing these functional tasks must organize
their tasks in files whose names match the names shown here.

.. code-block::

  install.yml
  configure.yml
  run.yml
  update.yml
  upgrade.yml
  scale_up.yml
  scale_down.yml

install.yml
  Installation tasks. Tasks that install software from remote repositories, or
  pull container images, unpack tarballs, etc.

configure.yml
  Configuration tasks. Tasks that configure software through generating or
  editing configuration files, setting configuration data, etc.

run.yml
  Run tasks. Tasks that run other commands, start daemon services, start one
  time or persistent containers, etc.

update.yml
  Update tasks. Tasks that update software across minor releases, which
  typically do not require downtime or cause API backwards compatibility.

upgrade.yml
  Upgrade tasks. Tasks that upgrade software across major releases. May require
  downtime of the managed software or cause breaking backwards compatibility
  changes.

scale_up.yml
  Scale up tasks. Tasks that are run when the software is scaled onto existing
  nodes or new nodes.

scale_down.yml
  Scale down tasks. Tasks that are run when the software is scaled down and
  stopped from running on existing nodes.

It may not be clear how to organize all tasks within the above files in a given
role. There may be some grey area for some tasks, or even subjective
classification of how to organize tasks. This is recognized. In the majority of
cases, roles should work in the manner of least surprise to users and
operators. As examples of "least suprise", tasks provided by configure.yml
should not leave long running processes around, run.yml should not install
needed software from remote repositories, etc.

Configuration
-------------

Configuration tasks will vary by role based on the software that the role
manages.

For containerized OpenStack services (and other services), that use
configuration files, the following configuration pattern can be used:

#. Start a container from the service image
#. Copy out all needed configuration files from the running container to
   the ``var/lib/config-data/ansible-generated/<service>`` directory on the
   managed node.
#. Configure the configuration files as needed using common configuration
   modules such as ``inifile``.
#. When starting the actual service container, bind mount in the configuration
   files from ``/var/lib/config-data/ansible-generated/<service>`` to the
   needed locations within the service container.

The following tasks show an example implementation of the above pattern to
configure the ``nova_compute`` service from within the ``tripleo_nova_compute``
role. Note that this is a simplified implementation of the actual task list
from the role:

.. code-block:: yaml

    - name: Ensure /var/lib/config-data/ansible-generated/nova_compute/etc/nova exists
      file:
        path: "/var/lib/config-data/ansible-generated/nova_compute/etc/nova"
        state: directory
        recurse: true

    - name: Remove nova_compute_config container if exists
      shell: |
        podman rm -f nova_compute_config || :

    - name: Run nova_compute_config container
      shell: podman run --detach --name nova_compute_config quay.io/tripleomastercentos9/openstack-nova-compute:current-tripleo sleep infinity
      register: config_container_id

    - name: Copy initial config files from nova_libvirt_config container
      shell: |
        mount_dir=$(podman mount nova_compute_config)
        cp -a ${mount_dir}/etc/nova/nova.conf /var/lib/config-data/ansible-generated/nova_compute/etc/nova/nova.conf
      failed_when: false
      notify: Remove nova_compute_config container
      register: copy_config_files

    - name: Check for failure
      debug:
        msg: |
          Copying config files failed
          {{ copy_config_files.stdout }}
          {{ copy_config_files.stderr }}
      when:
        - copy_config_files.rc != 0
      failed_when: true

    - name: Configure nova.conf
      ini_file:
        path: "/var/lib/config-data/ansible-generated/nova_compute/etc/nova/nova.conf"
        section: "{{ item.section }}"
        option: "{{ item.option }}"
        value: "{{ item.value }}"
      loop: "{{ nova_conf }}"
      vars:
        nova_conf: |
          - section: DEFAULT
            option: reserved_host_memory_mb
            value: 1024
          - section: DEFAULT
            option: ram_allocation_ratio
            value: 1.0

.. note::

  Configuration is **not** done with Puppet in the standalone roles. Puppet
  should not be used at all within new role development in tripeo-ansible.
  Puppet functionality needs to be migrated to ansible tasks. See the
  tripleo-spec `decouple-tripleo-tasks`_ for more information.

Container management
--------------------

Managing containers from a role may vary depending on the role's purpose. For
OpenStack and similar services, container management can be done with the
:doc:`roles/role-tripleo_container_standalone` role. The
``tripleo_container_standalone`` role has 3 main input variables each time it
is used:

#. tripleo_container_standalone_service - Service name/label used for directory
   and file naming.
#. tripleo_container_standalone_container_defs - A dictionary of container
   names and yml definitions. The YAML structure matches that of the
   ``docker_config`` interface defined from ``tripleo-heat-templates``.
#. tripleo_container_standalone_kolla_config_files - A dictionary of container
   names and yml structure of a kolla conifguration file.

With these 3 inputs, the ``tripleo_container_standalone`` role will manage the
container (start/run) as described by the inputs.

The following tasks show an example implementation of using the
``tripleo_container_standalone`` role to manage the containers defined by the
``nova_compute`` service within the ``tripleo_nova_compute`` role:

.. code-block:: yaml

    - name: Manage nova_wait_for_compute_service container
      when: tripleo_nova_compute_additional_cell|bool
      include_role:
        name: tripleo_container_standalone
      vars:
        tripleo_container_standalone_service: nova_wait_for_compute_service
        tripleo_container_standalone_container_defs:
          nova_wait_for_compute_service: "{{ lookup('template', 'nova_wait_for_compute_service.yml.j2') | from_yaml }}"
        tripleo_container_standalone_kolla_config_files:
          nova_wait_for_compute_service: "{{ lookup('file', 'files/nova_wait_for_compute_service.yml') | from_yaml }}"

    - name: Manage nova_compute container
      include_role:
        name: tripleo_container_standalone
      vars:
        tripleo_container_standalone_service: nova_compute
        tripleo_container_standalone_container_defs:
          nova_compute: "{{ lookup('template', 'nova_compute.yml.j2') | from_yaml }}"
        tripleo_container_standalone_kolla_config_files:
          nova_compute: "{{ lookup('template', 'templates/kolla_config/nova_compute.yml.j2') | from_yaml }}"

Notice how the container definitions and kolla config files yml structure are
read from templates using ``lookup``. This allows for customizing the container
definitions based on the values of provided variables for the deployment.

Playbooks
=========

The standalone playbooks provided by tripleo-ansible can be used to deploy and
manage an OpenStack environment entirely with ansible runtimes (ansible /
ansible-playbook). To separate these playbooks from playbooks for other
purposes within tripleo-ansible, the standalone playbooks are prefixed with
``deploy-`` within the `tripleo_ansible/playbooks`_ directory.

The playbooks are organized by management function like the task files within
each role. Additionally, they are further organized to allow managing operating
system (OS) and OpenStack services in isolation from the other. Like task
organization, the delineation between an OS and OpenStack service may not be
clear. One way to distinguish the service is to consider the source of the
software managed by the service. The source may either be provided by an
OpenStack repository, or from an OS repository (such as CentOS). As an example,
libvirt may be considered an OS service as it's software is provided by CentOS,
while ``nova_compute`` is considered an OpenStack service as it's software is
provided by OpenStack/OpenDev.

The following provided playbooks illustrate the organization of management
function:

.. code-block::

  deploy-tripleo-openstack-configure.yml
  deploy-tripleo-openstack-install.yml
  deploy-tripleo-openstack-run.yml
  deploy-tripleo-os-configure.yml
  deploy-tripleo-os-install.yml
  deploy-tripleo-os-run.yml

Additionally, playbooks are provided to manage other parts of the deployment,
in order to manage a complete environment. The playbooks include:

.. code-block::

  deploy-tripleo-facts.yml
  deploy-tripleo-selinux.yml
  deploy-tripleo-pre-network.yml
  deploy-tripleo-network-configure.yml
  deploy-tripleo-network-validate.yml

In the simplest form, the standalone playbooks will consume standalone roles
with just an ``include_role`` module using the ``tasks_from`` argument to
include the corresponding tasks file from the role for the management function.

An example of tasks from the ``deploy-tripleo-os-run.yml`` playbook illustrate
this pattern:

.. code-block:: yaml

    - name: Run sshd
      include_role:
        name: tripleo_sshd
        tasks_from: run.yml
    - name: Run chrony
      include_role:
        name: chrony
        tasks_from: run.yml
    - name: Run timezone
      include_role:
        name: tripleo_timezone
        tasks_from: run.yml

A top level playbook, `deploy-overcloud-compute.yml`_ is also provided that
includes the above ``deploy-`` playbooks in a way that is used to deploy and
manage OpenStack compute nodes.

Other top level playbooks will be added for other OpenStack management use
cases.

Inventory
=========

The `inventory`_ provided by tripleo-ansible is an example inventory that can
be used to configure the same node running ansible-playbook as an OpenStack
compute node. It is a sample inventory, using standard TripleO defaults and is
meant to be copied and modified for different environments.

The files provided by the sample inventory are as follows:

.. code-block::

  01-site
  02-computes
  03-tripleo
  99-standalone-vars
  group_vars/overcloud
  host_vars/localhost

01-site
  Defines top level groups used by the playbooks including allovercloud,
  overcloud, and Compute
02-computes
  Defines the actual compute nodes for the deployment. Only localhost is
  included in the sample. Additional compute nodes could be added here.
03-tripleo
  Defines common variables for the overcloud.
99-standalone-vars
  Defines the minimal set of ansible variables to a default deployment using
  the default values. These variables include IP addresses in the default
  TripleO subnet range (192.168.24.0/24), passwords, and connection url's.
group_vars/overcloud
  Defines common variables to the overcloud group
host_vars/localhost
  Defines host specific variables to each compute node, in the sample, only
  localhost is used.

Usage Examples
==============

tripleo-ansible environment setup
---------------------------------

As work is in progress, an environment needs to be setup that can consume the
in progress work from tripleo-ansible and other repositories.

The environment setup example assumes a non-root user, and working from the
home directory, but the example can be modified as needed.

On the ansible controller node

#. Clone tripleo-ansible

   .. code-block:: shell

    git clone https://opendev.org/openstack/tripleo-ansible

#. Apply the latest patches from the `standalone-roles`_ topic branch to the cloned repository

#. Clone ansible-role-chrony. It is also needed, but is not part of tripleo-ansible.

   .. code-block:: shell

    git clone https://opendev.org/openstack/ansible-role-chrony

#. Create a roles directory for ansible-role-chrony, and an ``ansible.cfg`` to
   use roles from the git repositories.

   .. code-block:: shell

    mkdir ~/roles; ln -s ~/ansible-role-chrony ~/roles/chrony
    cat <<EOF>ansible.cfg
    [defaults]
    roles_path=~/roles:~/tripleo-ansible/tripleo_ansible/roles:~/.ansible/roles:/usr/share/ansible/roles:/etc/ansible/roles
    EOF


Execution examples
------------------

With the environment setup, ``anible-playbook`` is used to execute the playbook
to manage compute nodes. These examples show different ways to use the
playbooks.

#. TripleO defaults, localhost configured as a compute node

   .. code-block:: shell

    sudo ansible-playbook -i tripleo-ansible/tripleo_ansible/inventory tripleo-ansible/tripleo_ansible/playbooks/deploy-overcloud-compute.yml

#. TripleO defaults, remote node(s) configured as compute node(s)

   .. code-block:: shell

    # Edit tripleo-ansible/tripleo_ansible/inventory/02-computes, and add additional compute nodes under the ``[Compute]`` group
    # Add additional ``host_vars`` files under tripleo-ansible/tripleo_ansible/inventory/host_vars to configure host specific connection variables if needed
    sudo ansible-playbook -i tripleo-ansible/tripleo_ansible/inventory tripleo-ansible/tripleo_ansible/playbooks/deploy-overcloud-compute.yml

#. Modifying defaults, remote node(s) configured as compute node(s)

   .. code-block:: shell

    # Modify inventory as needed from previous examples
    # Edit tripleo-ansible/tripleo_ansible/inventory/99-custom, and set the desired variable values
    sudo ansible-playbook -i tripleo-ansible/tripleo_ansible/inventory tripleo-ansible/tripleo_ansible/playbooks/deploy-overcloud-compute.yml

tripleo_compute_node role for dev/test
======================================

The tripleo_compute_node role within tripleo-ansible can be used for development and
test of the standalone playbooks and roles. The role has a ``default`` molecule
scenario that executes the standalone playbooks when `converge.yml`_ is run by
molecule.

The scenario uses the podman molecule driver, and starts a podman container
named `tripleo_compute_node`_. The ``tripleo_compute_node`` container is a
`rootless podman`_ container started as the user executed molecule. The container uses
`podman in podman`_, and has `systemd as the init process`_. This
configuration allows for treating the container as a simulated compute node for
the purposes of dev and test.

On the host, the only requirements are that podman is installed, and the
openvswitch kernel module is loaded. Without the openvswitch module loaded on
the house, the ``ovn`` containers with the ``tripleo_compute_node`` container will
fail to start. Other than the openvswitch kernel module requirement, this
environment is isolated from the host.

A ``tox`` target exists to easily create the environment:

   .. code-block:: console

    [stack@centos-9-stream tripleo-ansible]$ tox -e molecule-compute-node -- --destroy=never

``destroy=never`` are passed as positional arguments to tox, so that molecule
does not clean up the environment automatically. Omit these arguments if the
container should be deleted after the molecule test.

After the tox execution with ``destroy=never`` the ``tripleo_compute_node``
environment is up and running:

   .. code-block:: console

    [stack@centos-9-stream tripleo-ansible]$ podman ps
    CONTAINER ID  IMAGE                                           COMMAND CREATED      STATUS          PORTS       NAMES
    cf9293611eb8  localhost/molecule_local/centos/centos:stream9  /sbin/init  3 hours ago  Up 3 hours ago              tripleo_compute_node

The container can be entered with either ``podman exec`` or with ``molecule
login``:

   .. code-block:: console

    [stack@centos-9-stream tripleo-ansible]$ source .tox/molecule-compute-node/bin/activate
    (molecule-compute-node) [stack@centos-9-stream tripleo-ansible]$ cd tripleo_ansible/roles/tripleo_compute_node/
    (molecule-compute-node) [stack@centos-9-stream tripleo_compute_node]$ molecule login
    INFO     Found config file
    /home/stack/tripleo-ansible/.config/molecule/config.yml
    INFO     Running default > login
    [root@tripleocomputenode /]#

From within the container, the compute services are visible:

   .. code-block:: console

    [root@tripleocomputenode /]# podman ps
    CONTAINER ID  IMAGE                                                                  COMMAND      CREATED      STATUS                     PORTS       NAMES
    fbdc4d34c11b  quay.io/tripleomastercentos9/openstack-ovn-controller:current-tripleo  kolla_start  3 hours ago  Up 3 hours ago (healthy)               ovn_controller
    e8be9a2f5b10  quay.io/tripleomastercentos9/openstack-cron:current-tripleo            kolla_start  2 hours ago  Up 2 hours ago (healthy)               logrotate_crond
    d741a2abacd0  quay.io/tripleomastercentos9/openstack-iscsid:current-tripleo          kolla_start  2 hours ago  Up 2 hours ago                         iscsid
    ea996a8c5357  quay.io/tripleomastercentos9/openstack-nova-libvirt:current-tripleo    kolla_start  2 hours ago  Up 2 hours ago                         nova_virtlogd
    d463308dcac8  quay.io/tripleomastercentos9/openstack-nova-libvirt:current-tripleo    kolla_start  2 hours ago  Up 2 hours ago                         nova_virtsecretd
    295fb6d01be7  quay.io/tripleomastercentos9/openstack-nova-libvirt:current-tripleo    kolla_start  2 hours ago  Up 2 hours ago                         nova_virtnodedevd
    ac21ae881494  quay.io/tripleomastercentos9/openstack-nova-libvirt:current-tripleo    kolla_start  2 hours ago  Up 2 hours ago                         nova_virtstoraged
    270fe4c0f0ef  quay.io/tripleomastercentos9/openstack-nova-libvirt:current-tripleo    kolla_start  2 hours ago  Up 2 hours ago                         nova_virtqemud
    1e8085b34a49  quay.io/tripleomastercentos9/openstack-nova-libvirt:current-tripleo    kolla_start  2 hours ago  Up 2 hours ago                         nova_virtproxyd
    5ba018f50b31  quay.io/tripleomastercentos9/openstack-nova-compute:current-tripleo    kolla_start  2 hours ago  Up 2 hours ago                         nova_compute

Exit the container to return to the ``tripleo-ansible`` checkout:

   .. code-block:: console

    [root@tripleocomputenode /]# exit
    exit
    (molecule-compute-node) [stack@centos-9-stream tripleo_compute_node]$

To develop and test any of the playbooks and roles, make the desired changes
directly in the tripleo-ansible checkout. The ``ansible-test-env.rc`` file must
be sourced to set the configuration paths for ansible so that ansible knows
where to find the custom strategies, plugins, modules, and roles provided by
``tripleo-ansible``:

   .. code-block:: console

    (molecule-compute-node) [stack@centos-9-stream tripleo_compute_node]$ source ../../../ansible-test-env.rc
    Ansible test environment is now active
    Run 'unset-ansible-test-env' to deactivate.

    (molecule-compute-node) [stack@centos-9-stream tripleo_compute_node]$ ansible-playbook -i molecule/inventory/ ../../playbooks/deploy-tripleo-facts.yml

TripleO integration
===================

`TripleO standalone`_ can be used to deploy an OpenStack control plane, and
the standalone roles can then be used to deploy additional Compute node(s).

The required ``99-standalone-vars`` inventory file can be generated from the deployed
OpenStack control plane by using ``tripleo-standalone-vars`` script.

Copy the script to either your standalone controller or undercloud before running it.

Use the generated ``99-standalone-vars`` from the below commands
when ``ansible-playbook`` is executed.

#. Here is the ``tripleo-standalone-vars`` help page.

   .. code-block:: shell

    ~/tripleo-ansible/scripts/tripleo-standalone-vars --help
    usage: tripleo-standalone-vars [-h] [--config-download-dir CONFIG_DOWNLOAD_DIR] [--output-file OUTPUT_FILE] [--role ROLE] [--force]

    tripleo-standalone-vars

    options:
      -h, --help            show this help message and exit
      --config-download-dir CONFIG_DOWNLOAD_DIR, -c CONFIG_DOWNLOAD_DIR
                            The config-download directory for the deployment used as the source of the generated ansible variables. (default: ~/overcloud-
                            deploy/overcloud/config-download/overcloud)
      --output-file OUTPUT_FILE, -o OUTPUT_FILE
                            Output file containing the generated ansible vars. (default: 99-standalone-vars)
      --role ROLE, -r ROLE  Primary role name from the source deployment. (default: Controller)
      --force, -f           Force overwriting the output file if it exists. (default: False)

#. From a standalone controller where you want to add compute services, Execute the ``tripleo-standalone-vars`` script

   .. code-block:: shell

    ~/tripleo-ansible/scripts/tripleo-standalone-vars \
      --config-download-dir /home/stack/tripleo-deploy/standalone/$(ls -1dtr standalone-ansible* | tail -n -1) \
      --role Standalone \
      --output-file ~/tripleo-ansible/tripleo_ansible/inventory/99-standalone-vars

#. From an undercloud with an already deployed overcloud control plane, Execute the ``tripleo-standalone-vars`` script

   .. code-block:: shell

    ~/tripleo-ansible/scripts/tripleo-standalone-vars

#. The script will generate ``99-standalone-vars`` in the current directory. Copy the file to the ansible control node where the inventory is defined.

#. If we want to regenerate the ``99-standalone-vars``, Execute the ``tripleo-standalone-vars`` script with ``--force`` flag.

   .. code-block:: shell

    ~/tripleo-ansible/scripts/tripleo-standalone-vars --force

Integration of standalone roles with tripleo-heat-templates
-----------------------------------------------------------

As standalone roles are developed, they can also be consumed from
tripleo-heat-templates so that maintenance of the ansible tasks only needs to
be done from a single location in tripleo-ansible.

Once a role provides the equivalent set of task functionality, the role can be
consumed within tripleo-heat-templates using the composable service interfaces.

The ``ansible_group_vars`` interface is used to define values for ansible
variables that can be consumed by the included roles. The following example
shows how the ``logrotate-crond-container-puppet.yml`` service from
tripleo-heat-templates uses the standalone ``tripleo_logrotate_crond`` role
from tripleo-ansible.

.. code-block:: yaml

    role_data:
      ansible_group_vars:
        tripleo_logrotate_crond_purge_after_days: {get_param: LogrotatePurgeAfterDays}
        tripleo_logrotate_crond_config_volume: /var/lib/config-data/puppet-generated/crond
        tripleo_logrotate_crond_image: {get_attr: [RoleParametersValue, value, ContainerCrondConfigImage]}
      host_prep_tasks:
        - name: tripleo_logrotate_crond install tasks
          include_role:
            name: tripleo_logrotate_crond
            tasks_from: install.yml
      deploy_steps_tasks:
        - name: tripleo_logrotate_crond configure tasks
          when: step|int == 2
          include_role:
            name: tripleo_logrotate_crond
            tasks_from: configure.yml
        - name: logrotate-crond container
          when: step|int == 4
          include_role:
            name: tripleo_logrotate_crond
            tasks_from: run.yml
      update_tasks:
        - name: logrotate-crond update
          when: step|int == 1
          include_role:
            name: tripleo_logrotate_crond
            tasks_from: update.yml
      upgrade_tasks:
        - name: logrotate-crond upgrade
          when: step|int == 1
          include_role:
            name: tripleo_logrotate_crond
            tasks_from: upgrade.yml

Each composable service interface (such as ``host_prep_tasks``,
``deploy_steps_tasks``, etc) consumes the corresponding task file from the
role. The ``docker_config`` and ``kolla_config`` sections are also no longer
needed in the composable service as that logic is contained within the
container management tasks in ``run.yml`` from the standalone role.

Step-wise deployment logic
--------------------------

The step based deployment from tripleo-heat-templates which uses a rigid
framework of 5 distinct steps or stages at which software is managed is **not**
reproduced with the standalone roles and playbooks.

Most OS and OpenStack services have sufficiently evolved such that the step
based deployment is not needed. However, ordering is still important during the
deployment. Ordering with the standalone roles in tripleo-ansible is defined
directly by the playbooks. There is no need for roles to have a higher concept
of ordering by defining tasks for each steps. The playbooks simply include the
right task files from a given role in the right order.

However, needed ordering may impose a given task file structure within a role.
If not all tasks from a role's ``run.yml`` can happen at once in a given
order, then the task file may need to be factored out into multiple files
(``setup.yml``, ``bootstrap.yml``) so that tasks can be included in the
needed order.

Heat parameter and Hiera key to Ansible group variable mapping
--------------------------------------------------------------

Heat parameters and Hiera keys will often end up mapped to equivalent Ansible
group variables as functionality is ported to standalone roles. In cases where
equivalent group variables are used, the name mapping between
tripleo-heat-templates, puppet-tripleo, tripleo-ansible should be consistent.

Heat parameters using CamelCase should be converted to ansible group variables
using under_score naming and prefixed with the standalone role name.

As an example, the Heat parameter ``CephClusterFSID`` would be named
``tripleo_nova_compute_ceph_cluster_fsid`` as an ansible group variable.

Configuration
-------------

tripleo-heat-templates still uses Puppet for configuration, host tasks, and
some bootstrap tasks. The standalone roles can still be used alongside Puppet,
even though the roles should themselves should not use puppet. The task file
organization of a role should allow for running only individual task files as
needed with ``include_role``, such that the Puppet pieces can be run by other
means.

For configuration, the standalone roles can be pointed at a different
configuration directory for bind mounting into containers. This allows the
container bind mount to switch between
``/var/lib/config-data/puppet-generated`` and
``/var/lib/config-data/ansible-generated`` depending on which method is used.

The standalone roles also provided a boolean variable to control whether
configuration is done at all with ansible. When set to ``False`` the ansible
tasks that generate the config files would be skipped in the standalone roles.

As an example, the variables for the ``tripleo_nova_compute`` role are defined
as:

.. code-block:: yaml

    tripleo_nova_compute_config_use_ansible: true
    tripleo_nova_compute_config_dir: /var/lib/config-data/ansible-generated/nova_libvirt

tripleo-heat-templates can define the variables within the
``ansible_group_vars`` interface to control the configuration behavior.

.. _tripleo_ansible/playbooks: https://opendev.org/openstack/tripleo-ansible/src/branch/master/tripleo_ansible/playbooks
.. _deploy-overcloud-compute.yml: https://opendev.org/openstack/tripleo-ansible/src/branch/master/tripleo_ansible/playbooks/deploy-overcloud-compute.yml
.. _inventory: https://opendev.org/openstack/tripleo-ansible/src/branch/master/tripleo_ansible/inventory
.. _standalone-roles: https://review.opendev.org/q/topic:standalone-roles
.. _standalone-roles patch for ansible-role-chrony: https://review.opendev.org/c/openstack/ansible-role-chrony/+/842223
.. _TripleO standalone: https://docs.openstack.org/project-deploy-guide/tripleo-docs/latest/deployment/standalone.html
.. _decouple-tripleo-tasks: https://specs.openstack.org/openstack/tripleo-specs/specs/zed/decouple-tripleo-tasks.html
.. _tripleo_compute_node: https://opendev.org/openstack/tripleo-ansible/src/branch/master/tripleo_ansible/roles
.. _converge.yml: https://opendev.org/openstack/tripleo-ansible/src/branch/master/tripleo_ansible/roles/tripleo_compute_node/molecule/default/converge.yml
.. _rootless podman: https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md
.. _podman in podman: https://www.redhat.com/sysadmin/podman-inside-container
.. _systemd as the init process: https://developers.redhat.com/blog/2019/04/24/how-to-run-systemd-in-a-container?extIdCarryOver=true&sc_cid=701f2000001Css0AAC#other_cool_features_about_podman_and_systemd
