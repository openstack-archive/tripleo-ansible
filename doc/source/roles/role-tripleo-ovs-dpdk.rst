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
    comma-separated string of logical cores. These core should be part
    of ``isolcpus`` kernel parameter and be excluded from ``NovaComputeCpuDedicatedSet``
    and from ``NovaComputeCpuSharedSet``
  - **Default**: ``''``
  - **Examples**: ``'1,13'``

- ``tripleo_ovs_dpdk_lcore_list``

  - **Description**: (*Optional*) List of lcores for DPDK. Its a
    comma-separated string of logical cores.
    All ovs-vswitchd threads will be pinned to the first core declared
    in the mask.
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

- ``tripleo_ovs_dpdk_emc_insertion_probablity``

  - **Description**: (*Optional*) EMC insertion inverse probability. Its a
    string with a number of flows (out of which 1 flow will cached). Having
    100, results in caching 1 in 100 flows. Having 0, disables EMC cache.
  - **Default**: ``''``
  - **Examples**: ``'100'``

- ``tripleo_ovs_dpdk_enable_tso``

  - **Description**: (*Optional*) Enable TSO support in OVS DPDK datapath.
  - **Default**: ``false``
  - **Examples**: ``true``

- ``tripleo_ovs_dpdk_pmd_auto_lb``

  - **Description**: (*Optional*) Enable DPDK OVS PMD Auto Load Balance.
  - **Default**: ``false``
  - **Examples**: ``true``

- ``tripleo_ovs_dpdk_pmd_load_threshold``

  - **Description**: (*Optional*) Minimum PMD thread load threshold, in range
    0 to 100. Its a string with a number, specifies the minimum
    PMD thread load threshold (% of used cycles) of any non-isolated PMD threads
    when a PMD Auto Load Balance may be triggered.
  - **Default**: ``''``
  - **Examples**: ``'50'``

- ``tripleo_ovs_dpdk_pmd_improvement_threshold``

  - **Description**: (*Optional*) PMD load variance improvement threshold, in range
    0 to 100. Its a string with a number, specifies the minimum evaluated % improvement
    in load distribution across the non-isolated PMD threads that will allow
    a PMD Auto Load Balance to occur.
    Note, setting this parameter to 0 will always allow an auto load balance to occur
    regardless of estimated improvement or not.
  - **Default**: ``''``
  - **Examples**: ``'10'``

- ``tripleo_ovs_dpdk_pmd_rebal_interval``

  - **Description**: (*Optional*) PMD auto load balancing interval, in range
    0 to 20,000. Its a string with a number, specifies the minimum time (in minutes)
    between 2 consecutive PMD Auto Load Balancing iterations. The defaul value is 1 min.
  - **Default**: ``''``
  - **Examples**: ``'5'``

- ``tripleo_ovs_dpdk_pmd_sleep_max``

  - **Description**: (*Optional*) PMD maximum sleep time, in range 0 to 10,000.
    Its a string with a number, specifies the maximum sleep time that will be
    requested in microseconds per iteration for a PMD thread which has received
    zero or a small amount of packets from the Rx queues it is polling. The
    actual sleep time requested is based on the load of the Rx queues that the
    PMD polls and may be less than the maximum value.
  - **Default**: ``''``
  - **Examples**: ``'50'``

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
