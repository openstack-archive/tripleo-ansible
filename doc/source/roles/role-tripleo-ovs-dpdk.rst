=======================
Role - tripleo-ovs-dpdk
=======================


Role Documentation
==================

Welcome to the "tripleo-ovs-dpdk" role documentation. This role enables and
configures DPDK in OpenvSwitch.


Requirements
------------

* Ensure hugepages is enabled


Role Defaults
-------------

- ``tripleo_ovs_dpdk_pmd_core_list``

  - **Description**: (*Mandatory*) List of PMD Cores for DPDK. Its a
    comma-separated string of logical cores.
  - **Default**: ``''``
  - **Examples**: ``'1,13'``

- ``tripleo_ovs_dpdk_lcore_list``

  - **Description**: (*Mandatory*) List of lcores for DPDK. Its a
    comma-separated string of logical cores.
  - **Default**: ``''``
  - **Examples**: ``'0,12'``

- ``tripleo_ovs_dpdk_socket_memory``

  - **Description**: (*Mandatory*) Memory in MB to be allocated on each NUMA
    node for DPDK. Its a comma-separated string of memory in MB.
  - **Default**: ``''``
  - **Examples**:

    - ``'1024'`` for a single NUMA memory allocation
    -  ``'1024,1024'`` for a dual NUMA memory allocation

- ``tripleo_ovs_dpdk_memory_channels``

  - **Description**: (*Optional*) Number of memory channels in the memory
    architecture. Its a number.
  - **Default**: ``4``

- ``tripleo_ovs_dpdk_extra``

  - **Description**: (*Optional*) Extra parameter to be passed on to DPDK for
    initialization. Its a string.
  - **Default**: ``''``

- ``tripleo_ovs_dpdk_revalidator_cores``

  - **Description**: (*Optional*) Number of cores to he used for revalidator
    threads. Its a string with a number, specifying the count of logical cores
    to be used as revalidator threads.
  - **Default**: ``''``
  - **Examples**: ``'2'``

- ``tripleo_ovs_dpdk_handler_cores``

  - **Description**: (*Optional*) Number of cores to be used for handler
    threads. Its a string with a number, specifying the count of logical cores
    to be used as handler threads.
  - **Default**: ``''``
  - **Examples**: ``'2'``

- ``triploe_ovs_dpdk_emc_insertion_probablity``

  - **Description**: (*Optional*) EMC insertion inverse probability. Its a
    string with a number of flows (out of which 1 flow will cached). Having
    100, results in caching 1 in 100 flows. Having 0, disables EMC cache.
  - **Default**: ``''``
  - **Examples**: ``'100'``



Modules
-------

- ``openvswitch_db``

  - **Description**: It is a ansible core module, which requires additional
    changes which are in progress. Below are the pull requests against the
    core module. Once these are merged, this module can be removed.

    - https://github.com/ansible/ansible/pull/61092
    - https://github.com/ansible/ansible/pull/60994


Dependencies
------------

None
