=================================
Role - tripleo-keystone-resources
=================================

.. ansibleautoplugin::
  :role: tripleo_ansible/roles/tripleo-keystone-resources

Usage
~~~~~

This Ansible role allows to do the following tasks:

* Manage /etc/openstack/clouds.yaml in order to configure `openstacksdk`_.
  If /etc/openstack/clouds.yaml already exists with some config, the role
  will only add new config without removing what was there before;
  however it will modify an existing config if it changed.
  Example: "undercloud" cloud is already configured in clouds.yaml and a new
  "overcloud" config is given to the role. clouds.yaml will now contain both
  configs. However if a new config is given later for "undercloud" and/or
  "overcloud", with e.g. new credentials, the configs will be updated
  accordingly.
  The task has two parameters: `tripleo_keystone_resources_cloud_name` which
  is the name of the cloud and `tripleo_keystone_resources_cloud_config` which
  is the cloud config, defined by `openstacksdk`_.
  Here is an example of a task which would configure the "overcloud" cloud in
  clouds.yaml:

.. code-block:: YAML

  - name: Configure /etc/openstack/clouds.yaml
    include_role:
      name: tripleo-keystone-resources
      tasks_from: clouds
    vars:
      tripleo_keystone_resources_cloud_name: overcloud
      tripleo_keystone_resources_cloud_config:
        auth:
          auth_url: https://keystone-public:5000
          password: verysecrete
          project_domain_name: Default
          project_name: admin
          user_domain_name: Default
          username: admin
        identity_api_version: '3'
        region_name: RegionOne


* Manage Keystone resources like: projects, domains, services, endpoints,
  roles, users and roles assignements.
  The resources are split by playbook, so they can be individually used.
  The `main` playbook will call them all, by starting with the `admin`
  playbook which manages things like: default domain, admin and service
  projects, admin role and _member_ role if
  `tripleo_keystone_resources_member_role_enabled` is set to true (needed by
  Horizon), admin user and its assignements to the roles, identity service and
  the three endpoints (public, internal and admin).
  The rest of the `main` playbook will create the resources according to what
  is defined in `tripleo_keystone_resources_catalog_config`.
  The `tripleo_keystone_resources_catalog_config` interface is documented later
  in this manual.
  The Keystone resources are created by using the OpenStack Ansible modules,
  and therefore the openstacksdk. To make it faster, we use `async`_ and batch
  the data by `10`. It can be changed with `tripleo_keystone_resources_batch`.
  Here is an example of a task which would configure the Keystone resources
  (with an small example of catalog config with only Neutron resources):

.. code-block:: YAML

  - name: Manage Keystone resources for OpenStack services
    include_role:
      name: tripleo-keystone-resources
    vars:
      tripleo_keystone_resources_catalog_config:
        neutron:
          endpoints:
            public: https://neutron-admin:9696
            internal: https://neutron-admin:9696
            admin: https://neutron-admin:9696
          users:
            neutron:
              password: secrete_neutron
          region: RegionOne
          service: 'network'
      tripleo_keystone_resources_service_project: 'service'
      tripleo_keystone_resources_cloud_name: overcloud
      tripleo_keystone_resources_region: RegionOne
      tripleo_keystone_resources_admin_endpoint: https://keystone-admin:35357
      tripleo_keystone_resources_public_endpoint: https://keystone-public:5000
      tripleo_keystone_resources_internal_endpoint: https://keystone-internal:500
      tripleo_keystone_resources_admin_password: verysecrete

Roles variables
~~~~~~~~~~~~~~~

+------------------------------------------------+----------------------------+----------------------------+
| Name                                           | Default Value              | Description                |
+================================================+============================+============================+
| tripleo_keystone_resources_cloud_name          | openstack                  | OpenStack cloud name       |
+------------------------------------------------+----------------------------+----------------------------+
| tripleo_keystone_resources_cloud_config        | {}                         | OpenStack Cloud config     |
+------------------------------------------------+----------------------------+----------------------------+
| tripleo_keystone_resources_clouds_file_path    | /etc/openstack/clouds.yaml | File path for clouds.yaml  |
+------------------------------------------------+----------------------------+----------------------------+
| tripleo_keystone_resources_clouds_file_owner   | root                       | File owner for clouds.yaml |
+------------------------------------------------+----------------------------+----------------------------+
| tripleo_keystone_resources_clouds_file_group   | root                       | File group for clouds.yaml |
+------------------------------------------------+----------------------------+----------------------------+
| tripleo_keystone_resources_clouds_file_mode    | '0600'                     | File mode for clouds.yaml  |
+------------------------------------------------+----------------------------+----------------------------+
| tripleo_keystone_resources_catalog_config      | {}                         | Cloud catalog config       |
+------------------------------------------------+----------------------------+----------------------------+
| tripleo_keystone_resources_member_role_enabled | false                      | Manage _member_ role       |
+------------------------------------------------+----------------------------+----------------------------+
| tripleo_keystone_resources_batch               | 10                         | How many Keystone          |
|                                                |                            | resources do we manage at  |
|                                                |                            | the same time              |
+------------------------------------------------+----------------------------+----------------------------+

Keystone resources catalog config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `tripleo_keystone_resources_catalog_config` parameter defines the
Keystone resources that we want to create.

The data type has to be a dictionary where:

* The (required) key is the service name and must be unique in the deployment.

* The (optional) `endpoints` contains three keys: public, internal and admin;
  which define each endpoint type.

* The (optional) `users` contains the users required by the service.
  Most of the services will have one defined user with its password but
  a second user or more can be provided with specific roles and domain.
  If a user has multiple roles, the user role assignment will be done for each
  role into either a project (default to service) or a domain if defined.

* The (required if endpoints are needed) `region` defines the OpenStack region
  in which the endpoints are created.

* The (required if endpoints are needed) `service` defines the service type
  name for the service that is deployed.
  Note that it's important to read the service documentation to know what
  service type should be used, or the service won't be discoverable by
  OpenStack clients.

* The (optional) `roles` is a list that contains the extra roles that will be
  created.

* The (optional) `domains` is a list that contains the extra domains that will
  be created.

Here is an advanced example for Heat API resources:

.. code-block:: YAML

  keystone_resources:
    heat:
      endpoints:
        public: https://neutron-public:8004
        internal: https://neutron-internal:8004
        admin: https://neutron-admin:8004
      users:
        heat:
          password: secrete_heat
        heat_stack_domain_admin:
          password: secret_heat_domain
          roles:
            - admin
          domain: heat_stack
      region: RegionOne
      service: 'orchestration'
      roles:
        - heat_stack_user
      domains:
        - heat_stack


.. _openstacksdk: https://docs.openstack.org/openstacksdk/latest/user/config/configuration.html#config-files
.. _async: https://docs.ansible.com/ansible/latest/user_guide/playbooks_async.html
